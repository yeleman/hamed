#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import translation
from django.conf import settings

from hamed.models.targets import Target
from hamed.utils import gen_targets_documents

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate documents for a Target"

    def add_arguments(self, parser):
        parser.add_argument('ident', type=str,
                            help="Target ident to generate doc for"),

    def handle(self, *args, **kwargs):
        translation.activate(settings.LANGUAGE_CODE)
        ident = kwargs.get('ident')
        target = Target.get_or_none(ident)
        if target is None:
            raise CommandError(
                "Error: Unable to find Target with ID `{ident}`"
                .format(ident=ident))

        # logger.info(target)

        # generate paper form
        gen_targets_documents([target])
        translation.deactivate()
