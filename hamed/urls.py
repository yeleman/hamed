#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import unicode_literals, absolute_import, division, print_function

from django.conf.urls import url
from hamed import views
from hamed.admin import admin_site

urlpatterns = [
    url(r"^$", views.home, name="home"),
    url(r"^collect/(?P<collect_id>[0-9]+)/?$", views.collect, name="collect"),
    url(
        r"^collect/(?P<collect_id>[0-9]+)/targets/?$",
        views.collect_data,
        name="collect_data",
    ),
    url(r"^start/?$", views.start_collect, name="start_collect"),
    url(r"^end/(?P<collect_id>[0-9]+)/?$", views.end_collect, name="end_collect"),
    url(
        r"^finalize/(?P<collect_id>[0-9]+)/?$",
        views.finalize_collect,
        name="finalize_collect",
    ),
    url(
        r"^reopen/(?P<collect_id>[0-9]+)/?$",
        views.reopen_collect,
        name="reopen_collect",
    ),
    url(
        r"attachment/(?P<fname>[a-zA-Z0-9\-\_\.]+)",
        views.attachment_proxy,
        name="attachment",
    ),
    # advanced actions
    url(
        r"^collect/(?P<collect_id>[0-9]+)/drop_scan_data/?$",
        views.collect_drop_scan_data,
        name="collect_drop_scan_data",
    ),
    url(
        r"^collect/(?P<collect_id>[0-9]+)/drop_data/?$",
        views.collect_drop_data,
        name="collect_drop_data",
    ),
    url(
        r"^collect/(?P<collect_id>[0-9]+)/downgrade/?$",
        views.collect_downgrade,
        name="collect_downgrade",
    ),
    url(
        r"^collect/(?P<collect_id>[0-9]+)"
        r"/delete-target/(?P<target_id>[a-zA-Z0-9]{5})?$",
        views.delete_target,
        name="delete_target",
    ),
    url(
        r"^collect/(?P<collect_id>[0-9]+)/export.(?P<format>json|xlsx)$",
        views.exports_proxy,
        name="collect_exports",
    ),
    url(
        r"^collect/(?P<collect_id>[0-9]+)/upload/?$",
        views.upload_data,
        name="collect_upload",
    ),
    url(r"^help/?$", views.help, name="help"),
    url(r"^advanced/?$", views.advanced_mode, name="advanced_mode"),
    url(r"^admin/", admin_site.urls),
]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
