#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

logger = logging.getLogger(__name__)

from hamed.steps import Task, TaskCollection
from hamed.exports.xlsx.xlsform import gen_xlsform
from hamed.ona import upload_xlsform, delete_form


class CreateCollectInstance(Task):
    required_inputs = ['form']
    required_outputs = ['collect']

    def _process(self):
        ''' create a Collect instance from the data in form param '''
        self.output['collect'] = self.kwargs['form'].save()

    def _revert(self):
        ''' delete the created Collect instance '''
        if 'collect' in self.output:
            self.output['collect'].delete()
            self.release_from_output('collect')
        # in case of cold revert, no output is present. collect is input
        elif 'collect' in self.kwargs:
            self.kwargs['collect'].delete()


class GenerateCollectXLSForm(Task):
    required_inputs = ['collect']
    required_outputs = ['xlsx']

    def _process(self):
        self.output['xlsx'] = gen_xlsform(
            'hamed/fixtures/enquete-sociale-mobile.xlsx',
            form_title=self.kwargs['collect'].form_title(),
            form_id=self.kwargs['collect'].ona_form_id())

    def _revert(self):
        ''' process is harmless so nothing to revert '''
        self.release_from_output('xlsx')


class UploadXLSForm(Task):
    required_inputs = ['xlsx', 'collect']

    def _process(self):
        ''' upload xlsform to ONA '''
        resp = upload_xlsform(self.kwargs['xlsx'])

        # save ONA primary key as required by API
        self.kwargs['collect'].ona_form_pk = resp['formid']
        self.kwargs['collect'].save()

    def _revert(self):
        ''' remove form on ONA and remove form ID in Collect '''
        if self.kwargs.get('collect'):
            if self.kwargs['collect'].ona_form_pk:
                delete_form(self.kwargs['collect'].ona_form_pk)

            self.kwargs['collect'].ona_form_pk = None
            self.kwargs['collect'].save()


class StartCollectTaskCollection(TaskCollection):
    tasks = [CreateCollectInstance,
             GenerateCollectXLSForm,
             UploadXLSForm]
