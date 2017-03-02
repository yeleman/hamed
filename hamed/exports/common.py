#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import datetime

from hamed.instance import Instance

logger = logging.getLogger(__name__)


def concat(parts, sep=" &ndash; "):
    if isinstance(parts, str):
        parts = [parts]
    return sep.join([part for part in parts if part])


def get_lieu_naissance(data, key, village=False):
    region = data.get('{}region'.format(key))
    cercle = data.get('{}cercle'.format(key))
    commune = data.get('{}commune'.format(key))
    lieu_naissance = concat([commune, cercle, region], " / ")
    return region, cercle, commune, lieu_naissance


def get_lieu(data, key):
    region, cercle, commune, _ = get_lieu_naissance(data, key)
    village = data.get('{}village'.format(key))
    lieu = concat([village, commune, cercle, region], "/")
    return region, cercle, commune, village, lieu


def get_other(data, key):
    data_value = data.get(key)
    data_value_other = data.get('{}_other'.format(key))
    return data_value_other if data_value == 'other' else data_value


def get_int(data, key, default=0):
    try:
        return int(data.get(key, default))
    except Exception as e:
        logger.info(e)
        return default


def get_date(data, key):
    try:
        return datetime.date(*[int(x) for x in data.get(key).split('-')])
    except:
        return None


def get_dob(data, key, female=False):
    type_naissance = data.get('{}type-naissance'.format(key), 'ne-vers')
    annee_naissance = get_int(data, '{}annee-naissance'.format(key), None)
    ddn = get_date(data, '{}ddn'.format(key))
    human = "Né{f} ".format(f="e" if female else "")
    if type_naissance == 'ddn':
        human += "le {}".format(ddn.strftime("%d-%m-%Y"))
    else:
        human += "vers {}".format(annee_naissance)

    return type_naissance, annee_naissance, ddn, human


def get_bool(data, key, default='non'):
    text = data.get(key, default)
    return text == 'oui', text


def get_nom(data, p='', s=''):
    nom = Instance.clean_lastname(
        data.get('{p}nom{s}'.format(p=p, s=s)))
    prenoms = Instance.clean_firstnames(data.get('{p}prenoms{s}'
                                                 .format(p=p, s=s)))
    name = Instance.clean_name(nom, prenoms)
    return nom, prenoms, name
