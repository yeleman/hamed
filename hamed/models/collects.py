#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
from collections import OrderedDict

from django.db import models
from django.urls import reverse
from django.utils import timezone

from hamed.utils import gen_targets_csv
from hamed.models.targets import Target

logger = logging.getLogger(__name__)


class ActiveCollectManager(models.Manager):
    def get_queryset(self):
        return super(ActiveCollectManager, self).get_queryset() \
            .filter(status__in=(Collect.STARTED, Collect.ENDED))


class ArchivedCollectManager(models.Manager):
    def get_queryset(self):
        return super(ArchivedCollectManager, self).get_queryset() \
            .filter(status=Collect.FINALIZED)


class Collect(models.Model):

    class Meta:
        unique_together = [('commune', 'suffix')]

    STARTED = 'started'
    ENDED = 'ended'
    FINALIZED = 'finalized'

    STATUSES = OrderedDict([
        (STARTED, "Collecte terrain en cours"),
        (ENDED, "Collecte terminée, analyse des données"),
        (FINALIZED, "Collecte finalisée avec documents")
    ])

    status = models.CharField(max_length=50,
                              choices=STATUSES.items(),
                              default=STARTED)

    started_on = models.DateTimeField(auto_now_add=True)
    ended_on = models.DateTimeField(blank=True, null=True)
    finalized_on = models.DateTimeField(blank=True, null=True)

    commune = models.CharField(max_length=100)
    suffix = models.CharField(max_length=50)

    ona_form_pk = models.IntegerField(blank=True, null=True)
    ona_scan_form_pk = models.IntegerField(blank=True, null=True)

    nb_submissions = models.IntegerField(blank=True, null=True)
    nb_indigents = models.IntegerField(blank=True, null=True)
    nb_non_indigents = models.IntegerField(blank=True, null=True)
    nb_medias = models.IntegerField(blank=True, null=True)
    medias_size = models.IntegerField(blank=True, null=True)

    objects = models.Manager()
    active = ActiveCollectManager()
    archived = ArchivedCollectManager()

    def name(self):
        return "E.S {commune} {suffix}".format(
            commune=self.commune, suffix=self.suffix)

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
        return self.STATUSES.get(self.status)

    def has_ended(self):
        return self.status in (self.ENDED, self.FINALIZED)

    def has_finalized(self):
        return self.status == self.FINALIZED

    def get_next_step(self):
        # find out next step
        if self.status == self.STARTED:
            url = reverse('end_collect',
                          kwargs={'collect_id': self.id})
            label = "Cloturer la collecte"
        elif self.status == self.ENDED:
            url = reverse('finalize_collect',
                          kwargs={'collect_id': self.id})
            label = "Finaliser la collecte"
        elif self.status == self.FINALIZED:
            url = reverse('export',
                          kwargs={'collect_id': self.id})
            label = "Exporter les données de la collecte"
        return {'url': url, 'label': label}

    def change_status(self, new_status):
        assert new_status in self.STATUSES.keys()

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
            # create Target
            Target.create_from_submission(self, submission)
            attachments = submission.get('_attachments', [])
            for media in attachments:
                media['filesize'] = get_media_size(
                    media.get('filename', ''))

            nb_medias += len(attachments)
            medias_size += sum([m['filesize'] for m in attachments])

        self.nb_submissions = len(data)
        self.nb_medias = nb_medias
        self.medias_size = medias_size
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
            target.dataset['_attachments'] += attachments
            target.save()

        self.nb_medias += nb_medias
        self.medias_size += medias_size
        self.nb_submissions = self.targets.count()
        self.nb_indigents = self.targets.filter(is_indigent=True).count()
        self.nb_non_indigents = self.nb_submissions - self.nb_indigents
        self.save()

        # set all other target as refused (non-indigent)
        for target in self.targets.filter(is_indigent__isnull=True):
            target.is_indigent = False
            target.save()

    def get_targets_csv(self):
        return gen_targets_csv(self.targets.all())
