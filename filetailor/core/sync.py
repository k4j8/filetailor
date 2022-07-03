#!/usr/bin/env python3
"""Copy files between local machine and sync_dir"""

# pylint: disable=no-member

import copy
import filecmp
import logging
import os
import re
import shutil
import stat
import sys
from pathlib import Path

import filetailor.config as ftconfig
import filetailor.helpers.get_key_list
import filetailor.helpers.okay_to_continue as okay
import filetailor.helpers.tailor_lines
from filetailor.helpers import cprint
from filetailor.helpers.diff import main as diff
from filetailor.helpers.get_option import main as get_option

STATUS = 'status'
BACKUP = 'backup'
RESTORE = 'restore'
SAME = 'same'
DIFFERENT = 'different'
MISSING_SOURCE = 'missing source'
MISSING_TARGET = 'missing target'
MISSING_BOTH = 'missing both'
SKIP = 'skip'
UPDATE = 'Update'
ADD_NEW = 'Add new'
DELETE = 'Delete'


class CDevice():
    """Current device"""
    type = 'device'

    def __init__(self, device_id, yaml_devices):
        self.device_id = device_id
        self.yaml_default = YAML_DEFAULT
        self.yaml_device = self.tailor_yaml(
                YAML_DEFAULT, yaml_devices[device_id])

    def replace_dict_values(self, d, find, replace):
        # pylint: disable=invalid-name
        """Replace dictionary values (not keys) recursively"""
        if d:
            for key in d.keys():
                if isinstance(d[key], dict):
                    d[key] = self.replace_dict_values(d[key], find, replace)
                elif isinstance(d[key], str):
                    d[key] = d[key].replace(find, replace)

        return d

    def tailor_yaml(self, yaml_device, yaml_file=None):
        """Replace vars in yaml"""
        key_list = filetailor.helpers.get_key_list.main(
                YAML_DEFAULT, yaml_device, yaml_file, 'yaml')

        # pylint: disable=consider-using-dict-items
        for key in key_list:
            var = key_list[key]
            if yaml_file:
                # Replace vars in `yaml_file` from `yaml_device` and
                # `YAML_DEFAULT`
                self.replace_dict_values(yaml_file, key, var)
            else:
                # Replace vars in `yaml_device` from `YAML_DEFAULT`
                self.replace_dict_values(yaml_device, key, var)

        if yaml_file:
            return yaml_file
        return yaml_device


class CFile(CDevice):
    """Current file"""
    type = 'file'

    def __init__(self, file_id, cdevice):
        # super().__init__(device_id, yaml_device)
        self.device = cdevice
        self.device_id = cdevice.device_id
        self.yaml_default = YAML_DEFAULT
        self.yaml_device = cdevice.yaml_device
        self.yaml_file = self.tailor_yaml(
            cdevice.yaml_device, yaml_files[file_id])
        self.file_id = self.get_file_id(file_id, cdevice)
        self.local = None
        self.sync = None
        self.dircmp_report = None
        self.source = None
        self.target = None
        self.target_parent = None
        self.in_progress = None
        self.stats = None

        self.new = None
        self.delete = None
        self.changed = []

    def get_file_id(self, file_id, cdevice):
        """Prefix `file_id` with device name if `unique = True`"""
        if self.yaml_file and 'unique' in self.yaml_file:
            if self.yaml_file['unique']:
                return f'{file_id}_{cdevice.device_id}'
        return file_id

    def set_paths(self, source, target, parent=None):
        """Set paths and associated attributes"""
        self.source = source
        self.target = target
        self.target_parent = self.target.parent.absolute()

        if parent:
            self.in_progress = Path(os.path.join(
                ftconfig.paths['in-progress_dir'], parent, self.file_id))
        else:
            self.in_progress = Path(os.path.join(
                ftconfig.paths['in-progress_dir'], self.file_id))

    def clean_in_progress_file(self):
        """Remove in_progress_file"""
        if not get_option('dry_run', self, self.device):
            if self.in_progress.is_file():
                os.remove(self.in_progress)
            elif self.in_progress.is_dir():
                shutil.rmtree(self.in_progress)


class SubFile(CFile):
    """Subfile of a directory (class CFile)"""
    type = 'subfile'
    def __init__(self, file_id, cfile):
        self.device = cfile.device
        self.device_id = cfile.device_id
        self.yaml_default = YAML_DEFAULT
        self.file_id = file_id
        self.yaml_device = cfile.yaml_device
        self.yaml_file = cfile.yaml_file
        CFile.set_paths(self,
                        Path(os.path.join(cfile.source, file_id)),
                        Path(os.path.join(cfile.target, file_id)),
                        cfile.file_id)


def check_for_sudo(xfile, device):
    """Check if filetailor should use sudo

    Called by `copy_file`, `create_dir`, and `backup_or_restore`
    """
    if ftconfig.sync == RESTORE and get_option('sudo', xfile, device):
        use_sudo = True
    else:
        use_sudo = False

    return use_sudo


def copy_file_with_sudo(in_progress, target, delete):
    """Copy file with permissions and sudo

    Called by `copy_file` (for files and dirs)
    """

    if delete:
        shutil.os.system(f'sudo rm "{target}"')
    else:
        shutil.os.system(f'sudo cp "{in_progress}" "{target}"')
        # subprocess.run(f'cp --preserve --recursive {source} {target}')

    return True


def copy_file(in_progress, target, xfile, delete):
    """Copy file with permissions

    Called by `copy_files` (for files and dirs)
    """

    copied = False
    if check_for_sudo(xfile, xfile.device):
        copy_file_with_sudo(in_progress, target, delete)
    else:
        try:
            if delete:
                os.remove(target)
            else:
                shutil.copy2(in_progress, target)
            if ftconfig.sync == RESTORE:
                # Apply permissions
                os.chown(target, xfile.stats[stat.ST_UID],
                         xfile.stats[stat.ST_GID])
            copied = True
        except PermissionError:
            if okay.main(f'Insufficient permissions to create "{target}". '
                         + 'Try with "sudo"?', 'n'):
                copied = copy_file_with_sudo(in_progress, target, delete)
            else:
                copied = False

    return copied


def create_dir_with_sudo(path):
    """Create the directory with sudo

    Called by `create_dir` (for files and dirs)
    """

    shutil.os.system(f'sudo mkdir --parents "{path}"')
    cprint.success(f'Created "{path}" with sudo.')
    print()

    return True


def create_dir(path, xfile):
    """Create the directory if it does not exist

    Called by `get_file_status` (for staging directories),
    `copy_files` (for files and dirs) and `copy_subfiles` (for dirs)
    """

    if path.is_dir():
        dir_exists = True
    else:
        dir_exists = False
        if okay.main(f'"{path}" does not exist. Create?', 'n'):
            create_dir_continue = True
        else:
            create_dir_continue = False
        if create_dir_continue:
            if check_for_sudo(xfile, xfile.device):
                if not get_option('dry_run', xfile, xfile.device):
                    dir_exists = create_dir_with_sudo(path)
            else:
                try:
                    if not get_option('dry_run', xfile, xfile.device):
                        os.makedirs(path)
                    cprint.success(f'Created "{path}".')
                    print()
                    dir_exists = True
                except PermissionError:
                    if okay.main('Insufficient permissions to create '
                                 + f'"{path}". Try with "sudo"?', 'n'):
                        dir_exists = create_dir_with_sudo(path)
                    else:
                        dir_exists = False

    return dir_exists


def copy_files(xfile, delete=False):
    """Copy file while creating parents and backups

    Called by `backup_or_restore` (for files) and `copy_subfiles` (for dirs)
    """

    # Create parent directory if needed
    if not create_dir(xfile.target_parent, xfile):
        return

    if (ftconfig.sync == RESTORE
            and not get_option('no_bak', xfile, xfile.device)
            and not get_option('dry_run', xfile, xfile.device)):
        # Create backup
        if xfile.target.is_file():
            copy_file(xfile.target, xfile.target.with_suffix('.filetailor_backup'),
                      xfile, False)

    if not args.dry_run:
        if copy_file(xfile.in_progress, xfile.target, xfile, delete):
            if delete:
                cprint.success(f'Deleted "{xfile.target}".')
            else:
                cprint.success(f'Copied "{xfile.source}" to "{xfile.target}".')
            print()


def copy_subfiles(cfile, subfiles_list, verb):
    """Tailor subfiles within a directory

    Called by `backup_or_restore` (for dirs)
    """

    if subfiles_list and len(subfiles_list):
        delete = (verb == DELETE)
        response = okay.get_response(f'\n{verb} files?', 'a')
        if response != 'n':
            if not create_dir(cfile.target, cfile):
                return
            for file_id in subfiles_list:
                subfile = SubFile(file_id, cfile)
                subfile.stats = cfile.stats
                if verb == UPDATE:
                    diff(subfile.target, subfile.in_progress)
                if response == 'a':
                    # Copy/delete each file without asking
                    if not get_option('dry_run', cfile, cfile.device):
                        copy_files(subfile, delete)
                elif okay.main(f'\n{verb} "{file_id}"?', 'n'):
                    # Asked to copy/delete file, answer was yes
                    if not get_option('dry_run', cfile, cfile.device):
                        copy_files(subfile, delete)
                subfile.clean_in_progress_file()


def tailor_file(xfile):
    """Backup or restore a single file; return True if files differ

    Called by `get_file_status` (for files) and `diff_dir` (for dirs)
    """

    logging.debug('xfile.source = %s', xfile.source)
    logging.debug('target = %s', xfile.target)

    # Convert all variables in source_text
    source_tailored = filetailor.helpers.tailor_lines.main(xfile)
    logging.debug('source_tailored = %s', source_tailored)

    # Write source_tailored to a file (in_progress_file)
    with open(xfile.in_progress, 'w', encoding='UTF-8') as in_progress_file:
        in_progress_file.writelines(source_tailored)

    # Compare files
    if (xfile.target.is_file()
            and filecmp.cmp(xfile.in_progress, xfile.target, shallow=False)):
        # Files are identical
        logging.debug('Skipping %s, identical', xfile.source)
        files_differ = False

    else:
        # Files differ
        logging.debug('Diffing %s', xfile.source)
        files_differ = True

    return files_differ


def filter_subfiles(search_criteria, subfiles, return_matching):
    """Return list of `subfiles` matching `p` if `return_matching` is True
    and return list of subfiles not matching `p` if `return_matching` is False

    Called by `diff_dir` (for dirs)
    """

    matching = []
    for subfile in subfiles:
        matches = search_criteria.search(subfile)
        if ((matches and return_matching)
                or (not matches and not return_matching)):
            # Ignore all files that match the filter
            # and ignore all files not matching the filter
            matching.append(subfile)

    return matching


def diff_dir(cfile):
    """Compare local directory to sync directory and record the sync status of
    each subfile but do not ask the user any questions; return True if files
    differ

    Called by `get_file_status` (for dirs)
    """

    # Ignore subdirectories
    ignores = next(os.walk(cfile.source))[1]
    try:
        if ftconfig.sync in [STATUS, RESTORE]:
            ignores += next(os.walk(cfile.local))[1]
    except StopIteration:
        pass

    # Get subfiles from source and target
    if cfile.target.is_dir():
        subfiles = os.listdir(cfile.source) + os.listdir(cfile.target)
    else:
        subfiles = os.listdir(cfile.source)

    # Ignore `.filetailor_backup` files
    search_criteria = re.compile(r'\.filetailor_backup$')
    ignores += filter_subfiles(search_criteria, subfiles, True)

    # Update ignores based on YAML
    if 'include_contents' in cfile.yaml_file:
        search_criteria = re.compile(cfile.yaml_file['include_contents'])
        ignores += filter_subfiles(search_criteria, subfiles, False)
    if 'exclude_contents' in cfile.yaml_file:
        search_criteria = re.compile(cfile.yaml_file['exclude_contents'])
        ignores += filter_subfiles(search_criteria, subfiles, True)

    # Create cfile in in-progress_dir
    if not cfile.in_progress.is_dir():
        if not get_option('dry_run', cfile, cfile.device):
            os.mkdir(cfile.in_progress)

    # Compare source to target directory
    if cfile.target.is_dir():
        dircmp_report = filecmp.dircmp(cfile.source, cfile.target,
                                       ignore=ignores)
        # Get subfiles changed, new, and delete
        if dircmp_report.diff_files:
            for file_id in dircmp_report.diff_files:
                subfile = SubFile(file_id, cfile)
                if tailor_file(subfile):
                    cfile.changed.append(subfile.file_id)
        cfile.new = dircmp_report.left_only
        cfile.delete = dircmp_report.right_only
    else:
        # Target directory does not exist, all files are new
        cfile.new = set(subfiles) - set(ignores)

    if cfile.new:
        for file_id in cfile.new:
            subfile = SubFile(file_id, cfile)
            tailor_file(subfile)

    # Determine if directories differ
    files_differ = cfile.changed or cfile.new or cfile.delete

    return files_differ


def get_file_status(cfile, cdevice):
    """Tailor file and return if files differ

    Called by `status` and `backup_or_restore`
    """

    # Loop through each file to perform the sync operation
    logging.debug('Beginning %s', cfile.file_id)

    # Check if file is for this device
    if 'include_devices' in cfile.yaml_file:
        if cdevice.device_id not in cfile.yaml_file['include_devices']:
            logging.debug('Skipping %s, host not in included list',
                          cfile.file_id)
            return SKIP
    elif 'exclude_devices' in cfile.yaml_file:
        if cdevice.device_id in cfile.yaml_file['exclude_devices']:
            logging.debug('Skipping %s, host in excluded list',
                          cfile.file_id)
            return SKIP

    run_script(cfile, 'before', ftconfig.sync)

    # Define file locations `sync` and `local`
    cfile.sync = Path(os.path.join(ftconfig.paths['sync_dir'], cfile.file_id))
    staging_dir = get_option('staging', cfile, cfile.device)
    if staging_dir:
        cfile.local = Path(os.path.join(
            Path(staging_dir).resolve(),
            cfile.file_id,
            os.path.basename(cfile.yaml_file['path'])))
    else:
        cfile.local = Path(cfile.yaml_file['path'])

    # Define file location `source` and `target`
    if ftconfig.sync in [BACKUP]:
        source = cfile.local
        target = cfile.sync

    elif ftconfig.sync in [STATUS, RESTORE]:
        source = cfile.sync
        target = cfile.local

    # Check if `source` and `target` are files or directories,
    # also set `in_progress` path
    cfile.set_paths(source, target)

    # Copy owner and group from `local` (same as `target`)
    if ftconfig.sync in [RESTORE]:

        if not cfile.target.exists() and not cfile.target_parent.is_dir():
            # Target nor its parent exist, so offer to create parent dir
            cprint.plain(f'For "{cfile.file_id}", local file\'s parent folder '
                         + f'"{cfile.target_parent}" does not exist.')
            if not create_dir(cfile.target_parent, cfile):
                return SKIP

        if cfile.target.exists():
            # Target exists
            cfile.stats = os.stat(cfile.local)
            logging.debug('stats[stat.ST_UID] = %s', cfile.stats[stat.ST_UID])
            logging.debug('stats[stat.ST_GID] = %s', cfile.stats[stat.ST_GID])
            logging.debug('stats[stat.st_mode] = %s', cfile.stats[stat.ST_MODE])
        else:
            # Parent of target exists
            cfile.stats = os.stat(cfile.target_parent)
            logging.debug('stats[stat.ST_UID] = %s', cfile.stats[stat.ST_UID])
            logging.debug('stats[stat.ST_GID] = %s', cfile.stats[stat.ST_GID])
            logging.debug('stats[stat.st_mode] = %s', cfile.stats[stat.ST_MODE])

    # Tailor and compare files
    # First check if a file/directory of opposite type will block creating
    # a new file.
    if cfile.source.is_file():
        # For files
        if cfile.target.is_dir():
            cprint.plain(f'Trying to copy file "{cfile.file_id}" to '
                         + f'"{cfile.target}", but a directory (not file) of '
                         + 'the same name already exists. Skipping.')
            return
        files_differ = tailor_file(cfile)
        if cfile.target.is_file():
            if files_differ:
                file_status = DIFFERENT
            else:
                file_status = SAME
        else:
            file_status = MISSING_TARGET
    elif cfile.source.is_dir():
        # For directories
        if cfile.target.is_file():
            cprint.plain(f'Trying to copy directory "{cfile.file_id}" to '
                         + f'"{cfile.target}", but a file (not directory) of '
                         + 'the same name already exists. Skipping.')
            return
        files_differ = diff_dir(cfile)
        if cfile.target.is_dir():
            if files_differ:
                file_status = DIFFERENT
            else:
                file_status = SAME
        else:
            file_status = MISSING_TARGET
    elif cfile.target.exists():
        file_status = MISSING_SOURCE
    else:
        file_status = MISSING_BOTH

    return file_status


def setup():
    """Get current device with YAML and files to sync

    Called by `backup_or_restore`
    """

    logging.debug('Running setup')
    global args
    args = ftconfig.args

    # Get YAML
    global YAML_DEFAULT
    YAML_DEFAULT = copy.deepcopy(ftconfig.yaml_default)
    yaml_devices = copy.deepcopy(ftconfig.yaml_devices)
    global yaml_files
    yaml_files = copy.deepcopy(ftconfig.yaml_files)

    # Get current device
    device_id = ftconfig.device_id

    # Replace vars in device YAML
    if device_id not in yaml_devices:
        cprint.error(f'Device "{device_id}" is not in YAML. Run "filetailor '
                     + 'add" or manually update YAML with device to use '
                     + 'filetailor.')
        sys.exit()
    cdevice = CDevice(device_id, yaml_devices)

    # Get list of files to operate on
    if args.FILES == []:
        # Use all files in YAML if user didn't specify any
        files = yaml_files.keys()
    else:
        # If the user specified files, use those
        files = []
        for file_id in args.FILES:
            if file_id in yaml_files:
                # Check file exists in the YAML
                files.append(file_id)
            else:
                cprint.plain(f'{file_id} not found in YAML.')

    return (cdevice, files)


def run_script(cfile, time, operation):
    """Runs script from YAML

    Called by `backup_or_restore`
    """

    if time == 'before':
        if operation in [STATUS, BACKUP]:
            script_name = 'before_backup'
        elif operation == RESTORE:
            script_name = 'before_restore'
    elif time == 'after':
        if operation in [STATUS, BACKUP]:
            script_name = 'after_backup'
        elif operation == RESTORE:
            script_name = 'after_restore'

    try:
        script_command = cfile.yaml_file['scripts'][script_name]
        cprint.plain(f'For file "{cfile.file_id}", running {script_name} '
                     + f'script "{script_command}"')
        shutil.os.system(script_command)
    except (KeyError, TypeError, UnboundLocalError):
        pass


def backup_or_restore():
    """Copy files from/to local machine and sync_dir

    Called by `status`, `backup`, and `restore`
    """

    (cdevice, files) = setup()
    for file_id in files:

        # Replace vars in file YAML
        cfile = CFile(file_id, cdevice)

        file_status = get_file_status(cfile, cdevice)
        if file_status == SKIP:
            continue

        # If running status, report the status
        if ftconfig.sync == STATUS and file_status == SAME:
            cprint.same(f'No change: {cfile.file_id}')
        elif ftconfig.sync == STATUS and file_status == DIFFERENT:
            cprint.differ(f'Modified: {cfile.file_id}')
        elif ftconfig.sync == STATUS and file_status == MISSING_TARGET:
            cprint.differ(f'Not in local directory: "{cfile.file_id}" does '
                          + f'not exist at "{cfile.target}".')

        # Report issue if missing source
        elif file_status in [MISSING_SOURCE, MISSING_BOTH]:
            if ftconfig.sync in [BACKUP]:
                cprint.differ(f'Not in local directory: "{cfile.file_id}" does '
                              + f'not exist at "{cfile.source}".')
            if ftconfig.sync in [STATUS, RESTORE]:
                cprint.differ(f'Not in sync directory: "{cfile.file_id}" does '
                              + f'not exist at "{cfile.source}".')

        # If running backup/restore and not missing source, update files
        elif file_status in [DIFFERENT, MISSING_TARGET]:

            if cfile.source.is_file():
                # For files
                # Print diff or state target doesn't exist
                if file_status == DIFFERENT:
                    if not get_option('no_diff', cfile, cfile.device):
                        diff(cfile.target, cfile.in_progress)
                elif file_status == MISSING_TARGET:
                    cprint.plain(f'For "{cfile.file_id}", '
                                 + f'"{cfile.target}" does not exist.')
                cprint.plain('')

                # Copy file
                if check_for_sudo(cfile, cfile.device):
                    cprint.plain('Using "sudo"...')
                if okay.main(f'Copy file "{cfile.file_id}"?', 'n'):
                    copy_files(cfile)

            elif cfile.source.is_dir():
                # For directories
                cprint.differ(f'\nDIRECTORY: {cfile.file_id}')
                if cfile.changed:
                    cprint.plain('\nFiles to update:')
                    cprint.plain(cfile.changed)
                if cfile.new:
                    cprint.plain('\nNew files to add:')
                    cprint.plain(cfile.new)
                if cfile.delete:
                    cprint.plain('\nOld files to delete:')
                    cprint.plain(cfile.delete)
                copy_subfiles(cfile, cfile.changed, UPDATE)
                copy_subfiles(cfile, cfile.new, ADD_NEW)
                copy_subfiles(cfile, cfile.delete, DELETE)

        if file_status != SKIP:
            if ftconfig.sync == STATUS:
                cfile.clean_in_progress_file()
            run_script(cfile, 'after', ftconfig.sync)


def status():
    """Show status of files"""
    logging.debug('Running status')
    backup_or_restore()
    cprint.plain('\nStatus check complete!\n')


def backup():
    """Copy files from local machine to sync_dir"""
    logging.debug('Running backup')
    backup_or_restore()
    cprint.plain('\nBackup complete!\n')


def restore():
    """Copy files from sync_dir to local machine"""
    logging.debug('Running restore')
    backup_or_restore()
    cprint.plain('\nRestore complete!\n')
