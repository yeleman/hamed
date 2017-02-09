#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

import openpyxl

logger = logging.getLogger(__name__)


class IncorrectExcelFile(ValueError):
    pass


def letter_to_column(letter):
    return openpyxl.utils.cell.column_index_from_string(letter)


def column_to_letter(column):
    return openpyxl.utils.cell.get_column_letter(column)


def indexes_to_coordinate(row, column):
    return "{c}{r}".format(c=column_to_letter(column), r=row + 1)
