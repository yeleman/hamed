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
from hamed.ona import (
    get_form_detail, upload_xlsform,
    disable_form, get_form_data, upload_csv_media,
    download_media)
from hamed.exports.xlsx.xlsform import gen_xlsform
from hamed.utils import gen_targets_documents


logger = logging.getLogger(__name__)


def home(request):
    context = {
        'collects': {
            'actives': Collect.active.all(),
            'archives': Collect.archived.all(),
        }
    }
    return render(request, 'home.html', context)


def collect_data(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))

    context = {'collect': collect}

    return render(request, 'collect_data.html', context)


def attachment_proxy(request, fname):
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

    print(slug, within, index)
    attachment = target.get_attachment(slug, within, index)
    if attachment is None:
        raise Http404("No attachment with name `{}`".format(fname))

    return HttpResponse(
        download_media(attachment.get('download_url')),
        content_type=attachment.get('mimetype'))


def collect(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))
    context = {
        'collect': collect,
        'ona_collect': get_form_detail(collect.ona_form_pk)}

    return render(request, 'collect.html', context)


class NewCollectForm(forms.ModelForm):

    class Meta:
        model = Collect
        fields = ['commune', 'suffix']


def start_collect(request):
    context = {'state': 'creation'}

    if request.method == 'POST':
        # handle django form
        form = NewCollectForm(request.POST)
        if form.is_valid():
            try:
                # create actual Collect
                collect = form.save()
                # generate standard XLSForm for id and title
                xlsx = gen_xlsform(
                    'hamed/fixtures/enquete-sociale-mobile.xlsx',
                    form_title=collect.form_title(),
                    form_id=collect.ona_form_id())
                try:
                    # upload xlsform to ONA
                    resp = upload_xlsform(xlsx)
                    from pprint import pprint as pp ; pp(resp)

                    # save ONA primary key as required by API
                    collect.ona_form_pk = resp['formid']
                    collect.save()

                    messages.success(request, "Collect created")
                    return redirect('collect', collect_id=collect.id)

                except Exception as exp:
                    logger.exception(exp)
                    collect.delete()
                    context['state'] = 'failed'
            except:
                context['state'] = 'failed'
                raise
        else:
            context['state'] = 'failed'
            print("form is not valid")
    else:
        form = NewCollectForm()

    context.update({'form': form})

    return render(request, 'start_collect.html', context)


@require_POST
def end_collect(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return redirect('collect', collect_id=collect.id)

    # disable form on ONA
    try:
        disable_form(collect.ona_form_pk)
    except Exception as exp:
        logger.exception(exp)
        return fail("Unable to disable ONA form `{pk}`: {exp}"
                    .format(pk=collect.ona_form_pk, exp=exp))

    # download data
    try:
        data = get_form_data(collect.ona_form_pk)
    except Exception as exp:
        logger.exception(exp)
        return fail("Unable to download ONA data for form `{pk}`: {exp}"
                    .format(pk=collect.ona_form_pk, exp=exp))

    # populate data-related fields
    try:
        collect.process_form_data(data)
    except Exception as exp:
        logger.exception(exp)
        return fail("Error while processing form data. {exp}"
                    .format(exp=exp))

    # generate PDF files for all targets
    try:
        gen_targets_documents(collect.targets.all())
    except Exception as exp:
        logger.exception(exp)
        return fail("Error while generating PDF documents for targets. {exp}"
                    .format(exp=exp))

    # generate itemsets CSV
    try:
        targets_csv = collect.get_targets_csv()
    except Exception as exp:
        logger.exception(exp)
        return fail("Error while generating certifcates-scan form CSV. {exp}"
                    .format(exp=exp))

    # generate scan xlsx
    try:
        print(collect.ona_scan_form_id(), collect.scan_form_title())
        xlsx = gen_xlsform('hamed/fixtures/scan-certificat.xlsx',
                           form_id=collect.ona_scan_form_id(),
                           form_title=collect.scan_form_title())
    except Exception as exp:
        logger.exception(exp)
        return fail("Error while generating certificates-scan form. {exp}"
                    .format(exp=exp))

    # upload scan xlsx to ONA
    try:
        resp = upload_xlsform(xlsx)
        from pprint import pprint as pp ; pp(resp)

        # save ONA primary key as required by API
        collect.ona_scan_form_pk = resp['formid']
        collect.save()
    except Exception as exp:
        logger.exception(exp)
        return fail("Error while uploading certificates-scan form. {exp}"
                    .format(exp=exp))

    # add itemsets CSV to scan form
    try:
        resp = upload_csv_media(form_pk=collect.ona_scan_form_pk,
                                media_csv=targets_csv,
                                media_fname='targets.csv')
        from pprint import pprint as pp ; pp(resp)
    except Exception as exp:
        logger.exception(exp)
        return fail("Error while uploading certificates-scan form CSV. {exp}"
                    .format(exp=exp))
    else:
        collect.change_status(collect.ENDED)

    messages.success(request, "Collect ended")

    return redirect('collect', collect_id=collect.id)


@require_POST
def finalize_collect(request, collect_id):

    # retrieve collect ID / Collect
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))

    def fail(message):
        messages.error(request, message)
        return redirect('collect', collect_id=collect.id)

    # disable scan form on ONA
    try:
        disable_form(collect.ona_scan_form_pk)
    except Exception as exp:
        logger.exception(exp)
        return fail("Unable to disable ONA form `{pk}`: {exp}"
                    .format(pk=collect.ona_scan_form_pk, exp=exp))

    # download data and update each Target
    try:
        data = get_form_data(collect.ona_scan_form_pk)
        from pprint import pprint as pp ; pp(data)
        collect.process_scan_form_data(data)
    except Exception as exp:
        logger.exception(exp)
        return fail("Error while processing scan form data. {exp}"
                    .format(exp=exp))
    else:
        collect.change_status(collect.FINALIZED)

    messages.success(request, "Collect finalized")
    return redirect('collect', collect_id=collect.id)

