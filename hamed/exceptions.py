#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import re

logger = logging.getLogger(__name__)


class ONAAPIError(Exception):

    def __init__(self,
                 http_code, error_code=None,
                 message=None, description=None,
                 *args, **kwargs):
        super(ONAAPIError, self).__init__(*args, **kwargs)
        self.http_code = http_code
        self.error_code = error_code
        self.message = message
        self.description = description

    @property
    def code(self):
        return self.error_code

    @classmethod
    def from_request(cls, request):
        try:
            response = request.json()
            assert isinstance(response, dict)
        except:
            response = {}

        # unexpected answer (probably empty)
        if not len([k for k in ('code', 'error', 'requestError')
                    if k in response.keys()]):
            return cls.generic_http(request.status_code)

        data = {"description": request.text}
        # # regular API error syntax
        # if "code" in response.keys():
        #     data = _standard()
        # elif "requestError" in response.keys():
        #     data = _requestError()
        # # OAuth error syntax
        # else:
        #     data = _oauth()

        return cls(http_code=request.status_code, **data)

    @classmethod
    def generic_http(cls, http_code):
        return cls(http_code=http_code)

    def to_text(self):
        code = " {code}".format(code=self.code) if self.code else ""
        text = "HTTP{http}{code}. {msg}: {desc}".format(
            http=self.http_code,
            code=code,
            msg=self.message,
            desc=self.description)
        return text

    def __str__(self):
        return "<{cls} {text}>".format(cls=self.__class__.__name__,
                                       text=self.to_text())
