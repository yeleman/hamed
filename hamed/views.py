#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import re
import os

import humanfriendly
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django import forms
from django.conf import settings
import hamed_advanced

from hamed.models.collects import Collect
from hamed.models.targets import Target
from hamed.models.settings import Settings
from hamed.ona import get_form_detail, download_media
from hamed.steps.start_collect import StartCollectTaskCollection
from hamed.steps.end_collect import EndCollectTaskCollection
from hamed.steps.finalize_collect import FinalizeCollectTaskCollection
from hamed.steps.reopen_collect import ReopenCollectTaskCollection
from hamed.locations import get_communes
from hamed.utils import (
    get_export_fname,
    MIMES,
    upload_export_data,
    find_export_disk,
    parse_parted_info,
    is_advanced_mode,
    activate_advanced_mode,
)
from hamed.exceptions import MultipleUSBDisksPlugged, NoUSBDiskPlugged

logger = logging.getLogger(__name__)


class NewCollectForm(forms.ModelForm):
    class Meta:
        model = Collect
        fields = ["commune_id", "suffix", "mayor_title", "mayor_name"]

    def __init__(self, *args, **kwargs):
        super(NewCollectForm, self).__init__(*args, **kwargs)

        cercle_id = Settings.cercle_id()
        self.fields["commune_id"] = forms.ChoiceField(
            label="Commune", choices=get_communes(cercle_id)
        )


def home(request):
    context = {
        "collects": {
            "actives": Collect.active.all(),
            "archives": Collect.archived.all(),
        },
        "form": NewCollectForm(),
    }
    return render(request, "home.html", context)


def collect(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    context = {"collect": collect, "advanced_mode": is_advanced_mode()}

    ona_form = {}
    ona_scan_form = {}

    def fail(exp):
        messages.error(
            request, "ERREUR ONA. Contactez le support: {exp}".format(exp=exp)
        )
        return redirect("home")

    if collect.ona_form_pk:
        try:
            ona_form = get_form_detail(collect.ona_form_pk)
        except Exception as exp:
            return fail(exp)

    if collect.ona_scan_form_pk:
        try:
            ona_scan_form = get_form_detail(collect.ona_scan_form_pk)
        except Exception as exp:
            return fail(exp)

    context.update({"ona_form": ona_form, "ona_scan_form": ona_scan_form})

    if collect.has_finalized():
        try:
            disk = find_export_disk()
            disk_info = parse_parted_info(disk)
            disk_name = "{name} ({size})".format(
                name=disk_info[4],
                size=humanfriendly.format_size(disk_info[2], binary=True),
            )
        except NoUSBDiskPlugged:
            disk = None
            disk_name = "Aucun disque branché"
        except MultipleUSBDisksPlugged:
            disk = None
            disk_name = "Plusieurs disques USB branchés"

        context.update(
            {
                "WS_SERVER": "{domain}:{port}".format(
                    domain=settings.ALLOWED_HOSTS[0],
                    port=settings.WEBSOCKET_SERVER_PORT,
                ),
                "disk": disk,
                "disk_name": disk_name,
            }
        )

    context.update({"FOLDER_OPENER_SERVER": settings.FOLDER_OPENER_SERVER})

    return render(request, "collect.html", context)


def collect_data(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    context = {"collect": collect, "advanced_mode": is_advanced_mode()}

    return render(request, "collect_data.html", context)


def delete_target(request, collect_id, target_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    if not is_advanced_mode():
        messages.error(request, "Impossible de supprimer une cible hors du mode avancé")
        return redirect("collect_data", collect_id=collect.id)

    target = Target.get_or_none(target_id)
    if target is None:
        raise Http404("Aucune cible avec l'ID `{}`".format(target_id))

    if target.collect != collect:
        raise Http404(
            "La cible «{}» ne fait pas partie de la collecte «{}»".format(
                target, collect
            )
        )

    try:
        target.remove_completely(delete_submissions=True)
    except Exception as exp:
        logger.exception(exp)
        messages.error(
            request,
            "Impossible de supprimer la cible «{target}»"
            ": {exp}".format(target=target, exp=exp),
        )
    else:
        messages.success(request, "La cible «{}» a été supprimée.".format(target))

    return redirect("collect_data", collect_id=collect.id)


@require_POST
def start_collect(request):
    def fail(message):
        messages.error(request, message)
        return redirect("home")

    # make sure form is valid before processing
    form = NewCollectForm(request.POST)
    if not form.is_valid():
        errors = []  # "\n".join(form.errors['__all__'])
        for field, field_errors in form.errors.items():
            if field == "__all__":
                errors += field_errors
            else:
                for error in field_errors:
                    errors.append("[{}] {}".format(form.fields[field].label, error))
        return fail(
            "Informations incorrectes pour créér la collecte : {all}".format(
                all="\n".join(errors)
            )
        )

    tc = StartCollectTaskCollection(form=form)
    tc.process()
    if tc.successful:
        messages.success(
            request,
            "La collecte «{}» a bien été créée.".format(tc.inputs.get("collect")),
        )
        return redirect("collect", tc.inputs.get("collect").id)
    elif not tc.clean_state:
        return fail(
            "Impossible de créer la collecte. "
            "Erreur lors de la tentative "
            "de retour à l'état précédent (exp: {})\n\n{}".format(
                tc.exception, tc.traceback
            )
        )
    else:
        return fail(
            "Impossible de créer la collecte. "
            "Collecte retournée à l'état précédent. (exp: {})\n\n{}".format(
                tc.exception, tc.traceback
            )
        )


@require_POST
def end_collect(request, collect_id):

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return JsonResponse({"status": "error", "message": message})

    tc = EndCollectTaskCollection(collect=collect)
    tc.process()
    if tc.successful:
        message = "Collecte «{}» terminée.".format(collect)
        messages.success(request, message)
        return JsonResponse({"status": "success", "message": message})
    elif not tc.clean_state:
        return fail(
            "Impossible de terminer la collecte. "
            "Erreur lors de la tentative "
            "de retour à l'état précédent. (exp: {})\n\n{}".format(
                tc.exception, tc.traceback
            )
        )
    else:
        return fail(
            "Impossible de terminer la collecte. "
            "Collecte retournée à l'état précédent. (exp: {})\n\n{}".format(
                tc.exception, tc.traceback
            )
        )


@require_POST
def finalize_collect(request, collect_id):

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return JsonResponse({"status": "error", "message": message})

    tc = FinalizeCollectTaskCollection(collect=collect)
    tc.process()
    if tc.successful:
        message = "Collecte «{}» finalisée.".format(collect)
        messages.success(request, message)
        return JsonResponse({"status": "success", "message": message})
    elif not tc.clean_state:
        return fail(
            "Impossible de finaliser la collecte. "
            "Erreur lors de la tentative "
            "de retour à l'état précédent (exp: {})\n\n{}".format(
                tc.exception, tc.traceback
            )
        )
    else:
        return fail(
            "Impossible de finaliser la collecte. "
            "Collecte retournée à l'état précédent. (exp: {})\n\n{}".format(
                tc.exception, tc.traceback
            )
        )


@require_POST
def reopen_collect(request, collect_id):

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return JsonResponse({"status": "error", "message": message})

    tc = ReopenCollectTaskCollection(collect=collect)
    tc.process()
    if tc.successful:
        message = "Collecte «{}» ré-ouverte.".format(collect)
        messages.success(request, message)
        return JsonResponse({"status": "success", "message": message})
    elif not tc.clean_state:
        return fail(
            "Impossible de ré-ouvrir la collecte. "
            "Erreur lors de la tentative "
            "de retour à l'état précédent (exp: {})\n\n{}".format(
                tc.exception, tc.traceback
            )
        )
    else:
        return fail(
            "Impossible de ré-ouvrir la collecte. "
            "Collecte retournée à l'état précédent. (exp: {})\n\n{}".format(
                tc.exception, tc.traceback
            )
        )


def attachment_proxy(request, fname):
    """finds a media from it's filename, downloads it from ONA and serves it

    filename is hamed-generated one which includes additional info.
    It is used for single-entry viewing/downloading only (not exports)"""

    target_id, cfname = fname.split("_", 1)

    target = Target.get_or_none(target_id)
    if target is None:
        raise Http404("No target with ID `{}`".format(target_id))

    within = None
    if cfname.startswith("enfant"):
        within = "enfants"
    elif cfname.startswith("epouse"):
        within = "epouses"

    if within:
        indexpart, filename = cfname.split("_", 1)
        index = int(re.sub(r"[^0-9]", "", indexpart)) - 1
    else:
        filename = cfname
        index = None
    slug = os.path.splitext(filename)[0]

    attachment = target.get_attachment(slug, within, index)
    if attachment is None:
        raise Http404("No attachment with name `{}`".format(fname))

    return HttpResponse(
        download_media(attachment.get("download_url")),
        content_type=attachment.get("mimetype"),
    )


def exports_proxy(request, collect_id, format):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    if format not in ("xlsx", "json"):
        raise Http404("Aucun export pour le format `{}`".format(format))

    fname = get_export_fname(format, collect)
    fpath = os.path.join(collect.get_documents_path(), fname)
    with open(fpath, "rb") as fd:
        response = HttpResponse(fd.read(), content_type=MIMES.get(format))
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(fname)
        return response


def help(request):
    context = {
        "collect": {
            "name": "E.S Commune-suffixe",
            "commune": "Commune",
            "form_title": "Enquête sociale Commune/suffixe",
            "ona_form_id": "enquete-sociale-x",
            "get_nb_papers": None,
            "scan_form_title": "Scan certificats Commune/suffixe",
            "ona_scan_form_id": "scan-certificats-x",
            "medias_size": 10024,
        }
    }
    return render(request, "help.html", context)


@require_POST
def collect_downgrade(request, collect_id):
    def fail(message):
        messages.error(request, message)
        return JsonResponse({"status": "error", "message": message})

    if not is_advanced_mode():
        return fail("Modification de la collecte impossible " "hors du «mode avancé»")

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    tc = collect.downgrade()
    if tc.reverted:
        message = "État de la collecte «{}» modifié.".format(collect)
        messages.success(request, message)
        return JsonResponse({"status": "success", "message": message})
    elif not tc.clean_state:
        return fail(
            "Impossible de modifier l'état de la collecte. "
            "Erreur lors de la tentative "
            "de retour à l'état précédent : {}".format(tc.exception)
        )
    else:
        return fail(
            "Impossible de modifier l'état de la collecte. "
            "Collecte retournée à l'état précédent. (exp: {})".format(tc.exception)
        )


@require_POST
def collect_drop_scan_data(request, collect_id):
    def fail(message):
        messages.error(request, message)
        return JsonResponse({"status": "error", "message": message})

    if not is_advanced_mode():
        return fail(
            "Suppression des données «scan» impossible " "hors du «mode avancé»"
        )

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    try:
        collect.reset_scan_form_data(delete_submissions=True)
        message = (
            "Les données «scan» de la collecte «{}» "
            "ont été supprimées.".format(collect)
        )
        messages.success(request, message)
        return JsonResponse({"status": "success", "message": message})
    except Exception as exp:
        logger.exception(exp)
        return fail(
            "Impossible de supprimer les données «scan» "
            "de la collecte. (exp: {})".format(exp)
        )


@require_POST
def collect_drop_data(request, collect_id):
    def fail(message):
        messages.error(request, message)
        return JsonResponse({"status": "error", "message": message})

    if not is_advanced_mode():
        return fail("Suppression des données impossible hors du «mode avancé»")

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    try:
        collect.reset_form_data(delete_submissions=True)
        message = "Les données de la collecte «{}» " "ont été supprimées.".format(
            collect
        )
        messages.success(request, message)
        return JsonResponse({"status": "success", "message": message})
    except Exception as exp:
        logger.exception(exp)
        return fail(
            "Impossible de supprimer les données "
            "de la collecte. (exp: {})".format(exp)
        )


@require_POST
def upload_data(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return JsonResponse({"status": "error", "message": message})

    try:
        result = upload_export_data(collect)
    except Exception as exp:
        result = {"status": "failed", "message": str(exp)}
    if result.get("status") == "success":
        message = "Données transmises à l'ANAM : {msg}".format(
            msg=result.get("message")
        )
        messages.success(request, message)
        return JsonResponse({"status": "success", "message": message})
    else:
        return fail(
            "Impossible de transmettre à l'ANAM : {msg}".format(
                msg=result.get("message")
            )
        )


class AdvancedRequestForm(forms.Form):

    request_code = forms.CharField(
        label="RequestCode",
        max_length=9,
        min_length=9,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    activation_code = forms.CharField(
        label="ActivationCode",
        max_length=5,
        min_length=5,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def clean_activation_code(self):
        if not hamed_advanced.validate_acceptation_code(
            self.cleaned_data.get("request_code"),
            self.cleaned_data.get("activation_code"),
        ):
            raise forms.ValidationError(
                "ActivationCode non valide pour ce RequestCode", code="invalid"
            )


def advanced_mode(request):
    if is_advanced_mode():
        return redirect("home")

    request_code = hamed_advanced.get_adavanced_request_code(
        cercle_id=Settings.cercle_id()
    )

    if request.method == "POST":
        form = AdvancedRequestForm(request.POST)
        if form.is_valid():
            cercle_id, date, pad = hamed_advanced.decode_request_code(
                form.cleaned_data["request_code"]
            )
            activate_advanced_mode(date)
            messages.success(request, "Mode avancé activé.")
            return redirect("home")
        else:
            pass
    else:
        form = AdvancedRequestForm(initial={"request_code": request_code})

    context = {
        "form": form,
        "request_code": request_code,
    }

    return render(request, "advanced.html", context)
