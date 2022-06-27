#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import os
from collections import OrderedDict
import io
import qrcode

from django.db import models
from django.utils import timezone
from jsonfield.fields import JSONField

from hamed.identifiers import full_random_id
from hamed.utils import get_attachment, PERSONAL_FILES, slugify_for_disk
from hamed.ona import delete_submission

logger = logging.getLogger(__name__)


class IndigentManager(models.Manager):
    def get_queryset(self):
        return super(IndigentManager, self).get_queryset().filter(is_indigent=True)


class NonIndigentManager(models.Manager):
    def get_queryset(self):
        return super(NonIndigentManager, self).get_queryset().filter(is_indigent=False)


class Target(models.Model):
    class Meta:
        ordering = ["-collect__started_on", "last_name", "first_name"]

    MALE = "male"
    FEMALE = "female"
    GENDERS = OrderedDict([(MALE, "Masculin"), (FEMALE, "Feminin")])
    SEXES = OrderedDict([(MALE, "Homme"), (FEMALE, "Femme")])

    identifier = models.CharField(max_length=10, primary_key=True)
    collect = models.ForeignKey("Collect", related_name="targets")
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    age = models.IntegerField()
    gender = models.CharField(max_length=20, choices=GENDERS.items())
    region = models.CharField(max_length=100)
    cercle = models.CharField(max_length=100)
    commune = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    is_indigent = models.NullBooleanField(blank=True, null=True)
    form_dataset = JSONField(default=dict, blank=True)
    scan_form_dataset = JSONField(default=dict, blank=True)

    objects = models.Manager()
    indigents = IndigentManager()
    nonindigents = NonIndigentManager()

    def fname(self):
        return slugify_for_disk(
            "{ident}-{last} {first}".format(
                ident=self.identifier,
                last=self.last_name.strip().upper(),
                first=self.first_name.strip().title(),
            )
        )

    def name(self):
        return "{first} {last}".format(
            last=self.last_name.upper(), first=self.first_name.title()
        )

    @property
    def verbose_sex(self):
        return self.SEXES.get(self.gender)

    @property
    def dataset(self):
        dataset = self.form_dataset.copy()
        for key, value in self.scan_form_dataset.items():
            if key not in dataset:
                dataset.update({key: value})
            elif key == "_attachments":
                dataset[key] += value
            else:
                dataset.update({"_scan:{}".format(key): value})
        return dataset

    def __str__(self):
        return "{ident}.{name}".format(ident=self.identifier, name=self.name())

    @classmethod
    def get_unused_ident(cls):
        nb_targets = cls.objects.count()
        attempts = 0
        while attempts <= nb_targets + 10:
            attempts += 1
            ident = full_random_id()
            if cls.objects.filter(identifier=ident).count():
                continue
            return ident
        raise Exception("Unable to compute a free identifier for Target.")

    @classmethod
    def create_from_submission(cls, collect, submission):
        sex = submission.get("enquete/sexe")
        birth_type = submission.get("enquete/type-naissance")
        yob = submission.get("enquete/annee-naissance", "")
        dob = submission.get("enquete/ddn", "")
        this_year = timezone.now().year
        if birth_type == "ddn":
            yob = int(dob.split("-")[0])
        age = this_year - int(yob)
        payload = {
            "identifier": cls.get_unused_ident(),
            "collect": collect,
            "first_name": submission.get("enquete/prenoms"),
            "last_name": submission.get("enquete/nom"),
            "age": age,
            "gender": cls.FEMALE if sex == "feminin" else cls.MALE,
            "region": submission.get("localisation-enquete/lieu_region"),
            "cercle": submission.get("localisation-enquete/lieu_cercle"),
            "commune": submission.get("localisation-enquete/lieu_commune"),
            "village": submission.get("localisation-enquete/lieu_village")
            or submission.get("localisation-enquete/lieu_village_autre")
            or submission.get("localisation-enquete/lieu_commune"),
            "form_dataset": submission,
        }
        return cls.objects.create(**payload)

    def update_with_scan_submission(self, submission):
        self.scan_form_dataset = submission
        self.is_indigent = bool(submission)
        self.save()

    @classmethod
    def get_or_none(cls, identifier):
        try:
            return cls.objects.get(identifier=identifier)
        except cls.DoesNotExist:
            return None

    def get_qrcode(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )

        qr.add_data(self.identifier)
        qr.make(fit=True)
        im = qr.make_image()
        output = io.BytesIO()
        im.save(output, format="PNG")
        output.seek(0)
        return output

    def attachments(self):

        labels = {
            "acte-naissance/image_acte_naissance": {
                "slug": "acte-naissance",
                "short": "AN",
                "long": "Acte de naissance",
            },
            "carte_identite/image_carte_identite": {
                "slug": "carte-identite",
                "short": "CI",
                "long": "Carte d'identité",
            },
            "signature": {
                "slug": "signature",
                "short": "SIG",
                "long": "Signature",
            },
            "certificat-indigence": {
                "slug": "certificat-indigence",
                "short": "CERT-IND",
                "long": "Certificat d'indigence",
            },
            "certificat-residence": {
                "slug": "certificat-residence",
                "short": "CERT-RES",
                "long": "Certificat de résidence",
            },
        }

        children_labels = {
            "enfants/situation/enfant_certificat-frequentation/enfant_image_f": {
                "slug": "certificat-frequentation",
                "short": "CERT-FREQ",
                "long": "Certificat de fréquentation",
            },
            "enfants/situation/enfant_certificat-medical/enfant_image_m": {
                "slug": "certificat-medical",
                "short": "CERT-MED",
                "long": "Certificat médical",
            },
            "enfants/enfant_acte-naissance/enfant_image_n": {
                "slug": "acte-naissance",
                "short": "AN",
                "long": "Acte de naissance",
            },
        }

        spouses_labels = {
            "epouses/e_acte-mariage/e_image_m": {
                "slug": "acte-mariage",
                "short": "AM",
                "long": "Acte de mariage",
            },
            "epouses/e_acte-naissance/e_image_n": {
                "slug": "acte-naissance",
                "short": "AN",
                "long": "Acte de naissance",
            },
        }

        data = {"enfants": [], "epouses": []}

        # retrieve each expected image, add label and export fname
        for key, label in labels.items():
            attachment = get_attachment(self.dataset, self.dataset.get(key))
            if attachment is None:
                continue
            attachment["labels"] = label
            attachment["hamed_url"] = label["slug"]
            attachment["export_fname"] = "{id}_{label}{ext}".format(
                id=self.identifier,
                label=label["slug"],
                ext=os.path.splitext(attachment["filename"])[1],
            )
            data.update({label["slug"]: attachment})
            del attachment

        # loop on spouses to apply same process
        for index, spouse in enumerate(self.dataset.get("epouses", [])):
            spouse_data = {}
            for key, label in spouses_labels.items():
                attachment = get_attachment(self.dataset, spouse.get(key))
                if attachment is None:
                    continue
                attachment["labels"] = label
                attachment["export_fname"] = "{id}_epouse{num}_{label}{ext}".format(
                    id=self.identifier,
                    num=index + 1,
                    label=label["slug"],
                    ext=os.path.splitext(attachment["filename"])[1],
                )
                spouse_data.update({label["slug"]: attachment})
                del attachment
            data["epouses"].append(spouse_data)

        # loop on children to apply same process
        for index, children in enumerate(self.dataset.get("enfants", [])):
            children_data = {}
            for key, label in children_labels.items():
                attachment = get_attachment(self.dataset, children.get(key))
                if attachment is None:
                    continue
                attachment["labels"] = label
                attachment["export_fname"] = "{id}_enfant{num}_{label}{ext}".format(
                    id=self.identifier,
                    num=index + 1,
                    label=label["slug"],
                    ext=os.path.splitext(attachment["filename"])[1],
                )
                children_data.update({label["slug"]: attachment})
                del attachment
            data["enfants"].append(children_data)

        return data

    def get_attachment(self, slug, within=None, at_index=None):
        """retrieve single (or several) attachment for specific slug

        within: enfants | epouses
        at_index: specify 0-based entry within the `within` group"""

        # root-level (enquetee) attachment
        if within is None:
            return self.attachments().get(slug)

        # attachments for that slug for each of the group members
        if at_index is None:
            return [att.get(slug) for att in self.attachments().get(within, [])]

        try:
            return self.attachments().get(within)[at_index].get(slug)
        except IndexError:
            return None

    def list_attachments(self):
        al = []
        for attach_key, attachment in self.attachments().items():
            if attach_key == "signature":
                continue
            if isinstance(attachment, list):
                for person in attachment:
                    for _, pattachment in person.items():
                        al.append(pattachment)
            else:
                al.append(attachment)
        return al

    def get_folder_fname(self):
        return self.fname()

    def get_folder_path(self):
        return os.path.join(
            self.collect.get_documents_path(), PERSONAL_FILES, self.get_folder_fname()
        )

    def export_data(self):
        data = self.dataset.copy()
        if "ident" not in data.keys():
            data.update({"ident": self.identifier})
        data.update({"_hamed_attachments": self.attachments()})
        return data

    @property
    def ona_submission_id(self):
        return self.form_dataset.get("_id")

    @property
    def ona_scan_submission_id(self):
        return self.scan_form_dataset.get("_id")

    def delete_ona_scan_submission(self):
        if self.collect.ona_scan_form_pk and self.ona_scan_submission_id:
            delete_submission(
                form_pk=self.collect.ona_scan_form_pk,
                submission_id=self.ona_scan_submission_id,
            )

    def delete_ona_submission(self):
        if self.collect.ona_form_pk and self.ona_submission_id:
            delete_submission(
                form_pk=self.collect.ona_form_pk, submission_id=self.ona_submission_id
            )

    def delete_ona_submissions(self):
        self.delete_ona_scan_submission()
        self.delete_ona_submission()

    def delete_scan_data(self, delete_submission=False):
        if delete_submission:
            self.delete_ona_scan_submission()
        self.scan_form_dataset = {}
        self.is_indigent = None
        self.save()

    def remove_completely(self, delete_submissions=False):
        if delete_submissions:
            self.delete_ona_submissions()
        self.delete()
