#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

import requests

from hamed.models.settings import Settings
from hamed.exceptions import ONAAPIError

ONA_API = '/api/v1'
ONA_MEDIA = '/media'
XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml' \
            '.sheet; charset=binary'
CSV_MIME = 'text/plain; charset=utf-8'

logger = logging.getLogger(__name__)


def get_base_url():
    return Settings.get_or_none(Settings.ONA_SERVER).value


def get_url(path):
    return ''.join([get_base_url(), path])


def get_api_path(path):
    return ''.join([ONA_API, path])


def get_username():
    return Settings.get_or_none(Settings.ONA_USERNAME).value


def get_auth_header():
    return {'Authorization': "Token {token}".format(
        token=Settings.get_or_none(Settings.ONA_TOKEN).value)}


def post(path, payload={}, headers={}, files={},
         expected_codes=(200, 201), silent_failure=False):
    return request(method='POST', path=path, payload=payload,
                   headers=headers, files=files,
                   expected_codes=expected_codes,
                   silent_failure=silent_failure)


def get(path, payload={}, headers={}, files={},
        expected_codes=(200, 204), silent_failure=False):
    return request(method='GET', path=path,
                   headers=headers, files=files,
                   expected_codes=expected_codes,
                   silent_failure=silent_failure)


def request(method, path, payload={}, headers={}, files={},
            silent_failure=False, expected_codes=(200, 201, 204)):
    url = get_url(path)
    func = requests.post if method == 'POST' else requests.get
    headers.update(get_auth_header())
    req = func(url=url, data=payload, files=files, headers=headers)
    from pprint import pprint as pp ; pp(req.request.url)
    from pprint import pprint as pp ; pp(req.request.headers)
    try:
        assert req.status_code in expected_codes
        return req.json()
    except AssertionError:
        exp = ONAAPIError.from_request(req)
        logger.error("ONA Request Error. {exp}".format(exp=exp))
        logger.exception(exp)
        if not silent_failure:
            raise exp


def upload_xlsform(xls_file, silent_failure=False):
    return post(path=get_api_path('/forms'),
                files={'xls_file':  ('xform.xlsx', xls_file,
                                     XLSX_MIME, {'Expires': '0'})},
                expected_codes=(201,))


def get_form_detail(form_pk):
    return get(get_api_path('/forms/{id}'.format(id=form_pk)))


def toggle_downloadable_ona_form(form_pk, downloadable):
    url = get_url(get_api_path('/forms/{}'.format(form_pk)))
    req = requests.patch(url=url,
                         headers=get_auth_header(),
                         data={'downloadable': downloadable})
    try:
        assert req.status_code == 200
        return req.json()
    except AssertionError:
        exp = ONAAPIError.from_request(req)
        logger.error("ONA Request Error. {exp}".format(exp=exp))
        logger.exception(exp)


def disable_form(form_pk):
    return toggle_downloadable_ona_form(form_pk, False)


def enable_form(form_pk):
    return toggle_downloadable_ona_form(form_pk, True)


def get_form_data(form_pk):
    return get(get_api_path('/data/{id}'.format(id=form_pk)))


def get_media_size(filename):
    url = get_url('/{media}/{fname}'.format(media=ONA_MEDIA,
                                            fname=filename))
    resp = requests.head(url)
    return int(resp.headers['Content-Length'])


def upload_csv_media(form_pk, media_csv, media_fname):
    return post(
        path=get_api_path('/metadata.json'),
        payload={'data_value': media_fname,
                 'data_type': 'media',
                 'xform': form_pk},
        files={'data_file':  (media_fname, media_csv,
                              CSV_MIME, {'Expires': '0'})},
        expected_codes=(201,))
