#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import io
import csv

from hamed.exports.pdf.social_survey import gen_social_survey_pdf

logger = logging.getLogger(__name__)


def gen_targets_csv(targets):
    csvfile = io.StringIO()
    fieldnames = ['ident', 'nom', 'age', 'sexe']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for target in targets:
        writer.writerow({'ident': target.identifier,
                         'nom': target.name(),
                         'age': target.age,
                         'sexe': target.verbose_sex})
    # write complete, reset pointer
    csvfile.seek(0)
    return csvfile


def gen_targets_documents(targets):

    for target in targets:
        survey = gen_social_survey_pdf(target.dataset, target.get_qrcode())
        with open('/tmp/{id}.pdf'.format(id=target.identifier), 'wb') as f:
            f.write(survey.read())