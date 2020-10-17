#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from hamed.steps import Task, TaskCollection
from hamed.ona import (disable_form, enable_form, get_form_data)
from hamed.utils import (export_collect_data, remove_exported_collect_data,
                         remove_collect_medias, export_collect_medias)

logger = logging.getLogger(__name__)


class DisableONAScanForm(Task):
    required_inputs = ['collect']

    def _process(self):
        ''' disable form on ONA to prevent new submission '''
        disable_form(self.kwargs['collect'].ona_scan_form_pk)

    def _revert(self):
        ''' re-enable form on ONA to allow new submissions '''
        if self.kwargs.get('collect'):
            if self.kwargs['collect'].ona_scan_form_pk:
                enable_form(self.kwargs['collect'].ona_scan_form_pk)


class DownloadScanData(Task):
    required_inputs = ['collect']
    required_outputs = ['data']

    def _process(self):
        ''' retrieve ONA data for form '''
        self.output['data'] = get_form_data(
            self.kwargs['collect'].ona_scan_form_pk)

    def _revert(self):
        ''' release collected data for form '''
        self.release_from_output('data')
        # delete ONA submissions on ONA


class AddONAScanDataToCollect(Task):
    required_inputs = ['collect', 'data']

    def _process(self):
        ''' populate Collect with retrieved data and create Targets '''
        self.kwargs['collect'].process_scan_form_data(self.output['data'])

    def _revert(self):
        ''' delete created targets and empty data-fields on Collect '''
        self.kwargs['collect'].reset_scan_form_data()


class ExportAllData(Task):
    required_inputs = ['collect']

    def _process(self):
        ''' export complete JSON data to file and medias '''
        export_collect_data(self.kwargs['collect'])

    def _revert(self):
        ''' remove such files (JSON export and all medias) from disk '''
        if self.kwargs.get('collect'):
            remove_exported_collect_data(self.kwargs['collect'])


class ExportAllMedias(Task):
    required_inputs = ['collect']

    def _process(self):
        ''' export complete JSON data to file and medias '''
        export_collect_medias(self.kwargs['collect'])

    def _revert(self):
        ''' remove such files (JSON export and all medias) from disk '''
        if self.kwargs.get('collect'):
            remove_collect_medias(self.kwargs['collect'])


class MarkCollectAsFinalized(Task):
    required_inputs = ['collect']

    def _process(self):
        ''' change collect status to ENDED '''
        self.kwargs['collect'].change_status(self.kwargs['collect'].FINALIZED)

    def _revert(self):
        ''' return Collect status to STARTED '''
        self.kwargs['collect'].change_status(self.kwargs['collect'].ENDED)


class FinalizeCollectTaskCollection(TaskCollection):
    tasks = [DisableONAScanForm,
             DownloadScanData,
             AddONAScanDataToCollect,
             ExportAllData,
             ExportAllMedias,
             MarkCollectAsFinalized]
