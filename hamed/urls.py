#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

from django.conf.urls import url
from hamed import views
from hamed.admin import admin_site

urlpatterns = [
    url(r'^$', views.home),
    url(r'^collect/(?P<collect_id>[0-9]+)$', views.collect, name='collect'),
    url(r'^start/?$', views.start_collect, name='start_collect'),
    url(r'^end/(?P<collect_id>[0-9]+)/?$', views.end_collect, name='end_collect'),
    url(r'^finalize/(?P<collect_id>[0-9]+)/?$', views.finalize_collect, name='finalize_collect'),
    url(r'^export/(?P<collect_id>[0-9]+)/?$', views.export, name='export'),
    url(r'^archives/?$', views.archives, name='archives'),

    url(r'^admin/', admin_site.urls),
]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
