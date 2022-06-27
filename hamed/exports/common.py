#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import re
import logging
import datetime
import locale

from hamed.instance import Instance

logger = logging.getLogger(__name__)


def concat(parts, sep=" &ndash; "):
    if isinstance(parts, str):
        parts = [parts]
    return sep.join([part for part in parts if part])


def get_lieu_naissance(data, key, village=False):
    region = data.get("{}region".format(key))
    cercle = data.get("{}cercle".format(key))
    commune = data.get("{}commune".format(key))
    lieu_naissance = concat([commune, cercle, region], " / ")
    return region, cercle, commune, lieu_naissance.upper()


def get_lieu(data, key):
    region, cercle, commune, _ = get_lieu_naissance(data, key)
    village = data.get("{}village".format(key))
    lieu = concat([village, commune, cercle, region], "/")
    return region, cercle, commune, village, lieu


def get_other(data, key):
    data_value = data.get(key)
    data_value_other = data.get("{}_other".format(key))
    return data_value_other if data_value == "other" else data_value


def get_int(data, key, default=0):
    try:
        return int(data.get(key, default))
    except Exception as e:
        logger.debug(e)
        return default


def get_date(data, key):
    try:
        return datetime.date(*[int(x) for x in data.get(key).split("-")])
    except:
        return None


def get_dob(data, key, female=False):
    type_naissance = data.get("{}type-naissance".format(key), "ne-vers")
    annee_naissance = get_int(data, "{}annee-naissance".format(key), None)
    ddn = get_date(data, "{}ddn".format(key))
    human = "né{f} ".format(f="e" if female else "")
    if type_naissance == "ddn":
        date_or_year = ddn.strftime("%d-%m-%Y")
        human += "le {}".format(date_or_year)
    else:
        date_or_year = annee_naissance
        human += "vers {}".format(date_or_year)

    return type_naissance, annee_naissance, ddn, human, date_or_year


def get_bool(data, key, default="non"):
    text = data.get(key, default)
    return text == "oui", text


def get_nom(data, p="", s=""):
    nom = Instance.clean_lastname(data.get("{p}nom{s}".format(p=p, s=s)))
    prenoms = Instance.clean_firstnames(data.get("{p}prenoms{s}".format(p=p, s=s)))
    name = Instance.clean_name(nom, prenoms)
    return nom, prenoms, name


def clean_phone_number_str(number, skip_indicator=None):
    """properly formated for visualization: (xxx) xx xx xx xx"""

    def format(number):
        if len(number) % 2 == 0:
            span = 2
        else:
            span = 3
        # use NBSP
        return " ".join(
            ["".join(number[i : i + span]) for i in range(0, len(number), span)]
        )

    clean_number = re.sub(r"[^\d\+]", "", number)
    return format(clean_number)


def number_format(value, precision=2):
    try:
        format = "%d"
        value = int(value)
    except:
        try:
            format = "%." + "%df" % precision
            value = float(value)
        except:
            format = "%s"
        else:
            if value.is_integer():
                format = "%d"
                value = int(value)
    try:
        return locale.format(format, value, grouping=True)
    except Exception:
        return value
