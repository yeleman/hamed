#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
from pyxform.builder import create_survey_from_xls

logger = logging.getLogger(__name__)


def build_form_labels(xlsform_path):
    # read XLSForm and feed PyXForm
    with open(xlsform_path, 'rb') as f:
        xlsform = create_survey_from_xls(f)

    # retrive JSONForm
    jsonform = xlsform.to_json_dict()
    # from pprint import pprint as pp ; pp(jsonform)

    # we'll want labels as {name: label}
    labelslist2dict = lambda l: {e['name']: e['label'] for e in l}

    labels = {}

    def walk(node):
        for item in node:
            if isinstance(item, dict):
                if 'type' in item and item['type'].startswith('select ') \
                        and 'external' not in item['type']:
                    labels.update(
                        {item['name']: labelslist2dict(item['children'])})
                else:
                    walk(item)
            else:
                pass

    # walk through jsonform tree to find select x questions
    walk(jsonform['children'])

    return labels


LABELS = build_form_labels('hamed/fixtures/enquete-sociale-mobile.xlsx')


def get_label_for(question, value):
    return LABELS.get(question, {}).get(value)
