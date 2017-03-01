#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import datetime
import logging
import math

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (Paragraph, Table, TableStyle, Image,
                                SimpleDocTemplate)
from hamed.exports.common import (concat, get_lieu_naissance, get_lieu, get_other,
                                  get_int, get_date, get_dob, get_bool, get_nom)

BLANK = "néant"
logger = logging.getLogger(__name__)


def gen_social_survey_pdf(target):
    instance = target.dataset
    pdf_form = io.BytesIO()

    colwidths = 160
    rowheights = 14
    style = getSampleStyleSheet()["Normal"]
    style.leading = 8
    style.fontSize = 8

    def get_blank_for_list_empty(data_list):
        return BLANK if len(data_list) == 0 else data_list

    # lieu (pas sur papier)
    lieu_region, lieu_cercle, lieu_commune, lieu_village, lieu = get_lieu(
        instance, 'lieu_')
    numero_enquete = instance.get('numero') or ""
    objet_enquete = get_other(instance, 'objet')
    identifiant_enqueteur = instance.get('enqueteur') or BLANK
    demandeur = get_other(instance, 'demandeur')

    # enquêté
    nom, prenoms, name = get_nom(instance, p='enquete/')
    sexe = instance.get('enquete/sexe') or 'masculin'
    is_female = sexe == 'feminin'
    type_naissance, annee_naissance, ddn, naissance = get_dob(
        instance, 'enquete/', is_female)
    region_naissance, cercle_naissance, commune_naissance, \
        lieu_naissance = get_lieu_naissance(instance, 'enquete/')

    # enquêté / instance
    nom_pere, prenoms_pere, name_pere = get_nom(
        instance, p='enquete/filiation/', s='-pere')
    nom_mere, prenoms_mere, name_mere = get_nom(
        instance, p='enquete/filiation/', s='-mere')

    situation_matrioniale = instance.get(
        'enquete/situation-matrimoniale', BLANK)
    profession = get_other(instance, 'enquete/profession')
    adresse = instance.get('enquete/adresse', BLANK)
    nina = instance.get('nina', BLANK)
    telephones = instance.get('enquete/telephones', [])
    if len(telephones) == 0:
        telephones = BLANK
    else:
        telephones = concat([str(tel.get('enquete/telephones/numero'))
                             for tel in telephones])
    nb_epouses = get_int(instance, 'nb_epouses')

    # enfants
    logger.info("enfants")
    nb_enfants = get_int(instance, 'nb_enfants', 0)
    nb_enfants_handicapes = get_int(instance, 'nb_enfants_handicapes', 0)
    nb_enfants_acharge = get_int(instance, 'nb_enfants_acharge', 0)

    # ressources
    salaire = get_int(instance, 'ressources/salaire')
    pension = get_int(instance, 'ressources/pension')
    allocations = get_int(instance, 'ressources/allocations')
    has_autres_revenus = get_bool(instance, 'ressources/autres-sources-revenu')
    autres_revenus = [
        (revenu.get('ressources/autres_revenus/source-revenu'),
         get_int(revenu, 'ressources/autres_revenus/montant-revenu'))
        for revenu in instance.get('ressources/autres_revenus', [])]
    total_autres_revenus = get_int(instance, 'ressources/total_autres_revenus')
    autres_revenus_f = concat(["[{} : {}]".format(source_revenu, montant_revenu)
                               for source_revenu, montant_revenu in autres_revenus], sep=". ")
    # charges
    loyer = get_int(instance, 'charges/loyer')
    impot = get_int(instance, 'charges/impot')
    dettes = get_int(instance, 'charges/dettes')
    aliments = get_int(instance, 'charges/aliments')
    sante = get_int(instance, 'charges/sante')
    autres_charges = [
        (charge.get('charges/autres_charges/nature'),
         get_int(charge, 'charges/autres_charges/montant_charge'))
        for charge in instance.get('charges/autres_charges', [])]

    autres_charges_f = concat(["[{} : {}]".format(nature, montant_charge)
                               for nature, montant_charge in autres_charges], sep=". ")

    # habitat
    type_habitat = get_other(instance, 'habitat/type')
    materiau_habitat = get_other(instance, 'habitat/materiau')

    # antecedents
    antecedents_personnels = instance.get('antecedents/personnels')
    antecedents_personnels_details = instance.get(
        'antecedents/personnels-details') or BLANK
    antecedents_familiaux = instance.get('antecedents/familiaux')
    antecedents_familiaux_details = instance.get(
        'fantecedents/amiliaux-details') or BLANK
    antecedents_sociaux = instance.get('antecedents/sociaux')
    antecedents_sociaux_details = instance.get(
        'antecedents/sociaux-details') or BLANK

    situation_actuelle = instance.get('situation-actuelle') or BLANK
    diagnostic = instance.get('diagnostic') or BLANK
    diagnostic_details = instance.get('diagnostic-details') or BLANK
    recommande_assistance = get_bool(instance, 'observation') or BLANK

    def addQRCodeToFrame(canvas, doc):
        text = "ID: {}".format(target.identifier)
        qrsize = 100
        x = doc.width + doc.rightMargin - 40
        y = math.ceil(doc.height * 0.9)

        canvas.saveState()
        canvas.drawImage(
            ImageReader(target.get_qrcode()), x - qrsize / 2, y, qrsize, qrsize)
        canvas.drawCentredString(x, y, text)
        canvas.restoreState()

    def draw_paragraph_title(text):
        return Paragraph("""<para align=center spaceb=10 spaceafter=10><b><font size=12>{}</font>
                  </b></para>""".format(text), style)

    def draw_paragraph_sub_title_h2(text):
        return Paragraph("""<para align=left spaceb=8 spaceafter=8><b><font size=10>{}</font>
                  </b></para>""".format(text), style)

    def draw_paragraph_sub_title_h3(text):
        return Paragraph("""<para align=left spaceb=5 spaceafter=8><b><font size=8>{}</font>
                  </b></para>""".format(text), style)

    def style_label(label):
        return "<font size=8 ><u>{}</u></font> : ".format(label)

    def draw_paragraph(label, text, indent=0):
        if label != "":
            label = style_label(label)
        return Paragraph(
            """<para align=left leftIndent={indent} spaceb=2 spaceafter=1> {label} {text}</para>""".format(
                indent=indent, label=label, text=text), style)

    def body_table(data):
        table_data = Table(data)
        table_data.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 8),
                                        ('ALIGN', (1, 1), (1, -1), 'LEFT')]))
        return table_data

    doc = SimpleDocTemplate(pdf_form, pagesize=A4, leftMargin=35)
    logger.info("Headers")
    headers = [["MINISTÈRE DE LA SOLIDARITÉ", "",  "    REPUBLIQUE DU MALI"],
               ["DE L’ACTION HUMANITAIRE", "", "UN PEUPLE UN BUT UNE FOI"],
               ["ET DE LA RECONSTRUCTION DU NORD", "", ""],
               ["AGENCE NATIONALE D’ASSISTANCE MEDICALE (ANAM)", "", ""]]
    headers_t = Table(headers, rowHeights=rowheights, colWidths=colwidths)
    headers_t.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 8), ]))

    story = []
    story.append(headers_t)
    story.append(draw_paragraph_title("CONFIDENTIEL"))

    numero_enquete_t = Table([["FICHE D’ENQUETE SOCIALE N°.............../{year}"
                               .format(year=datetime.datetime.now().year), ]])
    numero_enquete_t.setStyle(TableStyle(
        [('BOX', (0, 0), (-1, -1), 0.30, colors.black), ]))
    story.append(numero_enquete_t)
    story.append(draw_paragraph("Identifiant enquêteur", numero_enquete))
    story.append(draw_paragraph("Objet de l’enquête", objet_enquete))
    story.append(draw_paragraph("Enquête demandée par", demandeur))
    story.append(draw_paragraph_sub_title_h2("Enquêté"))
    logger.info("Enquêté")
    story.append(
        draw_paragraph("Concernant", concat([name, sexe, situation_matrioniale])))
    story.append(
        draw_paragraph("", "{} à {}".format(naissance, lieu_naissance)))
    logger.info("Parent")
    story.append(draw_paragraph("N° NINA", nina))
    story.append(draw_paragraph("Père", name_pere))
    story.append(draw_paragraph("Mère", name_mere))
    story.append(
        draw_paragraph("Profession", profession))
    story.append(draw_paragraph("Adresse", adresse))
    story.append(
        draw_paragraph("Téléphones", telephones))
    story.append(draw_paragraph_sub_title_h2("COMPOSITION DE LA FAMILLE"))
    story.append(draw_paragraph_sub_title_h3("Situation des Epouses"))
    epouses = instance.get('epouses', [])
    logger.info("Epouses")
    if epouses == []:
        story.append(draw_paragraph("", BLANK))
    else:
        for nb, epouse in enumerate(epouses):
            nom_epouse, prenoms_epouse, name_epouse = get_nom(
                epouse, p='epouses/e_')
            nom_pere_epouse, prenoms_pere_epouse, name_pere_epouse = get_nom(
                epouse, p='epouses/e_p_')
            nom_mere_epouse, prenoms_mere_epouse, name_mere_epouse = get_nom(
                epouse, p='epouses/e_m_')
            region_epouse, cercle_epouse, commune_epouse, lieu_naissance_epouse = get_lieu_naissance(
                epouse, 'epouses/e_')
            type_naissance_epouse, annee_naissance_epouse, ddn_epouse, naissance_epouse = get_dob(
                epouse, 'epouses/e_', True)
            profession_epouse = get_other(epouse, 'epouses/e_profession')
            nb_enfants_epouse = get_int(epouse, 'epouses/e_nb_enfants', 0)
            story.append(draw_paragraph_sub_title_h3(
                "épouse : {}".format(nb + 1)))
            epouses = concat([name_epouse, str(nb_enfants_epouse) +
                              " enfant{p}".format(p="s" if nb_enfants_epouse > 1 else ""), profession_epouse])
            story.append(draw_paragraph("", epouses, 10))
            dob = "{naissance} à {lieu_naissance}".format(
                naissance=naissance_epouse, lieu_naissance=lieu_naissance_epouse)
            story.append(draw_paragraph("", dob, 10))
            story.append(draw_paragraph("", concat(
                ["{} {}".format(style_label("Père"), name_pere_epouse),
                 "{} {}".format(style_label("Mère"), name_mere_epouse)]), 10))
    # enfants
    story.append(draw_paragraph_sub_title_h3("Situation des Enfants"))
    logger.debug("Child")
    enfants = instance.get('enfants', [])
    if enfants == []:
        story.append(draw_paragraph("", BLANK))
    else:
        for nb, enfant in enumerate(enfants):
            nom_enfant, prenoms_enfant, name_enfant = get_nom(
                enfant, p='enfants/enfant_')
            nom_autre_parent, prenoms_autre_parent, name_autre_parent = get_nom(
                enfant, p='enfants/', s='-autre-parent')
            region_enfant, cercle_enfant, commune_enfant, lieu_naissance_enfant = get_lieu_naissance(
                enfant, 'enfants/enfant_')
            type_naissance_enfant, annee_naissance_enfant, ddn_enfant, naissance_enfant = get_dob(
                enfant, 'enfants/enfant_')
            # situation
            scolarise, scolarise_text = get_bool(
                enfant, 'enfants/situation/scolarise')
            handicape, handicape_text = get_bool(
                enfant, 'enfants/situation/handicape')
            acharge, acharge_text = get_bool(
                enfant, 'enfants/situation/acharge')
            # Scolarisé = SC; Handicapé = HP; À charge = AC; Autre parent = AP
            story.append(draw_paragraph("", "{nb}. {enfant}".format(
                nb=nb + 1, enfant=concat([name_enfant, naissance_enfant,
                                          "à {lieu}".format(lieu=lieu_naissance_enfant), "SC ?: {}".format(scolarise_text), "HD ?: {}".format(
                                              handicape_text), "AC ? : {}".format(acharge_text), "AP ? : {}".format(name_autre_parent)]))))
        nb_enfant = get_int(instance, 'nb_enfants')
        nb_enfant_handicap = get_int(instance, 'nb_enfants_handicapes')
        nb_enfant_acharge = get_int(instance, 'nb_enfant_acharge')
        nb_enfants_scolarises = get_int(instance, 'nb_enfants_scolarises')
        story.append(draw_paragraph("", concat(["Nombre d'enfant : {}".format(nb_enfant),
                                                "Scolarisés : {}".format(
                                                    nb_enfants_scolarises),
                                                "Handicapé : {}".format(
                                                    nb_enfant_handicap),
                                                "À charge : {}".format(nb_enfants_acharge)])))
    # autres
    story.append(draw_paragraph_sub_title_h2(
        "AUTRES PERSONNES à la charge de l’enquêté"))
    autres = instance.get('autres', [])
    if autres == []:
        story.append(draw_paragraph(BLANK))
    else:
        logger.debug("Other")
        for nb, autre in enumerate(autres):
            nom_autre, prenoms_autre, name_autre = get_nom(
                autre, p='autres/autre_')
            region_autre, cercle_autre, commune_autre, lieu_naissance_autre = get_lieu_naissance(
                autre, 'autres/autre_')
            type_naissance_autre, annee_naissance_autre, ddn_autre, naissance_autre = get_dob(
                autre, 'autres/autre_')
            parente_autre = get_other(autre, 'autres/autre_parente')
            profession_autre = get_other(autre, 'autres/autre_profession')
            story.append(draw_paragraph("", "{nb}. {enfant}".format(nb=nb + 1, enfant=concat(
                [name_autre or BLANK, naissance_autre, "à {lieu}".format(
                    lieu=lieu_naissance_autre), parente_autre, profession_autre])), 10))
    # ressources
    logger.debug("Ressources")
    story.append(
        draw_paragraph_sub_title_h2("RESSOURCES ET CONDITIONS DE VIE DE L’ENQUETE (E)"))
    story.append(draw_paragraph_sub_title_h3("RESSOURCES"))
    story.append(
        draw_paragraph("", concat(["Salaire : {}/mois".format(salaire),
                                   "Pension : {}/mois".format(pension),
                                   "Allocations : {}/mois".format(allocations)], sep=". ")))
    story.append(draw_paragraph("Autres revenus", autres_revenus_f))
    story.append(draw_paragraph_sub_title_h3("CHARGES"))
    story.append(
        draw_paragraph("", concat(["Loyer : {}/mois".format(loyer),
                                   "Impot : {}/an".format(impot),
                                   "Dettes : {}".format(dettes),
                                   "Aliments : {}/mois".format(aliments),
                                   "Santé : {}/mois".format(sante), ], sep=". ")))
    story.append(draw_paragraph("Autres Charges", autres_charges_f))
    story.append(draw_paragraph_sub_title_h3("HABITAT"))
    story.append(
        draw_paragraph("", concat(["Type d’habitat : {}".format(type_habitat),
                                   "Principal matériau des murs du logement : {}".format(materiau_habitat)])))
    story.append(draw_paragraph_sub_title_h2("Exposé détaillé des faits"))
    # antecedents
    logger.debug("Antecedents")
    story.append(
        draw_paragraph("Antécédents personnels", concat(antecedents_personnels)))
    story.append(draw_paragraph(
        "Détails Antécédents personnels", antecedents_personnels_details))
    story.append(
        draw_paragraph("Antécédents familiaux", antecedents_familiaux))
    story.append(
        draw_paragraph("Détails Antécédents familiaux", antecedents_familiaux_details))
    story.append(draw_paragraph("Antécédents sociaux", antecedents_sociaux))
    story.append(
        draw_paragraph("Détails Antécédents sociaux", antecedents_sociaux_details))
    story.append(
        draw_paragraph("Situation actuelle", concat(situation_actuelle)))
    story.append(draw_paragraph("Diagnostic", diagnostic))
    story.append(draw_paragraph("Diagnostic details", diagnostic_details))
    # signature_dict = instance.get("signature")
    # img = ""
    # if signature_dict:
    #     dir_media = os.path.join(output_folder, "signature_{}".format(
    #         signature_dict.get("filename")))
    #     img = Image(dir_media, width=80, height=82)

    # signature = [["SIGNATURE DE L’ENQUÊTEUR", "",
    #               "VISA DU CHEF DU SERVICE SOCIAL"], [img, ""]]
    # signature_t = Table(signature, colWidths=150, rowHeights=90)
    # signature_t.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 8), ]))
    # story.append(signature_t)

    # Fait le 01-06-2016 à cercle-de-mopti
    # VISA DU CHEF DU SERVICE SOCIAL
    # SIGNATURE DE L’ENQUÊTEUR
    doc.build(story, onFirstPage=addQRCodeToFrame)

    pdf_form.seek(0)  # make sure it's readable

    return pdf_form
