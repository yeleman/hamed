#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import logging
import math

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph, Table, TableStyle, SimpleDocTemplate)

from django.utils import timezone
from django.template.defaultfilters import date as date_filter

from hamed.exports.common import (get_lieu_naissance, get_lieu, get_other,
                                  get_date, get_dob, get_nom)
from hamed.form_labels import get_label_for

BLANK = "néant"
logger = logging.getLogger(__name__)


def gen_residence_certificate_pdf(target):
    instance = target.dataset
    pdf_form = io.BytesIO()

    styles = getSampleStyleSheet()
    n_style = styles["Normal"]
    n_style.leading = 15

    def addQRCodeToFrame(canvas, doc):
        text = "ID: {}".format(target.identifier)
        qrsize = 100
        x = doc.width + doc.rightMargin
        y = math.ceil(doc.height * 0.9)

        canvas.saveState()
        canvas.drawImage(
            ImageReader(target.get_qrcode()), x - qrsize / 2, y, qrsize, qrsize)
        canvas.drawCentredString(x, y, text)
        canvas.restoreState()

    def draw_paragraph_title(text):
        return Paragraph("""<para align=center spaceb=20 spacea=50>
            <b><font size=12>{}</font></b></para>""".format(text), n_style)

    def draw_paragraph(data, indent=30, align="left"):
        return Paragraph("""<para align={align} leftIndent={indent}
                         spaceb=2 spaceafter=1>{data}</para>""".format(
                            align=align, indent=indent, data=data), n_style)

    doc = SimpleDocTemplate(pdf_form, pagesize=A4)

    nom, prenoms, name = get_nom(instance, p='enquete/')
    sexe = instance.get('enquete/sexe')
    is_female = sexe == 'feminin'

    type_naissance, annee_naissance, ddn, naissance, \
        date_or_year = get_dob(instance, 'enquete/', is_female)
    region_naissance, cercle_naissance, commune_naissance, \
        lieu_naissance = get_lieu_naissance(instance, 'enquete/')

    nom_pere, prenoms_pere, name_pere = get_nom(
        instance, p='enquete/filiation/', s='-pere')
    nom_mere, prenoms_mere, name_mere = get_nom(
        instance, p='enquete/filiation/', s='-mere')

    situation_matrioniale = instance.get(
        'enquete/situation-matrimoniale', BLANK)
    adresse = instance.get('enquete/adresse', BLANK)
    profession = get_other(instance, 'enquete/profession')
    cercle = target.collect.cercle
    commune = target.collect.commune
    localisation_enquete = instance.get("localisation-enquete/lieu_village")

    headers = [["MINISTERE DE L'ADMINISTRATION", "", "",  "REPUBLIQUE DU MALI"],
               ["TERRITORIALE DE LA DECENTRALISATION",
                   "", "", "Un Peuple Un But Une Foi"],
               ["ET DE LA REFORME DE L'ETAT", "", "", "**" * 10],
               ["**" * 10, "", "", ""],
               ["CERCLE DE {} ".format(cercle.upper()), "", "", ""],
               ["**" * 10, "", "", ""],
               ["COMMUNE DE {}".format(commune.upper()), "", "", ""], ]
    headers_table = Table(headers, rowHeights=12, colWidths=120)
    headers_table.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 8),
                                       ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))

    # type_piece = instance.get('type-piece')
    # if type_piece == "acte-naissance":
    #     num_piece_and_centre = \
    #         "Acte de naissance n° {} délivrée à {}.".format(
    #         instance.get('acte-naissance/numero_acte_naissance'),
    #         instance.get('acte-naissance/centre_acte_naissance'))
    # elif type_piece == "piece-didentite":
    #     num_piece_and_centre = \
    #     "Carte d'identité nationale n° {} délivrée à {}.".format(
    #         instance.get('carte_identite/numero_carte_identite'),
    #         instance.get('carte_identite/centre_carte_identite'))
    # else:
    #     num_piece_and_centre = "Carte NINA n° {}".format(
    #         instance.get('nina', BLANK))

    story = []
    story.append(headers_table)
    story.append(draw_paragraph_title("CERTIFICAT D'IDENTITE ET DE RESIDENCE"))
    story.append(draw_paragraph(
        "Nous, {maire}, maire de la commune de {commune}"
        .format(maire=target.collect.mayor, commune=commune)))
    story.append(draw_paragraph(
        " Certifions que {} {}".format("Mme" if is_female else "M.", name)))
    story.append(
        draw_paragraph("{} à {}".format(naissance.capitalize(), lieu_naissance)))
    story.append(draw_paragraph(
        "{sexe} de {name_pere}  et de {name_mere}.".format(sexe="Fille "
        if is_female else "Fils", name_pere=name_pere, name_mere=name_mere)))
    story.append(draw_paragraph(
        "Exerçant la profession : {}".format(get_label_for('profession', profession))))

    story.append(draw_paragraph("Réside depuis plus de trois (3) mois à {village_enquete} dans la "
        "commune de {commune}.".format(village_enquete=localisation_enquete.upper(),
                                       commune=commune)))
    # story.append(draw_paragraph(num_piece_and_centre))
    story.append(draw_paragraph("En foi de quoi, nous lui avons délivré le "
        "présent certificat pour servir et faire valoir ce que de droit."))
    story.append(draw_paragraph("Pour constitution du dossier."))
    story.append(
        draw_paragraph("<b>Bamako, le</b> {}".format(
            date_filter(timezone.now())), align="right"))
    story.append(draw_paragraph("Le Maire", align="right"))

    doc.build(story, onFirstPage=addQRCodeToFrame)

    pdf_form.seek(0)  # make sure it's readable

    return pdf_form
