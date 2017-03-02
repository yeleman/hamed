#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import re
import os

from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django import forms

from hamed.models.collects import Collect, Target
from hamed.ona import get_form_detail, download_media
from hamed.steps.start_collect import StartCollectTaskCollection
from hamed.steps.end_collect import EndCollectTaskCollection
from hamed.steps.finalize_collect import FinalizeCollectTaskCollection


logger = logging.getLogger(__name__)


class NewCollectForm(forms.ModelForm):

    class Meta:
        model = Collect
        fields = ['commune', 'suffix']


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
        raise Http404("No collect with ID `{}`".format(collect_id))
    context = {
        'collect': collect,
        'ona_collect': get_form_detail(collect.ona_form_pk)}

    return render(request, 'collect.html', context)


def collect_data(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))

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
        errors = "\n".join(form.errors['__all__'])
        return fail("Informations incorrectes pour créér la collecte : {all}"
                    .format(all=errors))

    tc = StartCollectTaskCollection(form=form)
    tc.process()
    if tc.successful:
        messages.success(request, "Successfuly created Collect “{}”"
                                  .format(tc.output.get('collect')))
        return redirect('collect', tc.output.get('collect').id)
    elif not tc.clean_state:
        return fail("Unable to create collect. "
                    "Error while reverting to previous state: {}"
                    .format(tc.exception))
    else:
        return fail("Unable to create Collect. Reverted to previous state. {}"
                    .format(tc.exception))


@require_POST
def end_collect(request, collect_id):

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return redirect('collect', collect_id=collect.id)

    tc = EndCollectTaskCollection(collect=collect)
    tc.process()
    if tc.successful:
        messages.success(request, "Successfuly ended Collect “{}”"
                                  .format(collect))
        return redirect('collect', collect.id)
    elif not tc.clean_state:
        return fail("Unable to end collect. "
                    "Error while reverting to previous state: {}"
                    .format(tc.exception))
    else:
        return fail("Unable to end Collect. Reverted to previous state. {}"
                    .format(tc.exception))


@require_POST
def finalize_collect(request, collect_id):

    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return redirect('collect', collect_id=collect.id)

    tc = FinalizeCollectTaskCollection(collect=collect)
    tc.process()
    if tc.successful:
        messages.success(request, "Successfuly finalized Collect “{}”"
                                  .format(collect))
        return redirect('collect', collect.id)
    elif not tc.clean_state:
        return fail("Unable to finalize collect. "
                    "Error while reverting to previous state: {}"
                    .format(tc.exception))
    else:
        return fail("Unable to finalize Collect. "
                    "Reverted to previous state. {}"
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
