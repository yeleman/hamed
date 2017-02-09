#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from django.http import Http404
from django.shortcuts import render
from django.contrib import messages
from django import forms

from hamed.models.collects import Collect
from hamed.ona import (
    get_form_detail, upload_xlsform,
    disable_form, get_form_data, upload_csv_media)
from hamed.exports.xlsx.xlsform import gen_xlsform
from hamed.utils import gen_targets_documents
# from hamed.utils import (gen_xlsform, upload_xlsform,
#                          disable_ona_form, save_ona_data,
#                          retrieve_ona_form_data,
#                          gen_targets_documents,
#                          gen_targets_csv,
#                          upload_targets_csv,
#                          save_ona_scan_data,
#                          get_ona_form_detail)

logger = logging.getLogger(__name__)


def home(request):
    context = {
        'collects': {
            'actives': Collect.active.all(),
            'archives': Collect.archived.all(),
        }
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
            print("valid form")
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

                    context['state'] = 'created'
                    context['collect'] = collect
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


def end_collect(request, collect_id):
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))
    context = {'collect': collect,
               'state': 'initial'}

    if request.method == 'POST':
        context['state'] = 'failed'
        print("do end collect")

        # disable form on ONA
        disable_form(collect.ona_form_pk)

        # download data
        data = get_form_data(collect.ona_form_pk)

        # populate data-related fields
        collect.process_form_data(data)

        # generate PDF files for all targets
        gen_targets_documents(collect.targets.all())

        # generate itemsets CSV
        targets_csv = collect.get_targets_csv()

        # generate scan xlsx
        xlsx = gen_xlsform('hamed/fixtures/scan-certificat.xlsx',
                           form_id=collect.ona_scan_form_id(),
                           form_title=collect.scan_form_title())

        # with open('/Users/reg/Desktop/test.xlsx', 'wb') as f:
        #     f.write(xlsx.read())

        # xlsx.seek(0)

        # upload scan xlsx to ONA
        try:
            resp = upload_xlsform(xlsx)
            from pprint import pprint as pp ; pp(resp)
        except Exception as exp:
            print("Failed to upload XLSX")
            logger.exception(exp)
            raise

        # save ONA primary key as required by API
        collect.ona_scan_form_pk = resp['formid']
        collect.save()

        # add itemsets CSV to scan form
        try:
            resp = upload_csv_media(form_pk=collect.ona_scan_form_pk,
                                    media_csv=targets_csv,
                                    media_fname='targets.csv')
            from pprint import pprint as pp ; pp(resp)
        except Exception as exp:
            print("Failed to upload CSV")
            logger.exception(exp)
            raise
        else:
            context['state'] = 'success'
            collect.change_status(collect.ENDED)

    return render(request, 'end_collect.html', context)


def finalize_collect(request, collect_id):
    # retrieve collect ID / Collect
    collect = Collect.get_or_none(collect_id)
    if collect is None:
        raise Http404("No collect with ID `{}`".format(collect_id))
    context = {'collect': collect,
               'state': 'initial'}

    if request.method == 'POST':
        context['state'] = 'failed'
        print("do finalize collect")

    # disable scan form on ONA
    disable_form(collect.ona_scan_form_pk)

    # download data and update each RAMEDTarget
    data = get_form_data(collect.ona_scan_form_pk)
    from pprint import pprint as pp ; pp(data)
    collect.process_scan_form_data(data)

    collect.change_status(collect.FINALIZED)
    context['state'] = 'success'

    return render(request, 'finalize_collect.html', {})


def export(request, collect_id):
    return render(request, 'export.html', {})


def archives(request):
    context = {
        'collects': Collect.objects.all()
    }
    return render(request, 'archives.html', context)
