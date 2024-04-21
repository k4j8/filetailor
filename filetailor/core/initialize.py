#!/usr/bin/env python3
"""Creates filetailor.ini if it doesn't exist. Creates directories if it does
exist.
"""

import configparser
import os
import shutil
import sys
import tempfile
from pathlib import Path

import filetailor.config as ftconfig
import filetailor.helpers.okay_to_continue as okay
from filetailor.helpers import cprint, load_ini_files
from filetailor.helpers.get_option import main as get_option


def copy_filetailor_ini(data, os_path):
    """Copy "filetailor.ini" and "example_filetailor.ini"""

    if not get_option('dry_run'):
        shutil.copyfile(os.path.join(data, 'filetailor.yaml'),
                        os_path)
    cprint.success(f'Created "{os_path}" and default "filetailor.yaml".')


def create_filetailor_ini(filetailor_ini_path):
    """Create filetailor.ini if it doesn't exist"""

    if okay.main(f'Create "{filetailor_ini_path}"?', 'y'):
        parent_dir = Path(filetailor_ini_path).parent.absolute()
        if not os.path.isdir(parent_dir):
            # Create filetailor directory if it does not exist
            if not os.path.isfile(parent_dir) and not get_option('dry_run'):
                os.makedirs(parent_dir)
            else:
                cprint.plain(f'File named "{parent_dir}" already exists. '
                             + 'Please delete it and try again.')

        dirs = ftconfig.dirs

        # Create `filetailor.ini`
        config = configparser.ConfigParser()
        config['PATHS'] = {}
        config['PATHS']['sync_dir'] = os.path.join(dirs.user_data_dir, 'sync')
        config['PATHS']['yaml']     = os.path.join(dirs.user_data_dir, 'filetailor.yaml')
        if sys.platform in ['linux', 'darwin']:
            config['PATHS']['in-progress_dir'] = dirs.user_cache_dir
        else:
            config['PATHS']['in-progress_dir'] = os.path.join(
                tempfile.gettempdir(), 'filetailor')
        config['TOOLS'] = {}
        config['TOOLS']['diff_pager'] = 'None'
        config['TOOLS']['difftool'] = 'None'
        with open(filetailor_ini_path, 'w', encoding='UTF-8') as configfile:
            config.write(configfile)

        cprint.success(f'\nCreated "{filetailor_ini_path}".')
        cprint.plain('Update "filetailor.ini" with your desired '
                     + 'locations for synced files and configuration YAML, '
                     + 'then run "filetailor init" again '
                     + 'to create the directories.')
    else:
        cprint.plain('Exiting...')


def main():
    """Read filetailor.ini"""

    filetailor_ini_path = load_ini_files.find_filetailor_ini()
    if not os.path.isfile(filetailor_ini_path):
        # If filetailor.ini does not exist, create it
        create_filetailor_ini(filetailor_ini_path)
        sys.exit()

    # If filetailor.ini does exist, load it and proceed
    filetailor_ini = load_ini_files.read_filetailor_ini(
        filetailor_ini_path)
    paths = filetailor_ini['PATHS']

    # Get location of data directory
    data = ftconfig.data

    cprint.plain('Reading settings from "filetailor.ini"...')

    # If sync_dir, yaml, and in-progress_dir do not exist, create them
    cprint.plain('Creating filetailor directories...')
    init_complete = True

    # Check folders exist
    for key in ['sync_dir', 'yaml', 'in-progress_dir']:

        if key not in paths:
            cprint.error(f'\nMissing "{key}" in "filetailor.ini"')
            init_complete = False
            continue

        # Convert to Path type
        os_path = Path(paths[key])

        # Check if folder exists, otherwise create path
        if os.path.isdir(os_path):
            cprint.plain(f'\n"{os_path}" already exists ({key}).')
        else:
            if okay.main(f'\nCreate "{os_path}" for {key}?', 'y'):
                if not get_option('dry_run'):
                    if key == 'yaml':
                        # Copy the default filetailor.yaml for yaml
                        copy_filetailor_ini(data, os_path)
                    else:
                        Path(os_path).mkdir(parents=True)
                else:
                    cprint.success(f'Created "{os_path}".')
            else:
                init_complete = False

    if init_complete:
        cprint.plain('\nfiletailor initialization complete. Be sure to use Git, '
                     + 'Syncthing, etc. to sync the `sync_dir` and `yaml` '
                     + 'directories between your devices.')
    else:
        cprint.error('\nfiletailor initialization NOT complete, run ' +
                     '"filetailor init" again.')
