#!/usr/bin/env python3
"""Entry point for filetailor. Calls other helper functions to load configs and
YAML. Calls other core functions to modify files and YAML.
"""

import argparse
import logging
import os
import platform
import sys
from pathlib import Path
import pkg_resources

import filetailor.config as ftconfig
import filetailor.core.clean
import filetailor.core.initialize
import filetailor.core.paths
import filetailor.core.sync
import filetailor.core.uninstall
import filetailor.core.update_yaml
import filetailor.helpers.load_yaml
from filetailor.helpers import load_ini_files

__version__ = pkg_resources.require('filetailor')[0].version


def get_hostname():
    """Returns the hostname of the machine"""

    return platform.node()


def get_device_id(yaml_devices, device):
    """Given device (device_id or hostname), returns the device_id

    Example YAML:
    ```yaml
    device DEVICE_ID:
      hostname: HOSTNAME
    ```
    """

    device_id = device
    if device not in yaml_devices:
        # Search hostnames
        for key in yaml_devices.keys():
            if yaml_devices[key] and 'hostname' in yaml_devices[key]:
                if device == yaml_devices[key]['hostname']:
                    device_id = key

    return device_id


# PARSERS

def update_parser_all(parser, config_ini):
    """Adds arguments to the parser"""
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='suppress all output not requiring user input')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='suppress all output requiring user input by '
                        + 'assuming yes')
    if config_ini['DEFAULT'].get('testing', False):
        parser.add_argument('--debug', action='store_true',
                            help='display debug info')
        parser.add_argument('--test', action='store_true',
                            help='use test YAML, sync, and files')
    return parser


def update_parser_sync(parser, environment):
    """Adds arguments to the backup and restore parsers"""
    parser = update_parser_all(parser, environment)
    parser.add_argument('FILES', nargs='*',
                        help='files to interact on as specified in YAML, '
                        + 'defaults to all files for device')
    parser.add_argument('-d', '--device', default=get_hostname(),
                        help='specify device name to use, defaults to '
                        + 'current hostname')
    parser.add_argument('--no-diff', action='store_true',
                        help='suppress diff output')
    parser.add_argument('--dry-run', action='store_true',
                        help='do not modify any files')
    parser.add_argument('--sudo', action='store_true',
                        help='use "sudo" when copying/creating files')
    return parser


def update_parser_sync_restore(parser, environment):
    """Adds arguments to the restore parser"""
    parser = update_parser_sync(parser, environment)
    parser.add_argument('--staging',
                        help='store files to staging directory instead of '
                        + 'local files')
    return parser


def update_parser_yaml_modify(parser):
    """Adds arguments to the add and remove parsers"""
    parser.add_argument('-d', '--device', default=get_hostname(),
                        help='specify device name to use, defaults to current '
                        + 'hostname')
    parser.add_argument('--no-diff', action='store_true')
    parser.add_argument('--dry-run', action='store_true',
                        help='do not modify any files')

    return parser


# YAML

def prep_yaml():
    """Find filetailor.ini, read it, then load YAML"""

    if 'test' in ARGS and ARGS.test:
        # Use test locations
        logging.debug('Using test config')
        paths = {'sync_dir': './tests/sync', 'yaml_dir': './tests/yaml'}
    else:
        # Load YAML
        logging.debug('Using production config')
        filetailor_ini_path = load_ini_files.find_filetailor_ini()
        if not os.path.isfile(filetailor_ini_path):
            print('ERROR: "filetailor.ini" not found at '
                  + f'"{filetailor_ini_path}".')
            print('Fix the path or run "filetailor init" to generate a new '
                  + 'INI file.')
            sys.exit()
        filetailor_ini = load_ini_files.read_filetailor_ini(
            filetailor_ini_path)
        paths = filetailor_ini['PATHS']

        # Check folders exist
        for key in paths:

            if key not in ['sync_dir', 'yaml_dir', 'in-progress_dir']:
                continue

            # Convert to Path type
            os_path = Path(paths[key])

            # Check if folder exists
            if not os.path.isdir(os_path):
                print(f'ERROR: "{os_path}" does not exist ({key}). '
                      + 'Run "filetailor init" to create.')
                sys.exit()

        # Load YAML
        logging.debug('Loading YAML')
        (yaml_default, yaml_devices,
            yaml_files) = filetailor.helpers.load_yaml.main(paths)
        ftconfig.yaml_default = yaml_default
        ftconfig.yaml_devices = yaml_devices
        ftconfig.yaml_files = yaml_files

    ftconfig.paths = paths
    ftconfig.tools = filetailor_ini['TOOLS']
    if 'device' in ARGS:
        ftconfig.device_id = get_device_id(yaml_devices, ARGS.device)


# CORE FUNCTIONS

def call_init():
    """Create filetailor.ini or create sync_dir and yaml_dir"""
    filetailor.core.initialize.main()


def call_sync_status():
    """Display status of local files in comparison to the sync folder"""
    logging.debug('Calling sync:status')
    ftconfig.sync = 'status'
    prep_yaml()
    filetailor.core.sync.status()


def call_sync_backup():
    """Copy files from local machine to sync_dir"""
    logging.debug('Calling sync:backup')
    ftconfig.sync = 'backup'
    prep_yaml()
    filetailor.core.sync.backup()


def call_sync_restore():
    """Copy files from sync_dir to local machine"""
    logging.debug('Calling sync:restore')
    ftconfig.sync = 'restore'
    prep_yaml()
    filetailor.core.sync.restore()


def call_yaml_add():
    """Add file location to YAML for backup/restore"""
    prep_yaml()
    filetailor.core.update_yaml.main('add')


def call_yaml_remove():
    """Remove file location from YAML for backup/restore"""
    prep_yaml()
    filetailor.core.update_yaml.main('remove')


def call_clean():
    """Remove files from sync_dir that are no longer defined in YAML"""
    prep_yaml()
    filetailor.core.clean.main()


def call_uninstall():
    """Delete filetailor directories"""
    filetailor.core.uninstall.main()


def call_paths():
    """Show filetailor paths"""
    prep_yaml()
    filetailor.core.paths.main()


def main():
    """Create argparse parsers, update variables, and call the core function as
    defined by the user arguments
    """

    # Get path to data folder
    ftconfig.data = os.path.join(os.path.dirname(__file__), 'data')

    # Load config.ini
    config_ini = load_ini_files.load_config_ini()
    override_filetailor_ini_path = config_ini['DEFAULT'].get(
        'override_filetailor_ini_path', '')
    ftconfig.override_filetailor_ini_path = override_filetailor_ini_path

    # Generate main parser
    parser = argparse.ArgumentParser(
        description=('Peer-based configuration management utility with a high'
                     ' level of file content control.'))
    parser = update_parser_all(parser, config_ini)
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__}')
    subparsers = parser.add_subparsers(
        help='commands executing various aspects of filetailor')

    # Generate subparsers

    # Parser: init
    parser_init = subparsers.add_parser(
        'init',
        help='initialize new folders for sync')
    parser_init = update_parser_all(parser_init, config_ini)
    parser_init.set_defaults(func=call_init)

    # Parser: status
    parser_sync_status = subparsers.add_parser(
        'status',
        help='display status of local files in comparison to the sync folder')
    parser_sync_status = update_parser_sync(parser_sync_status, config_ini)
    parser_sync_status.set_defaults(func=call_sync_status)

    # Parser: backup
    parser_sync_backup = subparsers.add_parser(
        'backup',
        help='copy files from local device to sync folder')
    parser_sync_backup = update_parser_sync(parser_sync_backup, config_ini)
    parser_sync_backup.set_defaults(func=call_sync_backup)

    # Parser: restore
    parser_sync_restore = subparsers.add_parser(
        'restore',
        help='copy files from sync folder to local device')
    parser_sync_restore.add_argument('--no-bak', action='store_true')
    parser_sync_restore = update_parser_sync_restore(parser_sync_restore, config_ini)
    parser_sync_restore.set_defaults(func=call_sync_restore)

    # Parser: yaml:add
    parser_yaml_add = subparsers.add_parser(
        'add',
        help='add files to YAML')
    parser_yaml_add = update_parser_all(parser_yaml_add, config_ini)
    parser_yaml_add.add_argument(
        'PATHS', nargs='*', type=Path,
        help='file path(s) on system to add to YAML')
    parser_yaml_add.add_argument(
        '-n', '--name', action='append', help='name to save within YAML')
    parser_yaml_add = update_parser_yaml_modify(parser_yaml_add)
    parser_yaml_add.set_defaults(func=call_yaml_add)

    # Parser: yaml:remove
    parser_yaml_remove = subparsers.add_parser(
        'remove',
        help='remove files from YAML')
    parser_yaml_remove = update_parser_all(parser_yaml_remove, config_ini)
    parser_yaml_remove.add_argument(
        'FILES', nargs='*', help='file(s) to remove from YAML')
    parser_yaml_remove = update_parser_yaml_modify(parser_yaml_remove)
    parser_yaml_remove.set_defaults(func=call_yaml_remove)

    # Parser: clean
    parser_clean = subparsers.add_parser(
        'clean',
        help='permanently delete files not in YAML from sync folder')
    parser_clean = update_parser_all(parser_clean, config_ini)
    parser_clean.add_argument('--dry-run', action='store_true',
                             help='do not modify any files')
    parser_clean.set_defaults(func=call_clean)

    # Parser: uninstall
    parser_uninstall = subparsers.add_parser(
        'uninstall',
        help='delete filetailor directories')
    parser_uninstall = update_parser_all(parser_uninstall, config_ini)
    parser_uninstall.add_argument('--dry-run', action='store_true',
                             help='do not modify any files')
    parser_uninstall.set_defaults(func=call_uninstall)

    # Parser: paths
    parser_paths = subparsers.add_parser(
        'paths',
        help='show paths to configuration files')
    parser_paths.set_defaults(func=call_paths)

    # Get ARGS then call function
    global ARGS
    ARGS = parser.parse_args()
    ftconfig.args = ARGS
    if 'debug' in ARGS and ARGS.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.info('ARGS = %s', ARGS)

    if 'func' in ARGS:
        # Call core function
        ARGS.func()
    else:
        # Call help if no argument provided
        parser.print_help()


# https://docs.python.org/3/library/__main__.html
if __name__ == '__main__':
    main()
