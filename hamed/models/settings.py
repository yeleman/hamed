#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from django.db import models

logger = logging.getLogger(__name__)


class Settings(models.Model):

    ONA_SERVER = 'ona-server'
    ONA_USERNAME = 'ona-username'
    ONA_TOKEN = 'ona-token'

    key = models.SlugField(primary_key=True)
    value = models.CharField(max_length=500)

    @classmethod
    def get_or_none(cls, key):
        try:
            return cls.objects.get(key=key)
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return self.key
