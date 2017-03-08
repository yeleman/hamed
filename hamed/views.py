#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import re
import os

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django import forms

from hamed.models.collects import Collect
from hamed.models.targets import Target
from hamed.models.settings import Settings
from hamed.ona import get_form_detail, download_media
from hamed.steps.start_collect import StartCollectTaskCollection
from hamed.steps.end_collect import EndCollectTaskCollection
from hamed.steps.finalize_collect import FinalizeCollectTaskCollection
from hamed.locations import get_communes
from hamed.utils import open_finder_at, get_export_fname, MIMES

logger = logging.getLogger(__name__)


class NewCollectForm(forms.ModelForm):

    class Meta:
        model = Collect
        fields = ['commune_id', 'suffix', 'mayor_title', 'mayor_name']

    def __init__(self, *args, **kwargs):
        super(NewCollectForm, self).__init__(*args, **kwargs)

        cercle_id = Settings.cercle_id()
        self.fields['commune_id'] = forms.ChoiceField(
            label="Commune",
            choices=get_communes(cercle_id))


def home(request):
    context = {
        'collects': {
            'actives': Collect.active.all(),
            'archives': Collect.archived.all(),
        },
        'form': NewCollectForm(),
    }
    return render(request, 'home.html', context)


def collect(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))
    context = {
        'collect': collect,
        'ona_form': get_form_detail(collect.ona_form_pk)
        if collect.ona_form_pk else {},
        'ona_scan_form': get_form_detail(collect.ona_scan_form_pk)
        if collect.ona_scan_form_pk else {}}

    return render(request, 'collect.html', context)


def collect_data(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    context = {'collect': collect}

    return render(request, 'collect_data.html', context)


@require_POST
def start_collect(request):
    def fail(message):
        messages.error(request, message)
        return redirect('home')

    # make sure form is valid before processing
    form = NewCollectForm(request.POST)
    if not form.is_valid():
        errors = []  # "\n".join(form.errors['__all__'])
        for field, field_errors in form.errors.items():
            if field == '__all__':
                errors += field_errors
            else:
                for error in field_errors:
                    errors.append("[{}] {}".format(
                        form.fields[field].label, error))
        return fail("Informations incorrectes pour créér la collecte : {all}"
                    .format(all="\n".join(errors)))

    tc = StartCollectTaskCollection(form=form)
    tc.process()
    if tc.successful:
        messages.success(request, "La collecte «{}» a bien été créée."
                                  .format(tc.output.get('collect')))
        return redirect('collect', tc.output.get('collect').id)
    elif not tc.clean_state:
        return fail("Impossible de créer la collecte. "
                    "Erreur lors de la tentative "
                    "de retour à l'état précédent : {}"
                    .format(tc.exception))
    else:
        return fail("Impossible de créer la collecte. "
                    "Collecte retournée à l'état précédent. (exp: {})"
                    .format(tc.exception))


@require_POST
def end_collect(request, collect_id):

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return JsonResponse({'status': 'error', 'message': message})

    tc = EndCollectTaskCollection(collect=collect)
    tc.process()
    if tc.successful:
        message = "Collecte «{}» terminée.".format(collect)
        messages.success(request, message)
        return JsonResponse({'status': 'success', 'message': message})
    elif not tc.clean_state:
        return fail("Impossible de terminer la collecte. "
                    "Erreur lors de la tentative "
                    "de retour à l'état précédent : {}"
                    .format(tc.exception))
    else:
        return fail("Impossible de terminer la collecte. "
                    "Collecte retournée à l'état précédent. (exp: {})"
                    .format(tc.exception))


@require_POST
def finalize_collect(request, collect_id):

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return JsonResponse({'status': 'error', 'message': message})

    tc = FinalizeCollectTaskCollection(collect=collect)
    tc.process()
    if tc.successful:
        message = "Collecte «{}» finalisée.".format(collect)
        messages.success(request, message)
        return JsonResponse({'status': 'success', 'message': message})
    elif not tc.clean_state:
        return fail("Impossible de finaliser la collecte. "
                    "Erreur lors de la tentative "
                    "de retour à l'état précédent : {}"
                    .format(tc.exception))
    else:
        return fail("Impossible de finaliser la collecte. "
                    "Collecte retournée à l'état précédent. (exp: {})"
                    .format(tc.exception))


def attachment_proxy(request, fname):
    ''' finds a media from it's filename, downloads it from ONA and serves it

        filename is hamed-generated one which includes additional info.
        It is used for single-entry viewing/downloading only (not exports) '''

    target_id, cfname = fname.split("_", 1)

    target = Target.get_or_none(target_id)
    if target is None:
        raise Http404("No target with ID `{}`".format(target_id))

    within = None
    if cfname.startswith('enfant'):
        within = 'enfants'
    elif cfname.startswith('epouse'):
        within = 'epouses'

    if within:
        indexpart, filename = cfname.split("_", 1)
        index = int(re.sub(r'[^0-9]', '', indexpart)) - 1
    else:
        filename = cfname
        index = None
    slug = os.path.splitext(filename)[0]

    attachment = target.get_attachment(slug, within, index)
    if attachment is None:
        raise Http404("No attachment with name `{}`".format(fname))

    return HttpResponse(
        download_media(attachment.get('download_url')),
        content_type=attachment.get('mimetype'))


def exports_proxy(request, collect_id, format):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    if format not in ('xlsx', 'json'):
        raise Http404("Aucun export pour le format `{}`".format(format))

    fname = get_export_fname(format, collect)
    fpath = os.path.join(collect.get_documents_path(), fname)
    with open(fpath, 'rb') as fd:
        return HttpResponse(
            fd.read(), content_type=MIMES.get(format))


def open_documents_folder(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    open_finder_at(collect.get_documents_path())
    return JsonResponse({'satus': 'success'})


def help(request):
    context = {'collect': {
        'name': "E.S Commune-suffixe",
        'commune': "Commune",
        'form_title': "Enquête sociale Commune/suffixe",
        'ona_form_id': "enquete-sociale-x",
        'get_nb_papers': None,
        'scan_form_title': "Scan certificats Commune/suffixe",
        'ona_scan_form_id': "scan-certificats-x",
        'medias_size': 10024,
    }}
    return render(request, 'help.html', context)


@require_POST
def collect_downgrade(request, collect_id):

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("Aucune collecte avec l'ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return JsonResponse({'status': 'error', 'message': message})

    tc = collect.downgrade()
    if tc.reverted:
        message = "État de la collecte «{}» modifié.".format(collect)
        messages.success(request, message)
        return JsonResponse({'status': 'success', 'message': message})
    elif not tc.clean_state:
        return fail("Impossible de modifier l'état de la collecte. "
                    "Erreur lors de la tentative "
                    "de retour à l'état précédent : {}"
                    .format(tc.exception))
    else:
        return fail("Impossible de modifier l'état de la collecte. "
                    "Collecte retournée à l'état précédent. (exp: {})"
                    .format(tc.exception))
