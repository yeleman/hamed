#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import io
import csv
import os

from path import Path as P
from django.db.models import QuerySet

from hamed.exports.pdf.social_survey import gen_social_survey_pdf
from hamed.exports.pdf.indigence_certificate import \
    gen_indigence_certificate_pdf
from hamed.exports.pdf.residence_certificate import \
    gen_residence_certificate_pdf

logger = logging.getLogger(__name__)

PERSONAL_FILES = "Dossiers"
PRINTS = "Impressions"
SURVEYS = "Enquetes"
INDIGENCES = "Certificats indigence"
RESIDENCES = "Certificats residence"


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


def check_targets_documents_folder(collect):

    # collect-root
    croot = collect.get_documents_path()
    P(croot).makedirs_p()

    # static folders for collect
    for folder_name in (PRINTS, PERSONAL_FILES):
        P(os.path.join(croot, folder_name)).makedirs_p()


def get_document_fname(kind, target):
    templates = {
        'survey': "{id}_enquete-sociale.pdf",
        'indigence': "{id}_certificat-indigence-vierge.pdf",
        'residence': "{id}_certificat-residence-vierge.pdf"
    }
    return templates.get(kind).format(id=target.identifier)


def gen_targets_documents(targets):

    # ensure we have destinations folder
    if isinstance(targets, QuerySet):
        collects = set([t['collect'] for t in targets.values('collect')])
    else:
        collects = set([t.collect for t in targets])

    for collect in collects:
        check_targets_documents_folder(collect)
        prints_folder = os.path.join(collect.get_documents_path(), PRINTS)
        P(prints_folder).makedirs_p()

        for prints_subfolder in (SURVEYS, INDIGENCES, RESIDENCES):
            P(os.path.join(prints_folder, prints_subfolder)).makedirs_p()

        survey_links_folder = os.path.join(prints_folder, SURVEYS)
        P(survey_links_folder).makedirs_p()

    for target in targets:

        # social survey
        P(target.get_folder_path()).makedirs_p()  # ensure personnal folder OK
        survey = gen_social_survey_pdf(target)
        survey_fname = get_document_fname('survey', target)
        survey_fpath = os.path.join(
            target.get_folder_path(),
            survey_fname)
        with open(survey_fpath, 'wb') as f:
            f.write(survey.read())

        # indigence certificate and residence certificate goes to print folder
        for kind, subfolder, gen_func in (
                ('indigence', INDIGENCES, gen_indigence_certificate_pdf),
                ('residence', RESIDENCES, gen_residence_certificate_pdf)):
            document = gen_func(target)
            document_fpath = os.path.join(
                prints_folder,
                subfolder,
                get_document_fname(kind, target))
            with open(document_fpath, 'wb') as f:
                f.write(document.read())

        # survey is also symlinked in prints
        survey_link_fpath = os.path.join(survey_links_folder, survey_fname)
        # remove first as symlink can't be forced
        P(survey_link_fpath).unlink_p()
        P(survey_fpath).symlink(survey_link_fpath)


def get_attachment(dataset, question_value, main_key='_attachments'):
    ''' retrieve a specific attachment dict for a question value '''
    if question_value is not None:
        for attachment in dataset.get(main_key, []):
            if attachment.get('filename', "").endswith(question_value):
                return attachment
    return None
