#!/usr/bin/env python3
"""Add or remove devices and files from YAML"""

import logging
import os
import sys
from pathlib import Path

import filetailor.config as ftconfig
import filetailor.helpers.okay_to_continue as okay
from filetailor.helpers import cprint
from ruamel.yaml import YAML


def yaml_add(args, yaml_devices, yaml_files, data):
    """Add files to `data` with name if provided, otherwise basename"""

    # Check if enough names provided
    if args.name is not None:
        if len(args.PATHS) > 1 and args.name is not None:
            cprint.error('ERROR: When specifying a name for the file with, only '
                         + 'one file at a time can be added.')
            sys.exit()

    # Add device to `data`
    device = ftconfig.device_id
    if device not in yaml_devices:
        if okay.main(f'Device is not in YAML. Okay to add "{device}"?',
                     'y'):
            data[f'device {device}'] = None
            cprint.success(f'Added "{device}" to YAML.')

    # Add each file to `data`
    for (i, fpath_str) in enumerate(args.PATHS):
        fpath = Path(fpath_str).resolve()
        if args.name is None:
            basename = os.path.basename(fpath)
        else:
            basename = args.name[i]
        if yaml_files and basename in yaml_files:
            print(f'"{basename}" is already in "filetailor.yaml", ' +
                  'skipping file.')
            continue
        data[f'file {basename}'] = {}
        data[f'file {basename}']['path'] = str(fpath.absolute())
        cprint.success(f'File "{basename}" added to YAML.')


def yaml_remove(args, yaml_files, data):
    """Remove files from `data`"""

    files_removed = False

    # Remove each file from `data`
    for fpath_str in args.FILES:
        fpath = Path(fpath_str).resolve()
        basename = os.path.basename(fpath)
        if basename in yaml_files:
            del data[f'file {basename}']
            cprint.success(f'File "{basename}" removed from YAML.')
            files_removed = True
        else:
            cprint.error(f'"{basename}" not in "filetailor.yaml", '
                         + 'skipping file.')

    return files_removed


def main(operation):
    """Add or remove devices and files from YAML"""

    # Import from config
    args = ftconfig.args
    yaml_devices = ftconfig.yaml_devices
    yaml_files = ftconfig.yaml_files

    # Load `filetailor.yaml` using ruamel
    filetailor_yaml_path = os.path.expanduser(
            os.path.join(ftconfig.paths['yaml_dir'], 'filetailor.yaml'))
    ruamel = YAML()
    with open(filetailor_yaml_path, 'r') as filetailor_yaml:
        data = ruamel.load(filetailor_yaml)
    if data is None:
        data = {}

    if operation == 'add':
        yaml_add(args, yaml_devices, yaml_files, data)
        cprint.plain('Run "filetailor backup" to sync the new files.')
    elif operation == 'remove':
        files_removed = yaml_remove(args, yaml_files, data)
        if files_removed:
            cprint.plain('Run "filetailor clean" to delete the removed files.')
        else:
            cprint.plain('No files were removed from YAML.')

    # Show resulting YAML
    if args.dry_run:
        # Debug not working yet
        # https://stackoverflow.com/questions/47614862/best-way-to-use-ruamel-yaml-to-dump-to-string-not-to-stream
        # logging.debug(ruamel.dump(data, None, transform=print))
        logging.debug('data = %s' % data)
    else:
        # Dump `data` to `filetailor.yaml`
        with open(filetailor_yaml_path, 'w') as filetailor_yaml:
            ruamel.dump(data, filetailor_yaml)
