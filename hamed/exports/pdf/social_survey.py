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
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (Paragraph, Table, TableStyle, Image,
                                SimpleDocTemplate)

from hamed.ona import download_media
from hamed.exports.common import (concat, get_lieu_naissance, get_lieu,
                                  get_other, clean_phone_number_str, get_int,
                                  get_dob, get_bool, get_nom, number_format)
from hamed.form_labels import get_label_for

BLANK = "néant"
logger = logging.getLogger(__name__)


def gen_social_survey_pdf(target):
    instance = target.dataset
    pdf_form = io.BytesIO()

    style = getSampleStyleSheet()["Normal"]
    style.leading = 8
    style.fontSize = 8

    # lieu (pas sur papier)
    lieu_region, lieu_cercle, lieu_commune, lieu_village, lieu = get_lieu(
        instance, 'lieu_')
    # numero_enquete = instance.get('numero') or ""
    objet_enquete = get_other(instance, 'objet')
    identifiant_enqueteur = instance.get('enqueteur') or BLANK
    demandeur = get_other(instance, 'demandeur')

    # enquêté
    nom, prenoms, name = get_nom(instance, p='enquete/')
    sexe = instance.get('enquete/sexe') or 'masculin'
    is_female = sexe == 'feminin'
    type_naissance, annee_naissance, ddn, naissance, \
        date_or_year = get_dob( instance, 'enquete/', is_female)
    region_naissance, cercle_naissance, commune_naissance, \
        lieu_naissance = get_lieu_naissance(instance, 'enquete/')

    # enquêté / instance
    nom_pere, prenoms_pere, name_pere = get_nom(
        instance, p='enquete/filiation/', s='-pere')
    nom_mere, prenoms_mere, name_mere = get_nom(
        instance, p='enquete/filiation/', s='-mere')

    situation_matrimoniale = instance.get(
        'enquete/situation-matrimoniale', BLANK)
    profession = get_other(instance, 'enquete/profession')
    adresse = instance.get('enquete/adresse', BLANK)
    nina = instance.get('nina', BLANK)
    telephones = instance.get('enquete/telephones', [])
    if len(telephones) == 0:
        telephones = BLANK
    else:
        telephones = concat([clean_phone_number_str(
            str(tel.get('enquete/telephones/numero'))) for tel in telephones])
    nb_epouses = get_int(instance, 'nb_epouses')

    # enfants
    logger.info("enfants")
    nb_enfants = get_int(instance, 'nb_enfants', 0)
    nb_enfants_handicapes = get_int(instance, 'nb_enfants_handicapes', 0)
    nb_enfants_acharge = get_int(instance, 'nb_enfants_acharge', 0)
    nb_autres_personnes =  get_int(instance, 'nb_autres_personnes', 0)
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
    autres_revenus_f = concat(["[{} : {}]".format(get_label_for(
        "source-revenu", source_revenu), montant_revenu)
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
    conditions_hygiene = get_other(instance, 'habitat/conditions_hygiene')

    # antecedents
    antecedents_personnels = instance.get('antecedents/personnels')
    antecedents_personnels_details = instance.get(
        'antecedents/personnels-details', BLANK)
    antecedents_familiaux = instance.get('antecedents/familiaux')
    antecedents_familiaux_details = instance.get(
        'fantecedents/amiliaux-details', BLANK)
    antecedents_sociaux = instance.get('antecedents/sociaux')
    antecedents_sociaux_details = instance.get(
        'antecedents/sociaux-details', BLANK)

    situation_actuelle = instance.get('situation-actuelle', BLANK)
    situation_actuelle_details = instance.get('situation-actuelle-details', BLANK)
    diagnostic = instance.get('diagnostic', BLANK)
    diagnostic_details = instance.get('diagnostic-details', BLANK)
    recommande_assistance, recommande_assistance_text = get_bool(
        instance, 'observation')

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
        return Paragraph("""<para align=center spaceb=10 spaceafter=10><b><font
            size=12>{}</font> </b></para>""".format(text), style)

    def draw_paragraph_sub_title_h2(text):
        return Paragraph("""<para align=left spaceb=8 spaceafter=8><b><font
            size=10>{}</font> </b></para>""".format(text), style)

    def draw_paragraph_sub_title_h3(text):
        return Paragraph("""<para align=left spaceb=5 spaceafter=8><b><font
            size=8>{}</font> </b></para>""".format(text), style)

    def style_label(label):
        return "<font size=8 ><u>{}</u></font> : ".format(label)

    def draw_paragraph(label, text, indent=0):
        if label != "":
            label = style_label(label)
        return Paragraph("""<para align=left leftIndent={indent} spaceb=2
            spaceafter=1> {label} {text}</para>""".format(indent=indent,
                label=label, text=text), style)

    doc = SimpleDocTemplate(pdf_form, pagesize=A4, leftMargin=35)
    logger.info("Headers")
    headers = [["MINISTÈRE DE LA SOLIDARITÉ", "", "",  "REPUBLIQUE DU MALI"],
               ["DE L’ACTION HUMANITAIRE", "", "", "Un Peuple Un But Une Foi"],
               # ["ET DE LA RECONSTRUCTION DU NORD", "", "", ""],
               # ["AGENCE NATIONALE D’ASSISTANCE MEDICALE (ANAM)", "", "", ""]
               ]
    headers_t = Table(headers, rowHeights=12, colWidths=120)
    headers_t.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 8), ]))

    story = []
    story.append(headers_t)
    story.append(draw_paragraph_title("CONFIDENTIEL"))

    numero_enquete_t = Table([
        ["FICHE D’ENQUETE SOCIALE N°................./{year}".format(
            year=datetime.datetime.now().year), ]])
    numero_enquete_t.setStyle(TableStyle([('BOX', (0, 0), (-1, -1),
                                           0.30, colors.black), ]))
    story.append(numero_enquete_t)
    story.append(draw_paragraph("Identifiant enquêteur", identifiant_enqueteur))
    story.append(draw_paragraph("Objet de l’enquête",
                                get_label_for('objet', objet_enquete)))
    story.append(draw_paragraph("Enquête demandée par",
                                get_label_for('demandeur', demandeur)))
    story.append(draw_paragraph_sub_title_h2("Enquêté{}"
                                            .format("e" if is_female else "")))
    logger.info("Enquêté")
    story.append(draw_paragraph("Concernant",
        concat([name,"Homme" if sexe == "masculin" else "Femme",
         get_label_for("situation-matrimoniale", situation_matrimoniale)])))
    story.append(draw_paragraph("Naissance",
        "{} à {}".format(date_or_year, lieu_naissance)))
    logger.info("Parent")
    story.append(draw_paragraph("N° NINA", nina))
    story.append(draw_paragraph("",
            concat(["{} {}".format(style_label("Père"), name_pere),
                    "{} {}".format(style_label("Mère"), name_mere)])))
    story.append(
        draw_paragraph("Profession", get_label_for('profession', profession)))
    story.append(draw_paragraph("Adresse", adresse))
    story.append(
        draw_paragraph("Téléphones", telephones))
    story.append(draw_paragraph_sub_title_h2("COMPOSITION DE LA FAMILLE"))
    story.append(draw_paragraph_sub_title_h3("Situation des épouses"))
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
            region_epouse, cercle_epouse, commune_epouse, \
                lieu_naissance_epouse = get_lieu_naissance(epouse, 'epouses/e_')
            type_naissance_epouse, annee_naissance_epouse, ddn_epouse, \
                naissance_epouse, date_or_year = get_dob(epouse,
                                                         'epouses/e_', True)
            profession_epouse = get_other(epouse, 'epouses/e_profession')
            nb_enfants_epouse = get_int(epouse, 'epouses/e_nb_enfants', 0)
            story.append(
                draw_paragraph_sub_title_h3("Épouse : {}".format(nb + 1)))
            epouses = concat([name_epouse,
                str(nb_enfants_epouse) + " enfant{p}".format(
                p="s" if nb_enfants_epouse > 1 else ""),
                get_label_for("e_profession", profession_epouse)])
            story.append(draw_paragraph("", epouses, 10))
            dob = "{naissance} à {lieu_naissance}".format(
                naissance=naissance_epouse, lieu_naissance=lieu_naissance_epouse)
            story.append(draw_paragraph("", dob, 10))
            story.append(draw_paragraph("", concat(
                ["{} {}".format(style_label("Père"), name_pere_epouse),
                 "{} {}".format(style_label("Mère"), name_mere_epouse)]), 10))
    # enfants
    story.append(draw_paragraph_sub_title_h3("Situation des enfants (SC : "
        "Scolarisé?, HD : Handicapé?, AC : À charge ?, AP : Autre parent)"))
    logger.debug("Child")
    enfants = instance.get('enfants', [])
    if enfants == []:
        story.append(draw_paragraph("", BLANK))
    else:
        for nb, enfant in enumerate(enfants):
            nom_enfant, prenoms_enfant,\
                name_enfant = get_nom(enfant, p='enfants/enfant_')
            nom_autre_parent, prenoms_autre_parent, name_autre_parent \
                = get_nom(enfant, p='enfants/', s='-autre-parent')
            region_enfant, cercle_enfant, commune_enfant, \
                lieu_naissance_enfant = get_lieu_naissance(
                    enfant, 'enfants/enfant_')
            type_naissance_enfant, annee_naissance_enfant, ddn_enfant, \
                naissance_enfant, date_or_year = get_dob(enfant,
                                                         'enfants/enfant_')
            # situation
            scolarise, scolarise_text = get_bool(enfant,
                'enfants/situation/scolarise')
            handicape, handicape_text = get_bool(enfant,
                'enfants/situation/handicape')
            acharge, acharge_text = get_bool(enfant,
                'enfants/situation/acharge')
            sexe_enfant = get_other(enfant, 'enfants/enfant_sexe')
            story.append(draw_paragraph("","{nb}. {enfant}".format(
                nb=nb + 1, enfant=concat([name_enfant,
                    "M" if sexe_enfant == "masculin" else "F", naissance_enfant,
                    "à {lieu}".format(lieu=lieu_naissance_enfant),
                    "SC : {}".format(get_label_for("scolarise",scolarise_text)),
                    "HD : {}".format(get_label_for("handicape",handicape_text)),
                    "AC : {}".format(get_label_for("acharge", acharge_text)),
                    "AP : {}".format(name_autre_parent)]))))
        nb_enfant = get_int(instance, 'nb_enfants')
        nb_enfant_handicap = get_int(instance, 'nb_enfants_handicapes')
        nb_enfant_acharge = get_int(instance, 'nb_enfant_acharge')
        nb_enfants_scolarises = get_int(instance, 'nb_enfants_scolarises')
        story.append(draw_paragraph("",
            concat(["Nombre d'enfant : {}".format(nb_enfant),
                    "scolarisés : {}".format(nb_enfants_scolarises),
                    "handicapé : {}".format(nb_enfant_handicap),
                    "à charge : {}".format(nb_enfants_acharge)])))
    # autres
    story.append(draw_paragraph_sub_title_h3(
        "Autres persionnes à la charge de l’enquêté{}".format(
                                                    "e" if is_female else "")))
    autres = instance.get('autres', [])
    if autres == []:
        story.append(draw_paragraph("", BLANK))
    else:
        logger.debug("Other")
        for nb, autre in enumerate(autres):
            nom_autre, prenoms_autre, name_autre = \
                get_nom(autre, p='autres/autre_')
            region_autre, cercle_autre, commune_autre, lieu_naissance_autre = \
                get_lieu_naissance(autre, 'autres/autre_')
            type_naissance_autre, annee_naissance_autre, ddn_autre,\
                naissance_autre, date_or_year = get_dob(autre, 'autres/autre_')
            autre_parente = get_other(autre, 'autres/autre_parente')
            autre_profession = get_other(autre, 'autres/autre_profession')
            story.append(draw_paragraph("","{nb}. {enfant}".format(
                nb=nb + 1, enfant=concat([name_autre or BLANK, naissance_autre,
                "à {lieu}".format(lieu=lieu_naissance_autre),
                get_label_for("autre_parente", autre_parente),
                get_label_for("autre_profession", autre_profession)])), 10))

    story.append(draw_paragraph("Nombre de personnes à charge", nb_autres_personnes))
    # ressources
    logger.debug("Ressources")
    story.append(draw_paragraph_sub_title_h2(
        "RESSOURCES ET CONDITIONS DE VIE DE L’ENQUETÉ{}".format(
                                                    "e" if is_female else "")))
    story.append(draw_paragraph_sub_title_h3("Ressources"))
    story.append(draw_paragraph("",concat(
        ["<u>Salaire</u> : {}/mois".format(number_format(salaire)),
        "<u>Pension</u> : {}/mois".format(number_format(pension)),
        "<u>Allocations</u> : {}/mois".format(number_format(allocations))],
         sep=". ")))
    story.append(draw_paragraph("Autres revenus", autres_revenus_f))
    story.append(draw_paragraph_sub_title_h3("Charges"))
    story.append(draw_paragraph("", concat(
        ["<u>Loyer</u> : {}/mois".format(number_format(loyer)),
         "<u>Impôt</u> : {}/an".format(number_format(impot)),
         "<u>Dettes</u> : {}".format(number_format(dettes)),
         "<u>Aliments</u> : {}/mois".format(number_format(aliments)),
         "<u>Santé</u> : {}/mois".format(number_format(sante)), ], sep=". ")))
    story.append(draw_paragraph("Autres Charges", autres_charges_f))
    story.append(draw_paragraph_sub_title_h3("Habitat"))
    story.append(draw_paragraph("", concat([
        "<u>Type d’habitat</u> : {}".format(get_label_for("type",type_habitat)),
        "<u>Principal matériau des murs du logement</u> : {}".format(
            get_label_for("materiau",materiau_habitat)),
        "<u>Conditions d'hygiène</u> : {}".format(conditions_hygiene)
        ])))
    # story.append(draw_paragraph("Conditions d'hygiène", conditions_hygiene))
    story.append(draw_paragraph_sub_title_h2("EXPOSÉ DÉTAILLÉ DES FAITS"))
    # antecedents
    logger.debug("Antecedents")
    story.append(draw_paragraph("Antécédents personnels", concat(
        [get_label_for("personnels", ap) for ap in antecedents_personnels.split()])))
    story.append(draw_paragraph("Détails antécédents personnels",
        antecedents_personnels_details))
    story.append(draw_paragraph("Antécédents familiaux",
         get_label_for("familiaux", antecedents_familiaux)))
    story.append(draw_paragraph( "Détails antécédents familiaux",
        antecedents_familiaux_details))
    story.append(draw_paragraph("Antécédents sociaux",
        get_label_for("sociaux",antecedents_sociaux)))
    story.append(draw_paragraph("Détails antécédents sociaux",
        antecedents_sociaux_details))
    story.append(draw_paragraph("Situation actuelle", concat([get_label_for(
        "situation-actuelle", sa) for sa in situation_actuelle.split()])))
    story.append(draw_paragraph("Situation actuelle details", situation_actuelle_details))
    story.append(draw_paragraph("Diagnostic",
        get_label_for("diagnostic", diagnostic)))
    story.append(draw_paragraph("Diagnostic details", diagnostic_details))
    story.append(draw_paragraph(
        "L'enquêteur recommande une assistance sociale ?",get_label_for(
            "observation", recommande_assistance_text)))

    sig_attachment = target.get_attachment('signature')
    signature = download_media(sig_attachment.get('download_url'))
    signature_img = Image(signature, width=80, height=82)
    signature = [["SIGNATURE DE L’ENQUÊTEUR", "", "",
                  "VISA DU CHEF DU SERVICE SOCIAL"], [signature_img, ""]]
    signature_t = Table(signature,  rowHeights=80, colWidths=110)
    signature_t.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 8),
                                     ('TOPPADDING', (1, 1), (-1, -1), 20),
                                     ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    story.append(signature_t)
    # VISA DU CHEF DU SERVICE SOCIAL
    # SIGNATURE DE L’ENQUÊTEUR
    doc.build(story, onFirstPage=addQRCodeToFrame)

    pdf_form.seek(0)  # make sure it's readable

    return pdf_form
