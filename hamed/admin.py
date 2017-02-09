#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from django.contrib.admin import AdminSite
from hamed.models.collects import Collect
from hamed.models.targets import Target
from hamed.models.settings import Settings


class HamedAdminSite(AdminSite):
    site_header = "hamed"

admin_site = HamedAdminSite(name='myadmin')

admin_site.register(Collect)
admin_site.register(Target)
admin_site.register(Settings)
