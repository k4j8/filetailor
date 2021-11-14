#!/usr/bin/env python3
"""Delete filetailor directories"""

import os
import shutil
from pathlib import Path

import filetailor.helpers.okay_to_continue as okay
from filetailor.helpers import cprint, load_ini_files
from filetailor.helpers.get_option import main as get_option


def delete(file_path):
    """Ask to permanently remove file or directory"""
    if okay.main(f'\nOkay to PERMANENTLY DELETE "{file_path}"?', 'n'):
        try:
            if not get_option('dry_run'):
                shutil.rmtree(file_path)
            cprint.success(f'Deleted "{file_path}".')
            delete_successful = True
        except NotADirectoryError:
            os.remove(file_path)
            cprint.success(f'Deleted "{file_path}".')
            delete_successful = True
        except:
            cprint.error(f'ERROR: Could not delete "{file_path}".')
            delete_successful = False
    else:
        delete_successful = False

    return delete_successful


def main():
    """Delete filetailor directories"""
    filetailor_ini_path = load_ini_files.find_filetailor_ini()
    filetailor_ini = load_ini_files.read_filetailor_ini(filetailor_ini_path)
    paths = filetailor_ini['PATHS']

    cprint.plain('Searching for directories to remove...')
    uninstall_successful = True
    for dir_str in paths:
        dir_path = Path(paths[dir_str]).resolve()
        if dir_path.is_dir():
            uninstall_successful = delete(dir_path)

    if uninstall_successful:
        if delete(filetailor_ini_path):
            cprint.plain('\nUninstall complete.')
