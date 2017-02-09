#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from django.core.management.base import BaseCommand, CommandError

from hamed.models import Target
from hamed.exports.pdf.social_survey import gen_social_survey_pdf
from hamed.utils import gen_ident_qrcode

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate documents for a Target"

    def add_arguments(self, parser):
        parser.add_argument('ident', type=str,
                            help="Target ident to generate doc for"),

    def handle(self, *args, **kwargs):
        ident = kwargs.get('ident')
        target = Target.get_or_none(ident)
        if target is None:
            raise CommandError(
                "Error: Unable to find Target with ID `{ident}`"
                .format(ident=ident))

        logger.info(target)

        # generate paper form
        qrcode = gen_ident_qrcode(target)
        paper = gen_social_survey_pdf(target.dataset, qrcode)
        from pprint import pprint as pp ; pp(target.dataset)
        with open('/tmp/{id}.pdf'.format(id=ident), 'wb') as f:
            f.write(paper.read())
