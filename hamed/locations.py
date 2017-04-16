#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

logger = logging.getLogger(__name__)


CERCLES = {
    "15": {
        "name": "SIKASSO",
        "id": "15",
        "communes": {
            "238": {"id": "238", "name": "SIKASSO"},
            "239": {"id": "239", "name": "BENKADI"},
            "240": {"id": "240", "name": "BLENDIO"},
            "241": {"id": "241", "name": "DANDERESSO"},
            "242": {"id": "242", "name": "DEMBELA"},
            "243": {"id": "243", "name": "DIALAKORO"},
            "244": {"id": "244", "name": "DIOMATENE"},
            "245": {"id": "245", "name": "DOGONI"},
            "246": {"id": "246", "name": "DOUMANABA"},
            "247": {"id": "247", "name": "FAMA"},
            "248": {"id": "248", "name": "FARAKALA"},
            "249": {"id": "249", "name": "FINKOLO"},
            "250": {"id": "250", "name": "FINKOLO GANADOUGOU"},
            "251": {"id": "251", "name": "GONGASSO"},
            "252": {"id": "252", "name": "KABARASSO"},
            "253": {"id": "253", "name": "KABOILA"},
            "254": {"id": "254", "name": "KAFOUZIELA"},
            "255": {"id": "255", "name": "KAPALA"},
            "256": {"id": "256", "name": "KAPOLONDOUGOU"},
            "257": {"id": "257", "name": "KIGNAN"},
            "258": {"id": "258", "name": "KLELA"},
            "259": {"id": "259", "name": "KOFAN"},
            "260": {"id": "260", "name": "KOLOKOBA"},
            "261": {"id": "261", "name": "KOUMANKOU"},
            "262": {"id": "262", "name": "KOUORO"},
            "263": {"id": "263", "name": "KOUROUMA"},
            "264": {"id": "264", "name": "LOBOUGOULA"},
            "265": {"id": "265", "name": "MINIKO"},
            "266": {"id": "266", "name": "MIRIA"},
            "267": {"id": "267", "name": "MISSIRIKORO"},
            "268": {"id": "268", "name": "N'TJIKOUNA"},
            "269": {"id": "269", "name": "NATIEN"},
            "270": {"id": "270", "name": "NIENA"},
            "271": {"id": "271", "name": "NONGO-SOUALA"},
            "272": {"id": "272", "name": "PIMPERNA"},
            "273": {"id": "273", "name": "SANZANA"},
            "274": {"id": "274", "name": "SOKOURANIMISSIRIK."},
            "275": {"id": "275", "name": "TELLA"},
            "276": {"id": "276", "name": "TIANKADI"},
            "277": {"id": "277", "name": "WATENI"},
            "278": {"id": "278", "name": "ZANFEREBOUGOU"},
            "279": {"id": "279", "name": "ZANGARADOUGOU"},
            "280": {"id": "280", "name": "ZANIENA"},
        }
    },
    "16": {
        "name": "BOUGOUNI",
        "id": "16",
        "communes": {
            "281": {"id": "281", "name": "BOUGOUNI"},
            "282": {"id": "282", "name": "BLADIE-TIEMALA"},
            "283": {"id": "283", "name": "DANOU"},
            "284": {"id": "284", "name": "DEBELIN"},
            "285": {"id": "285", "name": "DEFINA"},
            "286": {"id": "286", "name": "DOGO"},
            "287": {"id": "287", "name": "DOMBA"},
            "288": {"id": "288", "name": "FARADIELE"},
            "289": {"id": "289", "name": "FARAGOUARAN"},
            "290": {"id": "290", "name": "GARALO"},
            "291": {"id": "291", "name": "KELEYA"},
            "292": {"id": "292", "name": "KOKELE"},
            "293": {"id": "293", "name": "KOLA"},
            "294": {"id": "294", "name": "KOUMANTOU"},
            "295": {"id": "295", "name": "KOUROULAMINI"},
            "296": {"id": "296", "name": "MERIDIELA"},
            "297": {"id": "297", "name": "OUROUN"},
            "298": {"id": "298", "name": "SANSO"},
            "299": {"id": "299", "name": "SIBIRILA"},
            "300": {"id": "300", "name": "SIDO"},
            "301": {"id": "301", "name": "SYEN TOULA"},
            "302": {"id": "302", "name": "TIEMALA BANIMONOTIE"},
            "303": {"id": "303", "name": "WOLA"},
            "304": {"id": "304", "name": "YININDOUGOU"},
            "305": {"id": "305", "name": "YIRIDOUGOU"},
            "306": {"id": "306", "name": "ZANTIEBOUGOU"},
        },
    },
    "29": {
        "name": "MOPTI",
        "id": "29",
        "communes": {
            "503": {"id": "503", "name": "MOPTI"},
            "504": {"id": "504", "name": "BASSIROU"},
            "505": {"id": "505", "name": "BORONDOUGOU"},
            "506": {"id": "506", "name": "DIALLOUBE"},
            "507": {"id": "507", "name": "FATOMA"},
            "508": {"id": "508", "name": "KONNA"},
            "509": {"id": "509", "name": "KOROMBANA"},
            "510": {"id": "510", "name": "KOUBAYE"},
            "511": {"id": "511", "name": "KOUNARI"},
            "512": {"id": "512", "name": "OURO MODI"},
            "513": {"id": "513", "name": "OUROUBE DOUDDE"},
            "514": {"id": "514", "name": "SASALBE"},
            "515": {"id": "515", "name": "SIO"},
            "516": {"id": "516", "name": "SOCOURA"},
            "517": {"id": "517", "name": "SOYE"},
        },
    },
    "33": {
        "name": "DOUENTZA",
        "id": "33",
        "communes": {
            "563": {"id": "563", "name": "DOUENTZA"},
            "564": {"id": "564", "name": "DALLAH"},
            "565": {"id": "565", "name": "DANGOL-BORE"},
            "566": {"id": "566", "name": "DEBERE"},
            "567": {"id": "567", "name": "DIANWELY"},
            "568": {"id": "568", "name": "DJAPTODJI"},
            "569": {"id": "569", "name": "GANDAMIA"},
            "570": {"id": "570", "name": "HAIRE"},
            "571": {"id": "571", "name": "HOMBORI"},
            "572": {"id": "572", "name": "KERENA"},
            "573": {"id": "573", "name": "KORAROU"},
            "574": {"id": "574", "name": "KOUBEWEL KOUNDIA"},
            "575": {"id": "575", "name": "MONDORO"},
            "576": {"id": "576", "name": "PETAKA"},
            "577": {"id": "577", "name": "TEDIE"},
        },
    },
}


def get_cercle(cercle_id):
    return CERCLES.get(cercle_id)


def get_cercle_name(cercle_id):
    cercle = get_cercle(cercle_id)
    return None if cercle is None else cercle.get('name')


def get_commune(cercle_id, commune_id):
    cercle = get_cercle(cercle_id)
    if cercle is None:
        return None

    return cercle.get('communes', {}).get(commune_id)


def get_commune_name(cercle_id, commune_id):
    commune = get_commune(cercle_id, commune_id)
    return None if commune is None else commune.get('name')


def get_communes(cercle_id):
    cercle = get_cercle(cercle_id)
    if cercle is None:
        return []
    return [(c['id'], c['name']) for c in cercle.get('communes', {}).values()]
