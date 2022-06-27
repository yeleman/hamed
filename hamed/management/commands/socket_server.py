#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import signal
import json
import os
import threading

from path import Path as P
from SimpleWebSocketServer import WebSocket, SimpleWebSocketServer
from django.core.management.base import BaseCommand
from django.conf import settings

from hamed.models.collects import Collect
from hamed.utils import list_files, find_export_disk, prepare_disk, unmount_device

FAILED = "failed"
SUCCESS = "success"
IN_PROGRESS = "in-progress"

logger = logging.getLogger(__name__)
clients = []


def pgresponse(pc, message, status=IN_PROGRESS):
    return json.dumps(
        {"progress": pc, "message": message.replace("\n", "<br />"), "status": status}
    )


class CopyProgressTicker(object):
    def __init__(self, nb_expected, client):
        self.nb_copied = 0
        self.nb_expected = nb_expected
        self.client = client

    def tick(self, filename):
        logger.debug("TICK {}".format(filename))
        self.client.sendMessage(
            pgresponse(
                self.percentage(), "Copie de {}".format(filename), status="in-progress"
            )
        )
        self.nb_copied += 1

    def percentage(self):
        return (self.nb_copied / self.nb_expected) * 100


class USBExportProgress(WebSocket):
    def __init__(self, *args, **kwargs):
        self.collect = None
        self.device_path = None
        self.mount_point = None

        self.percent = 0
        self.status = IN_PROGRESS
        self.message = "En préparation…"
        super(USBExportProgress, self).__init__(*args, **kwargs)

    @property
    def percentage(self):
        return self.percent

    def update(self, percentage, status):
        self.percent = percentage
        self.status = status

    def up_inform(self, percentage, status, message):
        self.update(percentage, status)
        self.inform(message)

    def inform(self, message):
        self.sendMessage(pgresponse(self.percentage, message, self.status))

    def fail(self, message):
        self.up_inform(100, FAILED, message)
        self.close()

    def handleMessage(self):
        jsd = self.json_data
        if jsd is None:
            logger.error("bad request")
            self.fail("bad request")
            return

        if jsd.get("action") == "start":
            collect_id = jsd.get("collect_id")
            self.collect = Collect.get_or_none(collect_id)
            if self.collect is None:
                self.fail("Aucune collecte avec cet ID `{}`".format(collect_id))
                return
            logger.info("Received start request for {}".format(self.collect))

            self.up_inform(1, IN_PROGRESS, "Préparation de la copie")

            threading.Thread(
                target=USBExportProgress.find_usb_disk, args=[self]
            ).start()

    def find_usb_disk(self):
        logger.info("FINDING USB DISK!")
        self.inform("Recherche du disque USB")

        # get device name of the sole USB disk
        try:
            self.device_path = find_export_disk()
        except Exception as exp:
            logger.exception(exp)
            self.fail(exp)
            return
        else:
            self.up_inform(5, IN_PROGRESS, "Disque USB trouvé.")
            threading.Thread(target=USBExportProgress.format_disk, args=[self]).start()

    def format_disk(self):
        self.inform("Formattage du disque USB.")
        # format USB disk
        try:
            self.mount_point = prepare_disk(self.device_path)
        except Exception as exp:
            logger.exception(exp)
            self.fail(
                "Impossible de formatter le disque USB {}".format(self.device_path)
            )
            unmount_device(self.device_path)
            P(self.mount_point).removedirs_p()
            return
        else:
            self.up_inform(10, IN_PROGRESS, "Formattage disque USB terminé.")
            logger.debug("USB preparation complete")
            threading.Thread(target=USBExportProgress.copy_files, args=[self]).start()

    def copy_files(self):

        src = self.collect.get_documents_path()
        dst = self.mount_point
        all_files = list_files(src)
        ticker = CopyProgressTicker(nb_expected=len(all_files), client=self)

        errors = []
        self.up_inform(15, IN_PROGRESS, "Copie des fichiers en cours…")
        logger.debug("Starting file copy")

        for index, filename in enumerate(all_files):
            ticker.tick(filename=filename)
            df = P(os.path.join(dst, filename))
            df.parent.makedirs_p()
            try:
                P(os.path.join(src, filename)).copy2(df)
            except Exception as exp:
                logger.exception(exp)
                errors.append((filename, exp))
        if len(errors) == 0:
            self.up_inform(
                100,
                SUCCESS,
                "Copie terminée avec succès: {} fichiers.".format(ticker.nb_expected),
            )
            logger.debug("All files copied")
        else:
            self.fail(
                "Des erreurs ont eu lieu:\n{errors}".format(
                    errors="\n".join(
                        ["{f}: {exp}".format(f=f, exp=ex) for f, ex in errors]
                    )
                )
            )
        logger.debug("unmounting and removing USB disk")
        unmount_device(self.device_path)
        P(dst).removedirs_p()

    def handleConnected(self):
        print(self.address, "connected")
        for client in clients:
            client.sendMessage(self.address[0] + " - connected")
        clients.append(self)

    def handleClose(self):
        clients.remove(self)
        print(self.address, "closed")
        for client in clients:
            client.sendMessage(self.address[0] + " - disconnected")

    @property
    def json_data(self):
        try:
            return json.loads(self.data)
        except:
            return None


class Command(BaseCommand):
    help = "Generate documents for a Target"

    def handle(self, *args, **kwargs):
        logger.debug("Export server for {}".format(settings.COLLECT_DOCUMENTS_FOLDER))

        server = SimpleWebSocketServer(
            "0.0.0.0", settings.WEBSOCKET_SERVER_PORT, USBExportProgress
        )

        def close_sig_handler(signal, frame):
            if server is not None:
                server.close()

        signal.signal(signal.SIGINT, close_sig_handler)

        logger.info("Starting WSS")
        server.serveforever()
