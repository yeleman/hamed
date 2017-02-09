#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import datetime
import logging

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

from hamed.instance import Instance

BLANK = "n/c"
logger = logging.getLogger(__name__)


def gen_social_survey_pdf(instance, qrcode):

    pdf_form = io.BytesIO()

    width, height = A4

    # writting data
    def format_location(parts):
        return " / ".join([part for part in parts if part])

    def concat(parts, sep=" / "):
        if isinstance(parts, str):
            parts = [parts]
        return sep.join([part for part in parts if part])

    def get_lieu_naissance(data, key, village=False):
        region = data.get('{}region'.format(key))
        cercle = data.get('{}cercle'.format(key))
        commune = data.get('{}commune'.format(key))
        lieu_naissance = format_location([commune, cercle, region])
        return region, cercle, commune, lieu_naissance

    def get_lieu(data, key):
        region, cercle, commune, _ = get_lieu_naissance(data, key)
        village = data.get('{}village'.format(key))
        lieu = format_location([village, commune, cercle, region])
        return region, cercle, commune, village, lieu

    def get_other(data, key):
        profession = data.get(key)
        profession_other = data.get('{}_other'.format(key))
        return profession_other if profession == 'other' else profession

    def get_int(data, key, default=0):
        try:
            return int(data.get(key, default))
        except:
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

    # lieu (pas sur papier)
    lieu_region, lieu_cercle, lieu_commune, lieu_village, lieu = \
        get_lieu(instance, 'localisation-enquete/lieu_')

    numero_enquete = instance.get('numero') or ""
    objet_enquete = instance.get('objet') or BLANK
    identifiant_enqueteur = instance.get('enqueteur') or BLANK
    demandeur = instance.get('demandeur') or BLANK

    # enquêté
    nom, prenoms, name = get_nom(instance, p='enquete/')
    sexe = instance.get('enquete/sexe') or 'masculin'
    is_female = sexe == 'feminin'
    type_naissance, annee_naissance, ddn, naissance = \
        get_dob(instance, 'enquete/', is_female)
    region_naissance, cercle_naissance, commune_naissance, lieu_naissance = \
        get_lieu_naissance(instance, 'enquete/')

    # enquêté / instance
    nom_pere, prenoms_pere, name_pere = get_nom(
        instance, p='enquete/filiation/', s='-pere')
    nom_mere, prenoms_mere, name_mere = get_nom(
        instance, p='enquete/filiation/', s='-mere')

    situation_matrioniale = instance.get(
        'enquete/situation-matrimoniale', BLANK)
    profession = get_other(instance, 'enquete/profession')
    adresse = instance.get('enquete/adresse')
    nina = instance.get('nina')
    telephones = [str(tel.get('enquete/telephones/numero'))
                  for tel in instance.get('enquete/telephones', [])]

    nb_epouses = get_int(instance, 'nb_epouses', 0)

    # enfants

    nb_enfants = get_int(instance, 'nb_enfants')
    nb_enfants_handicapes = get_int(instance, 'nb_enfants_handicapes')
    nb_enfants_acharge = get_int(instance, 'nb_enfants_acharge')

    # ressources
    salaire = get_int(instance, 'ressources/salaire')
    pension = get_int(instance, 'ressources/pension')
    allocations = get_int(instance, 'ressources/allocations')
    has_autres_revenus = get_bool(instance, 'ressources/autres-sources-revenu')
    autres_revenus = [
        (revenu.get('source-revenu'), get_int(revenu, 'montant-revenu'))
        for revenu in instance.get('ressources/autres_revenus', [])]
    total_autres_revenus = get_int(instance, 'ressources/total_autres_revenus')

    # charges
    loyer = get_int(instance, 'charges/loyer')
    impot = get_int(instance, 'charges/impot')
    dettes = get_int(instance, 'charges/dettes')
    aliments = get_int(instance, 'charges/aliments')
    sante = get_int(instance, 'charges/sante')
    autres_charges = get_int(instance, 'charges/autres_charges')

    # habitat
    type_habitat = get_other(instance, 'habitat/type')
    materiau_habitat = get_other(instance, 'habitat/materiau')

    # antecedents
    # antecedents = instance.get('antecedents', {})
    antecedents_personnels = instance.get('antecedents/personnels')
    antecedents_personnels_details = instance.get(
        'antecedents/personnels-details') or BLANK
    antecedents_familiaux = instance.get('antecedents/familiaux')
    antecedents_familiaux_details = instance.get(
        'antecedents/familiaux-details') or BLANK
    antecedents_sociaux = instance.get('antecedents/sociaux')
    antecedents_sociaux_details = instance.get(
        'antecedents/sociaux-details') or BLANK

    situation_actuelle = instance.get('situation-actuelle') or BLANK
    diagnostic = instance.get('diagnostic') or BLANK
    recommande_assistance = get_bool(instance, 'observation') or BLANK

    c = canvas.Canvas(pdf_form, pagesize=A4)
    c.setLineWidth(.3)
    row = 800
    right_col = 70
    interligne = 10
    c.setFont('Courier', 11)
    # Headers
    c.drawString(right_col, row, 'MINISTÈRE DE LA SOLIDARITÉ')
    c.drawString(right_col + 335, row, 'REPUBLIQUE DU MALI')
    row -= interligne
    c.drawString(right_col, row, 'DE L’ACTION HUMANITAIRE')
    c.drawString(right_col + 320, row, 'UN PEUPLE UN BUT UNE FOI')
    row -= interligne
    c.drawString(right_col, row, 'ET DE LA RECONSTRUCTION DU NORD')
    row -= interligne * 2
    c.drawString(right_col, row,
                 'AGENCE NATIONALE D’ASSISTANCE MEDICALE (ANAM)')
    row -= interligne
    c.setFont('Courier-Bold', 11)
    c.drawCentredString(width / 2, row, 'CONFIDENTIEL')
    row -= interligne * 2
    c.setFont('Courier', 10)
    c.drawCentredString(width / 2, row, 'FICHE D’ENQUETE SOCIALE N°{num}/2016'
                        .format(num=numero_enquete))
    # End header
    row -= interligne * 2
    c.drawString(right_col, row,  'Identifiant enquêteur : ' +
                 identifiant_enqueteur)
    row -= interligne
    c.drawString(right_col, row, 'Objet de l’enquête : ' +
                 objet_enquete)
    row -= interligne
    c.drawString(right_col, row, 'Enquête demandée par : ' + demandeur)
    row -= interligne
    # enquêté
    print(name, sexe, situation_matrioniale)
    c.drawString(right_col, row, concat([
        'Concernant ' + name, sexe, situation_matrioniale]))
    row -= interligne
    c.drawString(right_col, row, naissance + ' à ' + lieu_naissance)
    row -= interligne
    c.drawString(right_col, row, 'Père : ' + name_pere)
    row -= interligne
    c.drawString(right_col, row, 'Mère : ' + name_mere)
    row -= interligne
    c.drawString(right_col, row,
                 'Profession : ' + profession)
    row -= interligne
    c.drawString(right_col, row, 'Adresse : ' + adresse)
    row -= interligne
    c.drawString(right_col, row, "N° NINA : " + nina)
    row -= interligne

    if telephones == []:
        c.drawString(right_col, row, BLANK)
    else:
        c.drawString(right_col, row, "Téléphones : {}".format(
            ' / '.join(telephones)))
    row -= interligne
    c.setFont('Courier-Bold', 11)
    c.drawString(right_col, row, 'COMPOSITION DE LA FAMILLE :')
    row -= interligne
    c.drawCentredString(width / 2, row, 'Situation des Epouses :')
    row -= interligne
    c.setFont('Courier', 10)

    # epouses
    epouses = instance.get('epouses', [])
    if epouses == []:
        c.drawString(right_col, row, BLANK)
        row -= interligne

    for nb, epouse in enumerate(epouses):
        nom_epouse, prenoms_epouse, name_epouse = get_nom(
            epouse, p='epouses/e_')
        nom_pere_epouse, prenoms_pere_epouse, name_pere_epouse = get_nom(
            epouse, p='epouses/e_p_')
        nom_mere_epouse, prenoms_mere_epouse, name_mere_epouse = get_nom(
            epouse, p='epouses/e_m_')

        region_epouse, cercle_epouse, commune_epouse, lieu_naissance_epouse = \
            get_lieu_naissance(epouse, 'epouses/e_')
        type_naissance_epouse, annee_naissance_epouse, \
            ddn_epouse, naissance_epouse = get_dob(epouse, 'epouses/e_', True)
        profession_epouse = get_other(epouse, 'epouses/e_profession')
        nb_enfants_epouse = get_int(epouse, 'epouses/e_nb_enfants', 0)
        row -= interligne
        c.setFont('Courier-Bold', 11)
        c.drawString(right_col, row, "EPOUSE {} :".format(nb + 1))
        c.setFont('Courier', 10)
        row -= interligne
        c.drawString(right_col, row, concat(
            [name_epouse, str(nb_enfants_epouse) + " enfant{p}".format(
                p="s" if nb_enfants_epouse > 1 else "")]))
        row -= interligne
        c.drawString(right_col, row, "{naissance} à {lieu_naissance}".format(
            naissance=naissance_epouse, lieu_naissance=lieu_naissance_epouse))
        row -= interligne
        c.drawString(right_col, row,
                     "Père : {name_pere}".format(name_pere=nom_pere_epouse))
        row -= interligne
        c.drawString(right_col, row,
                     "Mère : {name_mere}".format(name_mere=nom_mere_epouse))
        row -= interligne
        c.drawString(right_col, row, "Profession : {profession}".format(
            profession=profession_epouse))
    row -= interligne
    c.setFont('Courier-Bold', 11)
    c.drawCentredString(width / 2, row, "Situation des Enfants :")
    c.setFont('Courier', 10)
    row -= interligne
    # enfants
    enfants = instance.get('enfants', [])

    if enfants == []:
        c.drawString(right_col, row, BLANK)
        row -= interligne

    for nb, enfant in enumerate(enfants):
        nom_enfant, prenoms_enfant, name_enfant = get_nom(
            enfant, p='enfants/enfant_')
        nom_autre_parent, prenoms_autre_parent, name_autre_parent = \
            get_nom(instance, s='-autre-parent')
        region_enfant, cercle_enfant, commune_enfant, \
            lieu_naissance_enfant = get_lieu_naissance(
                enfant, 'enfants/enfant_')
        type_naissance_enfant, annee_naissance_enfant, \
            ddn_enfant, naissance_enfant = get_dob(enfant, 'enfants/enfant_')
        # situation
        scolarise, scolarise_text = get_bool(
            enfant, 'enfants/situation/scolarise')
        handicape, handicape_text = get_bool(
            enfant, 'enfants/situation/handicape')
        acharge, acharge_text = get_bool(enfant, 'enfants/situation/acharge')
        nb_enfant_handicap = get_int(enfant, 'enfants/nb_enfant_handicap')
        nb_enfant_acharge = get_int(enfant, 'enfants/nb_enfant_acharge')

        row -= interligne
        logger.debug(name_autre_parent)
        c.drawString(right_col, row, "{nb}. {enfant}".format(
            nb=nb + 1, enfant=concat([name_enfant or BLANK, naissance_enfant,
                                      "à {lieu}".format(
                                          lieu=lieu_naissance_enfant),
                                      scolarise_text, handicape_text,
                                      name_autre_parent])))

    row -= interligne * 2
    c.setFont('Courier-Bold', 11)
    c.drawCentredString(
        width / 2, row, "AUTRES PERSONNES à la charge de l’enquêté")
    c.setFont('Courier', 10)
    row -= interligne

    # autres
    autres = instance.get('autres', [])

    if autres == []:
        c.drawString(right_col, row, BLANK)
        row -= interligne

    for nb, autre in enumerate(autres):
        nom_autre, prenoms_autre, name_autre = get_nom(autre, p='autre_')

        region_autre, cercle_autre, commune_autre, \
            lieu_naissance_autre = get_lieu_naissance(autre, 'autre_')
        type_naissance_autre, annee_naissance_autre, \
            ddn_autre, naissance_autre = get_dob(autre, 'autre_')
        parente_autre = get_other(autre, 'autre_parente')
        profession_autre = get_other(autre, 'autre_profession')

        c.drawString(right_col, row, "{nb}. {enfant}".format(
            nb=nb + 1, enfant=concat([name_autre or BLANK, naissance_autre,
                                      "à {lieu}".format(
                                          lieu=lieu_naissance_autre),
                                      parente_autre, profession_autre])))

        row -= interligne
    row -= interligne

    # ressources
    c.setFont('Courier-Bold', 11)
    c.drawString(
        right_col, row, "RESSOURCES ET CONDITIONS DE VIE DE L’ENQUETÉ (E)")
    c.setFont('Courier', 10)
    row -= interligne
    c.drawString(
        right_col, row, concat(["Salaire : {}/mois".format(salaire),
                                "Pension : {}/mois".format(pension),
                                "Allocations : {}/mois".format(allocations)],
                               sep=". "))
    autres_revenus_f = ["[{}/{}]".format(source_revenu, montant_revenu)
                        for source_revenu, montant_revenu in autres_revenus]
    row -= interligne
    c.drawString(
        right_col, row, "Autre: {}".format(concat(autres_revenus_f, sep=". ")))

    row -= interligne * 2
    c.setFont('Courier-Bold', 11)
    c.drawString(right_col, row,
                 "LES CHARGES DE L’ENQUETÉ "
                 "(Préciser le montant et la période)")
    c.setFont('Courier', 10)

    row -= interligne
    c.drawString(
        right_col, row, concat(["Loyer : {}".format(loyer),
                                "Impot : {}".format(impot),
                                "Dettes : {}".format(
                                    dettes), "Aliments : {}".format(aliments),
                                "Santé : {}".format(sante), ], sep=". "))
    row -= interligne
    c.drawString(
        right_col, row, "Autres Charges : {}".format(autres_charges))
    row -= interligne
    c.drawString(right_col, row,
                 "HABITAT : {}"
                 .format(concat([type_habitat, materiau_habitat])))
    c.setFont('Courier-Bold', 11)
    row -= interligne * 2
    c.drawString(
        right_col, row, "EXPOSÉ DETAILLÉ DES FAITS :")
    c.setFont('Courier', 10)
    row -= interligne

    # antecedents
    c.drawString(
        right_col, row, "Antécédents personnels :")
    row -= interligne
    c.drawString(
        right_col, row, concat(antecedents_personnels))
    row -= interligne
    c.drawString(
        right_col, row, antecedents_personnels_details)
    row -= interligne
    c.drawString(
        right_col, row, "Antécédents familiaux :")
    row -= interligne
    c.drawString(
        right_col, row, concat(antecedents_familiaux))
    row -= interligne
    c.drawString(
        right_col, row, antecedents_familiaux_details)
    row -= interligne
    c.drawString(
        right_col, row, "Antécédents sociaux :")
    row -= interligne
    c.drawString(
        right_col, row, concat(antecedents_sociaux))
    row -= interligne
    c.drawString(
        right_col, row, antecedents_sociaux_details)
    row -= interligne
    c.drawString(
        right_col, row, "Situation actuelle :")
    row -= interligne
    c.drawString(
        right_col, row, situation_actuelle)
    row -= interligne
    c.drawString(
        right_col, row, "Diagnostic :")
    row -= interligne
    c.drawString(right_col, row, diagnostic)
    c.setFont('Courier-Bold', 11)
    row -= interligne * 4
    c.drawString(
        right_col, row, "SIGNATURE DE L’ENQUÊTEUR")
    c.drawString(
        right_col + 250, row, "VISA DU CHEF DU SERVICE SOCIAL")

    # QR-code
    c.drawImage(ImageReader(qrcode), 0, 0, 100, 100)

    # Fait le 01-06-2016 à cercle-de-mopti
    # VISA DU CHEF DU SERVICE SOCIAL
    # SIGNATURE DE L’ENQUÊTEUR

    # saving to buffer
    c.save()
    pdf_form.seek(0)  # make sure it's readable

    return pdf_form
