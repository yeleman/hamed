#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import os
import logging
from collections import OrderedDict
from statistics import median, StatisticsError

from django.db import models
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from hamed.utils import gen_targets_csv
from hamed.models.targets import Target
from hamed.models.settings import Settings
from hamed.steps.start_collect import StartCollectTaskCollection
from hamed.steps.end_collect import EndCollectTaskCollection
from hamed.steps.finalize_collect import FinalizeCollectTaskCollection
from hamed.locations import get_cercle_name, get_commune_name

logger = logging.getLogger(__name__)

STARTED = 'started'
ENDED = 'ended'
FINALIZED = 'finalized'
STATE_MACHINE = OrderedDict([
    (STARTED, ("Collecte terrain en cours",
               StartCollectTaskCollection)),
    (ENDED, ("Collecte terminée, analyse des données",
             EndCollectTaskCollection)),
    (FINALIZED, ("Collecte finalisée avec documents",
                 FinalizeCollectTaskCollection))
])
STATUSES = lambda: {k: v[0] for k, v in STATE_MACHINE.items()}


class ActiveCollectManager(models.Manager):
    def get_queryset(self):
        return super(ActiveCollectManager, self).get_queryset() \
            .filter(status__in=(Collect.STARTED, Collect.ENDED))


class ArchivedCollectManager(models.Manager):
    def get_queryset(self):
        return super(ArchivedCollectManager, self).get_queryset() \
            .filter(status=Collect.FINALIZED)


class Collect(models.Model):

    STARTED = STARTED
    ENDED = ENDED
    FINALIZED = FINALIZED

    MAYOR_TITLES = OrderedDict([
        ('sir', "M."),
        ('madam', "Mme"),
        ('doctor', "Dr"),
    ])

    class Meta:
        unique_together = [('commune_id', 'suffix')]

    status = models.CharField(max_length=50, choices=STATUSES().items(),
                              default=STARTED)

    started_on = models.DateTimeField(auto_now_add=True)
    ended_on = models.DateTimeField(blank=True, null=True)
    finalized_on = models.DateTimeField(blank=True, null=True)

    cercle_id = models.CharField(max_length=100, default=Settings.cercle_id)
    commune_id = models.CharField(max_length=100, choices=[],
                                  verbose_name="Commune")
    suffix = models.CharField(max_length=50, verbose_name="Suffixe")
    mayor_title = models.CharField(max_length=50,
                                   choices=MAYOR_TITLES.items(),
                                   verbose_name="Titre")
    mayor_name = models.CharField(max_length=100,
                                  verbose_name="Nom du maire")

    ona_form_pk = models.IntegerField(blank=True, null=True)
    ona_scan_form_pk = models.IntegerField(blank=True, null=True)

    nb_submissions = models.IntegerField(blank=True, null=True)
    nb_indigents = models.IntegerField(blank=True, null=True)
    nb_non_indigents = models.IntegerField(blank=True, null=True)
    nb_medias_form = models.IntegerField(blank=True, null=True)
    nb_medias_scan_form = models.IntegerField(blank=True, null=True)
    medias_size_form = models.IntegerField(blank=True, null=True)
    medias_size_scan_form = models.IntegerField(blank=True, null=True)

    objects = models.Manager()
    active = ActiveCollectManager()
    archived = ArchivedCollectManager()

    def name(self):
        return "E.S {commune} {suffix}".format(
            commune=self.commune, suffix=self.suffix)

    @property
    def cercle(self):
        return get_cercle_name(self.cercle_id)

    @property
    def commune(self):
        return get_commune_name(self.cercle_id, self.commune_id)

    @property
    def mayor(self):
        return "{title} {name}".format(title=self.verbose_mayor_title,
                                       name=self.mayor_name)

    def form_title(self):
        return "Enquête sociale {commune}/{suffix}".format(
            commune=self.commune, suffix=self.suffix)

    def scan_form_title(self):
        return "Scan certificats {commune}/{suffix}".format(
            commune=self.commune, suffix=self.suffix)

    def ona_form_id(self):
        return "enquete-sociale-{id}".format(id=self.id)

    def ona_scan_form_id(self):
        return "scan-certificats-{id}".format(id=self.id)

    @property
    def nb_medias(self):
        return sum([self.nb_medias_form or 0, self.nb_medias_scan_form or 0])

    @property
    def medias_size(self):
        return sum([self.medias_size_form or 0,
                    self.medias_size_scan_form or 0])

    @classmethod
    def get_or_none(cls, cid):
        try:
            return cls.objects.get(id=cid)
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return self.name()

    @property
    def verbose_status(self):
        return STATUSES().get(self.status)

    @property
    def previous_verbose_status(self):
        try:
            assert self.sm_index > 0
            return self.machine_value_for(self.sm_index - 1)[0]
        except:
            return "Supprimer la collecte"

    @property
    def verbose_mayor_title(self):
        return self.MAYOR_TITLES.get(self.mayor_title)

    @property
    def started(self):
        return self.status == self.STARTED

    @property
    def ended(self):
        return self.status == self.ENDED

    @property
    def finalized(self):
        return self.status == self.FINALIZED

    def has_ended(self):
        return self.status in (self.ENDED, self.FINALIZED)

    def has_finalized(self):
        return self.status == self.FINALIZED

    @property
    def sm_index(self):
        try:
            return self.machine_index_for(self.status)
        except ValueError:
            return -1

    @classmethod
    def machine_index_for(cls, status):
        return list(STATE_MACHINE.keys()).index(status)

    @classmethod
    def machine_key_for(cls, index):
        return list(STATE_MACHINE.keys())[index]

    @classmethod
    def machine_value_for(cls, index):
        return list(STATE_MACHINE.values())[index]

    def upgrade(self):
        # can't upgrade if invalid or at last state
        if self.sm_index < 0 or (self.sm_index >= len(STATE_MACHINE) - 1):
            return

        # create task collection
        tc = self.machine_value_for(self.sm_index + 1)[1](collect=self)
        tc.process()
        return tc

    def downgrade(self):
        print("**********", "DOWNGRADE", "********", "SM-INDEX", self.sm_index)
        # can't downgrade if at first step. Delete instead
        if self.sm_index < 0:
            return

        tc = self.machine_value_for(self.sm_index)[1](collect=self)
        tc.revert_all()
        return tc

    def transform_to(self, new_status):
        # unable to move to non-existing state
        assert new_status in STATUSES().keys()

        # do nothing if requested state is current one
        if self.status == new_status:
            return

        # find out index of requested state or exit
        try:
            n_index = self.machine_index_for(new_status)
        except ValueError:
            logger.error("No such new status")
            return

        # wether we will upgrade or downgrade to get there
        updown = self.downgrade if self.sm_index > n_index else self.upgrade
        # nb of steps to get there
        nb_steps = abs(self.sm_index - n_index)

        # execute those steps
        for _ in range(0, nb_steps):
            updown()

    def get_next_step(self):
        # find out next step
        if self.status == self.STARTED:
            url = reverse('end_collect',
                          kwargs={'collect_id': self.id})
            label = "Cloturer la collecte"
            icon = 'end'
        elif self.status == self.ENDED:
            url = reverse('finalize_collect',
                          kwargs={'collect_id': self.id})
            label = "Finaliser la collecte"
            icon = 'finalize'
        else:
            return None
        # elif self.status == self.FINALIZED:
        #     url = reverse('export',
        #                   kwargs={'collect_id': self.id})
        #     label = "Exporter les données de la collecte"
        return {'url': url, 'label': label, 'icon': icon}

    def change_status(self, new_status):
        assert new_status in STATUSES().keys()

        if new_status == self.ENDED:
            self.ended_on = timezone.now()
            self.finalized_on = None
        elif new_status == self.FINALIZED:
            self.finalized_on = timezone.now()
        elif new_status == self.STARTED:
            self.ended_on = None
            self.finalized_on = None

        self.status = new_status
        self.save()

    def process_form_data(self, data):
        from hamed.ona import get_media_size

        nb_medias = 0
        medias_size = 0
        for submission in data:
            # get attachement filesizes
            attachments = submission.get('_attachments', [])
            for media in attachments:
                media['filesize'] = get_media_size(
                    media.get('filename', ''))
            submission['_attachments'] = attachments

            # create Target
            Target.create_from_submission(self, submission)

            nb_medias += len(attachments)
            medias_size += sum([m['filesize'] for m in attachments])

        self.nb_submissions = len(data)
        self.nb_medias_form = nb_medias
        self.medias_size_form = medias_size
        self.save()

    def reset_form_data(self):
        self.targets.all().delete()
        self.nb_submissions = None
        self.nb_medias_form = None
        self.medias_size_form = None
        self.save()

    def process_scan_form_data(self, data):
        from hamed.ona import get_media_size

        nb_medias = 0
        medias_size = 0
        for submission in data:
            # find target and mark as indigent
            target = Target.get_or_none(submission.get('ident'))
            assert target is not None
            target.is_indigent = True

            # include new attachments to counters
            attachments = submission.get('_attachments', [])
            for media in attachments:
                media['filesize'] = get_media_size(media.get('filename', ''))

            nb_medias += len(attachments)
            medias_size += sum([m['filesize'] for m in attachments])

            # add new attachments to Target payload
            target.dataset['_scan_attachments'] = attachments
            target.save()

        self.nb_medias_scan_form += nb_medias
        self.medias_size_scan_form += medias_size
        self.nb_submissions = self.targets.count()
        self.nb_indigents = self.targets.filter(is_indigent=True).count()
        self.nb_non_indigents = self.nb_submissions - self.nb_indigents
        self.save()

        # set all other target as refused (non-indigent)
        for target in self.targets.filter(is_indigent__isnull=True):
            target.is_indigent = False
            target.save()

    def reset_scan_form_data(self):
        # remove indigent
        for target in self.targets.filter(is_indigent=True):
            target.is_indigent = None
            if '_scan_attachments' in target.dataset:
                del(target.dataset['_scan_attachments'])
            target.save()

        self.nb_medias_scan_form = None
        self.medias_size_scan_form = None
        self.nb_submissions = self.targets.count()  # shouldn't have changed
        self.nb_indigents = None
        self.nb_non_indigents = None
        self.save()

    def get_targets_csv(self):
        return gen_targets_csv(self.targets.all())

    def get_documents_path(self):
        return os.path.join(settings.COLLECT_DOCUMENTS_FOLDER,
                            self.ona_form_id())

    def get_nb_men(self):
        return self.targets.filter(gender=Target.MALE).count()

    def get_nb_women(self):
        return self.targets.filter(gender=Target.FEMALE).count()

    def get_median_age(self):
        try:
            return median([t['age'] for t in self.targets.values('age')])
        except StatisticsError:
            return None

    def get_nb_papers(self):
        return self.nb_submissions * 3 if self.nb_submissions else None
