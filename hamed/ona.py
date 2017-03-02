#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
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


def post(path, payload={}, headers={}, files={}, params={},
         expected_codes=(200, 201), as_json=True, silent_failure=False):
    return request(method='POST', path=path, payload=payload, params=params,
                   headers=headers, files=files,
                   expected_codes=expected_codes,
                   as_json=as_json,
                   silent_failure=silent_failure)


def delete(path, payload={}, headers={}, files={}, params={},
           expected_codes=(200, 201), as_json=False, silent_failure=False):
    return request(method='DELETE', path=path, payload=payload, params=params,
                   headers=headers, files=files,
                   expected_codes=expected_codes,
                   as_json=as_json,
                   silent_failure=silent_failure)


def get(path, payload={}, headers={}, files={}, params={},
        expected_codes=(200, 204), as_json=True, silent_failure=False):
    return request(method='GET', path=path,
                   payload=payload, params=params,
                   headers=headers, files=files,
                   expected_codes=expected_codes,
                   as_json=as_json,
                   silent_failure=silent_failure)


def request(method, path, payload={}, headers={}, files={}, params={},
            expected_codes=(200, 201, 204), as_json=True,
            silent_failure=False):
    url = get_url(path)
    methods = {'POST': requests.post, 'DELETE': requests.delete,
               'GET': requests.get, 'OPTIONS': requests.options,
               'HEAD': requests.head, 'PUT': requests.put,
               'PATCH': requests.patch}
    func = methods.get(method, requests.get)
    headers.update(get_auth_header())
    req = func(url=url, params=params, data=payload,
               files=files, headers=headers)
    # from pprint import pprint as pp ; pp(req.request.url)
    # from pprint import pprint as pp ; pp(req.request.headers)
    try:
        assert req.status_code in expected_codes
        if as_json:
            return req.json()
        return req.text
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
    # TODO: move to patch method
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


def delete_form(form_pk):
    return delete(get_api_path('/forms/{}'.format(form_pk)),
                  expected_codes=(204,), as_json=False)


def get_form_data(form_pk):
    return get(get_api_path('/data/{id}'.format(id=form_pk)))


def get_media_size(filename):
    url = get_url('{media}/{fname}'.format(media=ONA_MEDIA,
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


def delete_media(collect, media_id):
    session = requests.Session()

    # first authenticate with token
    resp = session.get(get_url("/token-auth"), headers=get_auth_header())
    assert resp.status_code == 200

    # simulate click on remove button
    path = "/{username}/forms/{form_id}/formid-media/{media_id}".format(
        username=Settings.ona_username(),
        form_id=collect.ona_form_id(),
        media_id=media_id)
    resp = session.get(url=get_url(path),
                       params={"del": "true"})
    assert resp.status_code in (302, 200)


def download_media(path):
    url = get_url(path)
    req = requests.get(url)

    try:
        assert req.status_code == 200
        data = io.BytesIO(req.content)
        data.seek(0)
        return data
    except AssertionError:
        exp = ONAAPIError.from_request(req)
        logger.error("ONA Request Error. {exp}".format(exp=exp))
        logger.exception(exp)


def get_media_id(form_pk, media_fname):
    resp = get(get_api_path("/metadata.json"), params={"xform": form_pk})
    filtered = [data for data in resp
                if data['xform'] == form_pk
                and data['data_value'] == media_fname]
    try:
        return filtered[0]['id']
    except IndexError:
        return None
