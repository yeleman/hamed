#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from django.db import models

logger = logging.getLogger(__name__)


class Settings(models.Model):

    class Meta:
        verbose_name = "Setting"
        verbose_name_plural = "Settings"
        ordering = ['key']

    ONA_SERVER = 'ona-server'
    ONA_USERNAME = 'ona-username'
    ONA_TOKEN = 'ona-token'
    CERCLE_ID = 'cercle-id'
    DATAENTRY_USERNAME = 'dataentry-username'
    UPLOAD_SERVER = 'upload-server'
    ADVANCED_MODE = 'advanced-mode'

    key = models.SlugField(primary_key=True)
    value = models.CharField(max_length=500)

    @classmethod
    def get_or_none(cls, key):
        try:
            return cls.objects.get(key=key)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_value_or_none(cls, key):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return self.key

    @classmethod
    def ona_server(cls):
        return cls.get_value_or_none(cls.ONA_SERVER)

    @classmethod
    def ona_username(cls):
        return cls.get_value_or_none(cls.ONA_USERNAME)

    @classmethod
    def ona_token(cls):
        return cls.get_value_or_none(cls.ONA_TOKEN)

    @classmethod
    def cercle_id(cls):
        return cls.get_value_or_none(cls.CERCLE_ID)

    @classmethod
    def dataentry_username(cls):
        return cls.get_value_or_none(cls.DATAENTRY_USERNAME)

    @classmethod
    def upload_server(cls):
        return cls.get_value_or_none(cls.UPLOAD_SERVER)

    @classmethod
    def advanced_mode(cls):
        val = cls.get_value_or_none(cls.ADVANCED_MODE)
        return False if not val else val.lower() == "true"
