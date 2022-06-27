#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import os
import platform
import subprocess
import http.server
import socketserver

logger = logging.getLogger(__name__)
PORT = 8000


def is_running():
    p = subprocess.run(["curl", "http://localhost:{}".format(PORT)])
    return p.returncode == 0


def open_finder_at(abs_path):
    if platform.system() == "Windows":
        os.startfile(abs_path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", abs_path])
    else:
        subprocess.Popen(["xdg-open", abs_path])


class FolderRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if not self.path == "/":
            open_finder_at(self.path)
            self.path = "/"
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


if __name__ == "__main__":

    if not is_running():
        httpd = socketserver.TCPServer(("", PORT), FolderRequestHandler)
        print("serving at port", PORT)
        httpd.serve_forever()
    else:
        print("already running, exiting.")
