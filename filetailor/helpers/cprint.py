#!/usr/bin/env python3
"""Prints colored text"""

import filetailor.helpers.get_option
from termcolor import cprint


def is_quiet(cfile, cdevice):
    """Get whether quiet is true or false"""

    return filetailor.helpers.get_option.main('quiet', cfile, cdevice)


def plain(text, cfile=None, cdevice=None):
    """Print uncolored text"""
    if not is_quiet(cfile, cdevice):
        print(text)


def error(text, cfile=None, cdevice=None):
    """Color text for errors"""
    if not is_quiet(cfile, cdevice):
        cprint(text, 'red')


def success(text, cfile=None, cdevice=None):
    """Color text for successfully modifying files"""
    if not is_quiet(cfile, cdevice):
        cprint(text, 'white', 'on_blue')


def same(text, cfile=None, cdevice=None):
    """Color text for printing files that are the same"""
    if not is_quiet(cfile, cdevice):
        cprint(text, 'green')


def differ(text, cfile=None, cdevice=None):
    """Color text for printing files that differ"""
    if not is_quiet(cfile, cdevice):
        cprint(text, 'red')
