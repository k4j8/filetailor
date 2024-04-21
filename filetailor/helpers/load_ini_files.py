#!/usr/bin/env python3
"""Loads values from config.ini or filetailor.ini"""

import configparser
import logging
import os
import sys
from pathlib import Path

import filetailor.config as ftconfig
from filetailor.helpers import cprint


def check_paths(paths):
    """Checks 'sync_dir' and 'yaml' are in paths"""

    keys_exist = ('sync_dir' in paths
                  and 'yaml' in paths
                  and 'in-progress_dir' in paths)
    return keys_exist


def read_filetailor_ini(filetailor_ini_path):
    """Loads values from filetailor.ini, called by __main__.py when functions
    are called
    """

    # Read filetailor.ini
    logging.debug('"filetailor.ini" found, adding to "paths"')
    filetailor_ini = configparser.ConfigParser()
    filetailor_ini.read(filetailor_ini_path)

    # Check filetailor.ini for paths
    if ('PATHS' in filetailor_ini) and check_paths(filetailor_ini['PATHS']):
        for path in filetailor_ini['PATHS']:
            # Expand ~ to full path
            filetailor_ini['PATHS'][path] = os.path.expanduser(filetailor_ini['PATHS'][path])
            logging.debug('path for %s = %s', path, filetailor_ini['PATHS'][path])
    else:
        # filetailor_ini incomplete
        cprint.error(f'ERROR: Missing keys from "{filetailor_ini_path}".')
        sys.exit()

    return filetailor_ini


def find_filetailor_ini():
    """Gets location of filetailor.ini based on input and OS"""

    # User override path if defined, otherwise use OS default
    override = ftconfig.override_filetailor_ini_path
    if override != '':
        filetailor_ini_path = Path(os.path.expanduser(override))
    else:
        filetailor_ini_path = os.path.join(
                ftconfig.dirs.user_config_dir, 'filetailor.ini')
    ftconfig.filetailor_ini_path = filetailor_ini_path

    return filetailor_ini_path


def load_config_ini():
    """Loads values from config.ini, called by __main__.py, even when no
    functions are called (such as `filetailor --help`)
    """

    logging.debug('Running load_config_ini')

    # Read config.ini
    data = ftconfig.data
    config_ini_path = os.path.join(data, 'config.ini')
    ftconfig.config_ini_path = config_ini_path
    if not os.path.isfile(config_ini_path):
        cprint.error(f'"config.ini" not found at "{config_ini_path}". Please '
                     + 'reinstall filetailor.')
        sys.exit()
    config_ini = configparser.ConfigParser()
    config_ini.read(config_ini_path)
    logging.debug('config_ini.sections() = %s', config_ini.sections())

    return config_ini
