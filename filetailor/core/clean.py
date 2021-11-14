#!/usr/bin/env python3
"""Remove files from sync_dir that are no longer defined in YAML"""

import os
import shutil

import filetailor.config as ftconfig
import filetailor.helpers.okay_to_continue as okay
from filetailor.helpers import cprint
from filetailor.helpers.get_option import main as get_option


def file_in_yaml(sync_file, yaml_files):
    """Returns if `sync_file` is in `yaml_files` without the "unique" attribute
    OR `sync_file` without its unique part is in `yaml_files` and the "unique"
    attribute is present
    """

    underscore_location = sync_file.rfind('_')
    if underscore_location != -1:
        # Check if this file is saved with "unique" formatting
        unique_id = sync_file[:underscore_location]
        try:
            if yaml_files[unique_id]['unique']:
                # This file matches the unique formatting and the file has
                # the unique attribute
                return True
        except (KeyError, TypeError):
            pass
    if sync_file in yaml_files:
        # Check this file is NOT saved with "unique" formatting
        try:
            if yaml_files[sync_file]['unique']:
                # This file matches the file ID, but it doesn't have a unique
                # extension and this file has the unique attribute
                return False
        except (KeyError, TypeError):
            pass

        # This file is in the YAML
        return True

    # This file was not found in the YAML
    return False


def main():
    """Remove files from sync_dir that are no longer defined in YAML"""
    paths = ftconfig.paths

    cprint.plain('Searching for files in sync folder not listed in YAML...')
    sync_files = os.listdir(paths['sync_dir'])
    yaml_files = ftconfig.yaml_files
    orphans_found = False
    for sync_file in sync_files:
        if not file_in_yaml(sync_file, yaml_files):
            orphans_found = True
            if okay.main(f'\nOkay to delete "{sync_file}" from sync folder '
                         + '(no longer tracked in YAML)?', 'y'):
                sync_file_path = os.path.join(paths['sync_dir'], sync_file)
                try:
                    if not get_option('dry_run'):
                        shutil.rmtree(sync_file_path)
                    cprint.success(f'Deleted "{sync_file}" from sync folder.')
                except NotADirectoryError:
                    os.remove(sync_file_path)
                    cprint.success(f'Deleted "{sync_file}" from sync folder.')
    if orphans_found:
        cprint.plain('\nClean complete.\n')
    else:
        cprint.plain('\nNo untracked files found.\n')
