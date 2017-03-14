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
from django.utils import timezone

from hamed.models.collects import Collect
from hamed.utils import (list_files, find_export_disk, prepare_disk,
                         unmount_device)

logger = logging.getLogger(__name__)
clients = []


def pgresponse(pc, message, status='in-progress'):
    return json.dumps({'progress': pc,
                       'message': message,
                       'status': status})


class CopyProgressTicker(object):
    def __init__(self, nb_expected, client):
        self.nb_copied = 0
        self.nb_expected = nb_expected
        self.client = client

    def tick(self, filename):
        logger.debug("TICK {}".format(filename))
        self.nb_copied += 1
        self.client.sendMessage(
            pgresponse(self.percentage(),
                       "Copie de {}".format(filename),
                       status='in-progress'))

    def percentage(self):
        return (self.nb_copied / self.nb_expected) * 100


class USBExportProgress(WebSocket):

    def handleMessage(self):
        jsd = self.json_data

        self.sendMessage("ACK")

        def inform(pc, status, message):
            self.sendMessage(pgresponse(pc, message, status))

        def fail(message):
            inform(100, 'failed', "Échec: {msg}".format(msg=message))
            self.disconnect()

        if jsd is None:
            logger.error("bad request")
            self.disconnect()

        if jsd.get('action') == 'start':
            collect_id = jsd.get('collect_id')
            collect = Collect.get_or_none(collect_id)
            if collect is None:
                inform(100, 'failed',
                       "Aucune collecte avec cet ID `{}`".format(collect_id))
            logger.info("Received start request for {}".format(collect))

            inform(1, 'in-progress', "Préparation de la copie")

            # get device name of the sole USB disk
            try:
                device_path = find_export_disk()
            except Exception as exp:
                fail(exp)
                return
            else:
                inform(5, 'in-progress', "Préparation disque USB")

            # format USB disk
            try:
                mount_point = prepare_disk(device_path)
            except Exception as exp:
                logger.exception(exp)
                fail("Impossible de formatter le disque USB {}"
                     .format(device_path))
                unmount_device(device_path)
                P(mount_point).removedirs_p()
                return
            else:
                inform(10, 'in-progress', "Formattage disque USB terminé")
                logger.debug("USB preparation complete")

            src = collect.get_documents_path()
            dst = mount_point
            all_files = list_files(src)
            from pprint import pprint as pp ; pp(all_files)
            ticker = CopyProgressTicker(nb_expected=len(all_files),
                                        client=self)

            def _copy_files(src, dst, ticker, device_path):
                errors = []
                inform(15, 'in-progress', "Copie des fichiers en cours…")
                logger.debug("Starting file copy")
                for index, filename in enumerate(all_files):
                    ticker.tick(filename=filename)
                    df = P(os.path.join(dst, filename))
                    df.parent.makedirs_p()
                    try:
                        P(os.path.join(src, filename)).copy2(df)
                    except Exception as exp:
                        errors.append((filename, exp))
                if len(errors) == 0:
                    inform(100, 'success',
                           "Copie terminée avec succès: {} fichiers."
                           .format(ticker.nb_expected))
                    logger.debug("All files copied")
                else:
                    fail("Des erreurs ont eu lieu")
                logger.debug("unmounting and removing USB disk")
                unmount_device(device_path)
                P(dst).removedirs_p()

            t = threading.Thread(target=_copy_files,
                                 args=[src, dst, ticker, device_path])
            t.start()

    def handleConnected(self):
        print (self.address, 'connected')
        for client in clients:
            client.sendMessage(self.address[0] + u' - connected')
        clients.append(self)

    def handleClose(self):
        clients.remove(self)
        print (self.address, 'closed')
        for client in clients:
            client.sendMessage(self.address[0] + u' - disconnected')

    @property
    def json_data(self):
        try:
            return json.loads(self.data)
        except:
            return None


class Command(BaseCommand):
    help = "Generate documents for a Target"

    def handle(self, *args, **kwargs):
        logger.debug("Export server for {}"
                     .format(settings.COLLECT_DOCUMENTS_FOLDER))

        server = SimpleWebSocketServer(
            '0.0.0.0', settings.WEBSOCKET_SERVER_PORT,
            USBExportProgress)

        def close_sig_handler(signal, frame):
            if server is not None:
                server.close()

        signal.signal(signal.SIGINT, close_sig_handler)

        logger.info("Starting WSS")
        server.serveforever()
