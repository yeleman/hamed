#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from hamed.steps import Task, TaskCollection
from hamed.exports.xlsx.xlsform import gen_xlsform
from hamed.ona import (upload_xlsform, delete_form, disable_form, enable_form,
                       get_form_data, upload_csv_media,
                       delete_media, get_media_id)
from hamed.utils import (gen_targets_documents, remove_targets_documents,
                         share_form, unshare_form)

logger = logging.getLogger(__name__)


class DisableONAForm(Task):
    required_inputs = ['collect']

    def _process(self):
        ''' disable form on ONA to prevent new submission '''
        disable_form(self.kwargs['collect'].ona_form_pk)

    def _revert(self):
        ''' re-enable form on ONA to allow new submissions '''
        if self.kwargs.get('collect'):
            if self.kwargs['collect'].ona_form_pk:
                enable_form(self.kwargs['collect'].ona_form_pk)


class DownloadData(Task):
    required_inputs = ['collect']
    required_outputs = ['data']

    def _process(self):
        ''' retrieve ONA data for form '''
        self.output['data'] = get_form_data(self.kwargs['collect'].ona_form_pk)

    def _revert(self):
        ''' release collected data for form '''
        self.release_from_output('data')


class AddONADataToCollect(Task):
    required_inputs = ['collect', 'data']

    def _process(self):
        ''' populate Collect with retrieved data and create Targets '''
        self.kwargs['collect'].process_form_data(self.output['data'])

    def _revert(self):
        ''' delete created targets and empty data-fields on Collect '''
        self.kwargs['collect'].reset_form_data()


class GenerateTargetsDocuments(Task):
    required_inputs = ['collect']

    def _process(self):
        ''' generate documents for all targets '''
        gen_targets_documents(self.kwargs['collect'].targets.all())

    def _revert(self):
        ''' remove generated documents for targets '''
        if self.kwargs.get('collect'):
            remove_targets_documents(self.kwargs['collect'].targets.all())


class GenerateItemsetsCSV(Task):
    required_inputs = ['collect']
    required_outputs = ['targets_csv']

    def _process(self):
        ''' generate itemsets CSV for targets '''
        self.output['targets_csv'] = self.kwargs['collect'].get_targets_csv()

    def _revert(self):
        ''' release generated itemsets CSV for targets '''
        self.release_from_output('targets_csv')


class GenerateScanXLSForm(Task):
    required_inputs = ['collect']
    required_outputs = ['xlsx']

    def _process(self):
        ''' generate XLSForm for scan '''
        self.output['xlsx'] = gen_xlsform(
            'hamed/fixtures/scan-certificat.xlsx',
            form_id=self.kwargs['collect'].ona_scan_form_id(),
            form_title=self.kwargs['collect'].scan_form_title())

    def _revert(self):
        ''' release generated XLSForm for scan '''
        self.release_from_output('xlsx')


class UploadXLSForm(Task):
    required_inputs = ['collect', 'xlsx']

    def _process(self):
        ''' upload scan xlsform to ONA '''
        resp = upload_xlsform(self.kwargs.get('xlsx'))

        # save ONA primary key as required by API
        self.kwargs['collect'].ona_scan_form_pk = resp['formid']
        self.kwargs['collect'].save()

    def _revert(self):
        ''' remove form on ONA and remove form ID in Collect '''
        if self.kwargs.get('collect'):
            if self.kwargs['collect'].ona_scan_form_pk:
                delete_form(self.kwargs['collect'].ona_scan_form_pk)

            self.kwargs['collect'].ona_scan_form_pk = None
            self.kwargs['collect'].save()


class ShareForm(Task):

    def _process(self):
        ''' add agent user permission to submit to form '''
        share_form(self.kwargs['collect'].ona_scan_form_pk)

    def _revert(self):
        ''' remove agent user permission to submit to form '''
        if self.kwargs.get('collect'):
            if self.kwargs['collect'].ona_scan_form_pk:
                unshare_form(self.kwargs['collect'].ona_scan_form_pk)


class AddItemsetsToONAForm(Task):
    required_inputs = ['collect', 'targets_csv']
    required_outputs = ['uploaded_csv']

    def _process(self):
        ''' upload itemsets CSV to ONA as media '''
        self.output['uploaded_csv'] = upload_csv_media(
            form_pk=self.kwargs['collect'].ona_scan_form_pk,
            media_csv=self.kwargs['targets_csv'],
            media_fname='targets.csv')

    def _revert(self):
        ''' remove itemsets CSV from ONA medias '''
        if 'uploaded_csv' in self.output:
            delete_media(self.kwargs['collect'],
                         self.output['uploaded_csv']['id'])
        # in case of cold revert, no output present so no media ID
        else:
            targets_csv_id = get_media_id(
                self.kwargs['collect'].ona_scan_form_pk, 'targets.csv')
            if targets_csv_id is not None:
                delete_media(self.kwargs['collect'],
                             targets_csv_id)


class MarkCollectAsEnded(Task):
    required_inputs = ['collect']

    def _process(self):
        ''' change collect status to ENDED '''
        self.kwargs['collect'].change_status(self.kwargs['collect'].ENDED)

    def _revert(self):
        ''' return Collect status to STARTED '''
        self.kwargs['collect'].change_status(self.kwargs['collect'].STARTED)


class EndCollectTaskCollection(TaskCollection):
    tasks = [DisableONAForm,
             DownloadData,
             AddONADataToCollect,
             GenerateTargetsDocuments,
             GenerateItemsetsCSV,
             GenerateScanXLSForm,
             UploadXLSForm,
             ShareForm,
             AddItemsetsToONAForm,
             MarkCollectAsEnded]
