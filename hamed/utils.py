#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import io
import csv

from hamed.exports.pdf.social_survey import gen_social_survey_pdf
from hamed.exports.pdf.indigence_certificate import gen_indigence_certificate_pdf
from hamed.exports.pdf.residence_certificate import gen_residence_certificate_pdf

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
        survey = gen_social_survey_pdf(target)
        with open('/tmp/{id}.pdf'.format(id=target.identifier), 'wb') as f:
            f.write(survey.read())
        residence = gen_residence_certificate_pdf(target)
        with open('/tmp/residence_{id}.pdf'.format(id=target.identifier), 'wb') as f:
            f.write(residence.read())
        indigence = gen_indigence_certificate_pdf(target)
        with open('/tmp/indigence_{id}.pdf'.format(id=target.identifier), 'wb') as f:
            f.write(indigence.read())


def get_attachment(dataset, question_value, main_key='_attachments'):
    ''' retrieve a specific attachment dict for a question value '''
    if question_value is not None:
        for attachment in dataset.get(main_key, []):
            if attachment.get('filename', "").endswith(question_value):
                return attachment
    return None
