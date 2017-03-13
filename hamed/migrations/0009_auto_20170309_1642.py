# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-09 16:42
from __future__ import unicode_literals

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('hamed', '0008_auto_20170308_1924'),
    ]

    operations = [
        migrations.RenameField(
            model_name='target',
            old_name='dataset',
            new_name='form_dataset',
        ),
        migrations.AddField(
            model_name='target',
            name='scan_form_dataset',
            field=jsonfield.fields.JSONField(blank=True, default=dict),
        ),
    ]