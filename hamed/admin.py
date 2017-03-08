#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from django.contrib import admin
from hamed.models.collects import Collect
from hamed.models.targets import Target
from hamed.models.settings import Settings


class HamedAdminSite(admin.AdminSite):
    site_header = "hamed"

admin_site = HamedAdminSite(name='myadmin')


@admin.register(Settings, site=admin_site)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    list_editable = ('value', )


@admin.register(Collect, site=admin_site)
class CollectAdmin(admin.ModelAdmin):
    list_display = ('id', 'cercle', 'commune', 'status',
                    'nb_submissions', 'nb_indigents',
                    'ended_on', 'finalized_on',
                    'ona_form_pk', 'ona_scan_form_pk')
    list_filter = ('status', 'cercle_id', 'commune_id')


@admin.register(Target, site=admin_site)
class TargetAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'last_name', 'first_name', 'gender',
                    'age', 'is_indigent', 'collect')
    list_filter = ('collect', 'gender', 'is_indigent')
