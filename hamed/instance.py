#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import re


class Instance(dict):

    def __init__(self, *args, **kwargs):
        super(Instance, self).__init__(*args, **kwargs)
        self.parse()

    @classmethod
    def clean_firstnames(cls, firstnames):
        return firstnames.strip().title() if firstnames else None

    @classmethod
    def clean_lastname(cls, lastname):
        return lastname.strip().upper() if lastname else None

    @classmethod
    def clean_name(cls, lastname, firstnames):
        if firstnames and lastname:
            return "{lastname} {firstnames}".format(firstnames=firstnames,
                                                    lastname=lastname)
        elif firstnames:
            return firstnames
        return lastname

    @property
    def firstnames(self):
        return self.clean_firstnames(self.get('prenoms'))

    @property
    def lastname(self):
        return self.clean_lastname(self.get('nom'))

    @property
    def name(self):
        if self.firstnames and self.lastname:
            return "{lastname} {firstnames}".format(
                firstnames=self.firstnames, lastname=self.lastname)
        elif self.firstnames:
            return self.firstnames
        return self.lastname

    @property
    def uuid(self):
        return self.get("instanceID")[5:13]

    @property
    def ident(self):
        return "{uuid}: {name}".format(uuid=self.uuid, name=self.name)

    @property
    def folder_name(self):
        return "{nom}-{uuid}".format(
            nom=re.sub(r'\[\]/\;,\>\<\&\*\:\%\=\+\@\!\#\^\(\)\|\?',
                       '', self.name),
            uuid=self.uuid)

    @property
    def region(self):
        return self.get('region').strip().upper() or None

    @property
    def cercle(self):
        return self.get('cercle').strip().upper() or None

    @property
    def commune(self):
        return self.get('commune').strip().upper() or None

    @property
    def location(self):
        return "/".join([part for part
                         in (self.commune, self.cercle, self.region)
                        if part is not None])

    @property
    def medias(self):
        return self._medias

    def get_medias(self):
        medias = {}
        keys = ("filename", "type", "url")
        is_media = lambda d: sum([1 for k in keys
                                  if k in d.keys()]) == len(keys)

        def walk_dict(adict, parent_key=[]):
            for key, value in adict.items():
                new_parent_key = parent_key + [key]
                if isinstance(value, dict):
                    if is_media(value):
                        medias.update({"/".join(new_parent_key): value})
                    else:
                        walk_dict(value, parent_key=new_parent_key)
                elif isinstance(value, list):
                    walk_list(value, parent_key=new_parent_key)

        def walk_list(alist, parent_key=[]):
            for value in alist:
                if isinstance(value, dict):
                    walk_dict(value, parent_key=parent_key)
                elif isinstance(value, list):
                    walk_list(value, parent_key=parent_key)

        walk_dict(self)
        return medias

    def parse(self):
        self._medias = self.get_medias()
