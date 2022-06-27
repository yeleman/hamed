#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from hamed.steps import Task, TaskCollection
from hamed.exports.xlsx.xlsform import gen_xlsform
from hamed.ona import (
    upload_xlsform,
    delete_form,
    disable_form,
    enable_form,
    get_form_data,
    upload_csv_media,
    delete_media,
    get_media_id,
)
from hamed.utils import (
    gen_targets_documents,
    remove_targets_documents,
    share_form,
    unshare_form,
)

logger = logging.getLogger(__name__)


class ReEnableONAForm(Task):
    required_inputs = ["collect"]

    def _process(self):
        """re-enable form on ONA to allow new submissions"""
        enable_form(self.kwargs["collect"].ona_form_pk)

    def _revert(self):
        """disable form on ONA to prevent new submission"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        disable_form(self.kwargs["collect"].ona_form_pk)


class RemoveFormData(Task):
    required_inputs = ["collect"]
    # required_outputs = ["data"]

    def _process(self):
        """release collected data for form"""
        self.release_from_output("data")

    def _revert(self):
        """retrieve ONA data for form"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        self.output["data"] = get_form_data(self.kwargs["collect"].ona_form_pk)


class ResetONAData(Task):
    required_inputs = ["collect"]

    def _process(self):
        """delete created targets and empty data-fields on Collect"""
        self.kwargs["collect"].reset_form_data()

    def _revert(self):
        """populate Collect with retrieved data and create Targets"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        if not self.output.get("data"):
            logger.error("data not in output")
            return
        self.kwargs["collect"].process_form_data(self.output["data"])


class RemoveTargetsDocuments(Task):
    required_inputs = ["collect"]

    def _process(self):
        """remove generated documents for targets"""
        remove_targets_documents(self.kwargs["collect"].targets.all())

    def _revert(self):
        """generate documents for all targets"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        gen_targets_documents(self.kwargs["collect"].targets.all())


class RemoveItemsetsCSV(Task):
    required_inputs = ["collect"]
    # required_outputs = ["targets_csv"]

    def _process(self):
        """release generated itemsets CSV for targets"""
        self.release_from_output("targets_csv")

    def _revert(self):
        """generate itemsets CSV for targets"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        self.output["targets_csv"] = self.kwargs["collect"].get_targets_csv()


class RemoveScanXLSForm(Task):
    required_inputs = ["collect"]
    # required_outputs = ["xlsx"]

    def _process(self):
        """release generated XLSForm for scan"""
        self.release_from_output("xlsx")

    def _revert(self):
        """generate XLSForm for scan"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        self.output["xlsx"] = gen_xlsform(
            "hamed/fixtures/scan-certificat.xlsx",
            form_id=self.kwargs["collect"].ona_scan_form_id(),
            form_title=self.kwargs["collect"].scan_form_title(),
        )


class DeleteONAScanXLSForm(Task):
    required_inputs = ["collect"]

    def _process(self):
        """remove form on ONA and remove form ID in Collect"""
        if self.kwargs["collect"].ona_scan_form_pk:
            delete_form(self.kwargs["collect"].ona_scan_form_pk)

        self.kwargs["collect"].ona_scan_form_pk = None
        self.kwargs["collect"].save()

    def _revert(self):
        """upload scan xlsform to ONA"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        resp = upload_xlsform(self.kwargs.get("xlsx"))

        # save ONA primary key as required by API
        self.kwargs["collect"].ona_scan_form_pk = resp["formid"]
        self.kwargs["collect"].save()


class UnshareForm(Task):
    required_inputs = ["collect"]

    def _process(self):
        """remove agent user permission to submit to form"""
        if self.kwargs["collect"].ona_scan_form_pk:
            unshare_form(self.kwargs["collect"].ona_scan_form_pk)

    def _revert(self):
        """add agent user permission to submit to form"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        share_form(self.kwargs["collect"].ona_scan_form_pk)


class RemoveItemsetsToONAForm(Task):
    required_inputs = ["collect"]
    # required_outputs = ["uploaded_csv"]

    def _process(self):
        """remove itemsets CSV from ONA medias"""
        if "uploaded_csv" in self.output:
            delete_media(self.kwargs["collect"], self.output["uploaded_csv"]["id"])
        # in case of cold revert, no output present so no media ID
        else:
            targets_csv_id = get_media_id(
                self.kwargs["collect"].ona_scan_form_pk, "targets.csv"
            )
            if targets_csv_id is not None:
                delete_media(self.kwargs["collect"], targets_csv_id)

    def _revert(self):
        """upload itemsets CSV to ONA as media"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        self.output["uploaded_csv"] = upload_csv_media(
            form_pk=self.kwargs["collect"].ona_scan_form_pk,
            media_csv=self.kwargs["targets_csv"],
            media_fname="targets.csv",
        )


class MarkCollectAsStarted(Task):
    required_inputs = ["collect"]

    def _process(self):
        """return Collect status to STARTED"""
        self.kwargs["collect"].change_status(self.kwargs["collect"].STARTED)

    def _revert(self):
        """change collect status to ENDED"""
        if not self.kwargs.get("collect"):
            logger.error("Collect not in kwargs")
            return
        self.kwargs["collect"].change_status(self.kwargs["collect"].ENDED)


class ReopenCollectTaskCollection(TaskCollection):
    tasks = [
        ReEnableONAForm,
        RemoveFormData,
        ResetONAData,
        RemoveTargetsDocuments,
        RemoveItemsetsCSV,
        RemoveScanXLSForm,
        DeleteONAScanXLSForm,
        UnshareForm,
        RemoveItemsetsToONAForm,
        MarkCollectAsStarted,
    ]
