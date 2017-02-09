#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
from collections import OrderedDict
import io
import qrcode

from django.db import models
from django.utils import timezone
from jsonfield.fields import JSONField

from hamed.identifiers import full_random_id

logger = logging.getLogger(__name__)


class Target(models.Model):

    MALE = 'male'
    FEMALE = 'female'
    GENDERS = OrderedDict([
        (MALE, "Male"),
        (FEMALE, "Female")
    ])
    SEXES = OrderedDict([
        (MALE, "Man"),
        (FEMALE, "Woman")
    ])

    identifier = models.CharField(max_length=10, primary_key=True)
    collect = models.ForeignKey('Collect', related_name='targets')
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    age = models.IntegerField()
    gender = models.CharField(max_length=20, choices=GENDERS.items())
    region = models.CharField(max_length=100)
    cercle = models.CharField(max_length=100)
    commune = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    is_indigent = models.NullBooleanField(blank=True, null=True)
    dataset = JSONField(default=dict, blank=True)

    def fname(self):
        return "{ident}-{last} {first}".format(
            ident=self.identifier, last=self.last_name.upper(),
            first=self.first_name.title())

    def name(self):
        return "{first} {last}".format(
            last=self.last_name.upper(), first=self.first_name.title())

    @property
    def verbose_sex(self):
        return self.SEXES.get(self.gender)

    def __str__(self):
        return "{ident}.{name}".format(ident=self.identifier, name=self.name())

    @classmethod
    def get_unused_ident(cls):
        nb_targets = cls.objects.count()
        attempts = 0
        while attempts <= nb_targets + 10:
            attempts += 1
            ident = full_random_id()
            if cls.objects.filter(identifier=ident).count():
                continue
            return ident
        raise Exception("Unable to compute a free identifier for Target.")

    @classmethod
    def create_from_submission(cls, collect, submission):
        sex = submission.get('enquete/sexe')
        birth_type = submission.get('enquete/type-naissance')
        yob = submission.get('enquete/annee-naissance', '')
        dob = submission.get('enquete/ddn', '')
        this_year = timezone.now().year
        if birth_type == 'ddn':
            yob = int(dob.split('-')[0])
        age = this_year - int(yob)
        payload = {
            'identifier': cls.get_unused_ident(),
            'collect': collect,
            'first_name': submission.get('enquete/prenoms'),
            'last_name': submission.get('enquete/nom'),
            'age': age,
            'gender': cls.FEMALE if sex == 'feminin' else cls.MALE,
            'region': submission.get('localisation-enquete/lieu_region'),
            'cercle': submission.get('localisation-enquete/lieu_cercle'),
            'commune': submission.get('localisation-enquete/lieu_commune'),
            'village': submission.get('localisation-enquete/lieu_village')
            or submission.get('localisation-enquete/lieu_village_autre'),
            'dataset': submission,
        }
        return cls.objects.create(**payload)

    @classmethod
    def get_or_none(cls, identifier):
        try:
            return cls.objects.get(identifier=identifier)
        except cls.DoesNotExist:
            return None

    def get_qrcode(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4)

        qr.add_data(self.identifier)
        qr.make(fit=True)
        im = qr.make_image()
        output = io.BytesIO()
        im.save(output, format="PNG")
        output.seek(0)
        return output
