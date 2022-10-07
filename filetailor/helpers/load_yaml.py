#!/usr/bin/env python3
"""Imports YAML"""

import logging
import os
import sys

import yaml
from filetailor.helpers import cprint
from filetailor.helpers.load_ini_files import find_filetailor_ini

DEFAULT_KEYS = ['vars', 'yaml_only', 'file_only', 'quiet', 'no_diff', 'no_backup',
                'yes', 'dry_run', 'sudo', 'staging']
FILE_KEYS = ['path', 'vars', 'quiet', 'no_diff', 'no_backup', 'yes', 'dry_run',
             'sudo', 'staging', 'unique', 'include_devices', 'exclude_devices',
             'include_contents', 'exclude_contents', 'scripts']


def check_for_duplicates(paths, dictionary, key):
    """Checks for duplicate keys in YAML"""
    if key in dictionary:
        cprint.error(f'ERROR: Duplicate key "{key}". Please correct ' +
                     f'"{paths["yaml_dir"]}".')
        sys.exit()
    return 0


def validate_yaml(input_yaml, valid_keys, name):
    """Check that all keys are valid inputs"""
    if input_yaml is not None:
        for key in input_yaml:
            if key not in valid_keys:
                cprint.error(f'Key "{key}" in YAML "{name}" is not valid. '
                             + 'Please fix.')


def main(paths):
    """Imports YAML"""
    logging.debug('Running load_yaml')

    # Check directories exist
    folders_found = True
    expected_folders = ('yaml_dir', 'sync_dir', 'in-progress_dir')
    for expected_folder in expected_folders:
        if expected_folder not in paths.keys():
            filetailor_ini_path = find_filetailor_ini()
            cprint.error(f'"{expected_folder}" not found in '
                         + f'"{filetailor_ini_path}".')
            folders_found = False
    if not folders_found:
        cprint.plain('Exiting...')
        sys.exit()

    # Get list of all YAML files and merge
    yaml_path = os.path.join(paths['yaml_dir'], 'filetailor.yaml')
    with open(yaml_path, 'r') as f:
        data = yaml.load(f, Loader=yaml.Loader)

    # Split YAML into 3 dictionaries
    yaml_default = {}
    yaml_devices = {}
    yaml_files = {}
    if data:
        for key in data.keys():
            key_type, _, key_value = key.partition(' ')
            if key_type == 'default':
                # default
                yaml_default = data['default']
            else:
                if key_type == 'device':
                    # Device
                    yaml_devices[key_value] = data[key]
                elif key_type == 'file':
                    # File
                    yaml_files[key_value] = data[key]

    logging.debug('')
    logging.debug('yaml_default = %s', yaml_default)
    logging.debug('yaml_devices = %s', yaml_devices)
    logging.debug('yaml_files = %s', yaml_files)
    logging.debug('')
    logging.debug('yaml_default:\n%s',
                  yaml.dump(yaml_default, Dumper=yaml.Dumper))
    logging.debug('yaml_devices:\n%s',
                  yaml.dump(yaml_devices, Dumper=yaml.Dumper))
    logging.debug('yaml_files:\n%s',
                  yaml.dump(yaml_files, Dumper=yaml.Dumper))
    logging.debug('')

    validate_yaml(yaml_default, DEFAULT_KEYS, 'default')
    for device in yaml_devices:
        validate_yaml(yaml_devices[device],
                      DEFAULT_KEYS + ['hostname'],
                      'device ' + device)
    for file in yaml_files:
        validate_yaml(yaml_files[file],
                      FILE_KEYS,
                      'file ' + file)

    return (yaml_default, yaml_devices, yaml_files)
