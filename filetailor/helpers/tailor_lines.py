#!/usr/bin/env python3
"""Tailor a line of text by adding and removing comment for a
specific device based on the YAML
"""

import logging
import re
import sys

import filetailor.config as ftconfig
from filetailor.helpers import cprint
from filetailor.helpers.get_key_list import main as get_key_list


class LineAttributes:

    # Example: dummy_text //{filetailor host1 host2} additional text
    # Regex accounts for `{begin filetailor`, `{end filetailor`, and just
    # `{filetailor`
    global P1
    P1 = re.compile(r'(\S*)\{(begin |end |)filetailor (.*?)\}')

    def __init__(self, line, number, key_list={}):
        self.line = line
        self.number = number
        self.indent = self.get_indent()
        self.comment_char = None
        self.action = None
        self.devices = None
        self.get_action(key_list)

    def get_action(self, key_list):
        m1 = P1.search(self.line)
        if m1:

            # From `{filetailor`, `comment_sym` is equal to all preceding
            # characters until the first whitespace.
            # `devices` is all following characters until the first `}`
            # From example, `comment_char` = `//`
            self.comment_char = m1.group(1)

            # From example, `action` = `''`
            self.action = m1.group(2)

            # From example, `devices` = `device1 device2`
            devices = m1.group(3).split()

            # Converted device(s) have had vars replaced with values
            converted_devices = []

            for device in devices:
                converted_device = device
                for key in key_list:
                    # Replace vars in `line` with keys for backup; reverse for restore
                    var = key_list[key]
                    converted_device = converted_device.replace(key, var)
                converted_devices = converted_devices + converted_device.split()
            self.devices = converted_devices

    def update(self, source_text):
        """Update line and indent with new `self.number`"""
        self.line = source_text[self.number]
        self.indent = self.get_indent(self.line)

    def get_indent(self):
        """Get number of whitespaces at beginning of line"""

        if len(self.line) == len(self.line.lstrip()):
            # No indentation
            indent = 0
        else:
            # Some indentation
            indent = len(self.line) - len(self.line.lstrip())

        return indent


def update_comments(line, comment_char, indent):
    """Add or remove comments to tailor the line to the device

    Called by `update_line`
    """

    if ftconfig.sync in ['backup']:
        # If backup, comment out lines

        if len(line) > 1:
            # If line contains text, add comment_char and space in place of
            # empty line text
            line = ' '*indent + comment_char + ' ' + line[indent:]
        else:
            # If line is blank, add comment_char only
            # This is likely due to a multi-line tailor
            line = ' '*indent + comment_char + '\n'

    if ftconfig.sync in ['status', 'restore']:
        # If restore, uncomment lines
        # Remove space trailing the comment if it exists

        # Check if line is more than just a comment and whitespace
        if len(line.strip()) > 1:  # `.strip` removes newline character
            # Line contains text, so replace comment and following space
            line = line.replace(comment_char + ' ', '', 1)
        else:
            # Blank line aside from comment, so replace comment
            line = line.replace(comment_char, '', 1)

    return line


def main(xfile):
    """Tailor the line to fit the sync directory (backup) or device (restore)

    Called by `tailor_file`
    """

    with open(xfile.source) as source_file:
        try:
            source_text = source_file.readlines()
        except (UnboundLocalError, UnicodeDecodeError):
            logging.debug('Ignoring binary file {xfile.file_id}')
            return False


    source_tailored = []
    multiline = []  # List of comment symbols in active multiline

    # Update vars
    key_list = get_key_list(xfile.yaml_default,
                            xfile.yaml_device,
                            xfile.yaml_file,
                            'file')

    for (current_line_number, line) in enumerate(source_text):
        # For each line in file

        for key in key_list:
            # Replace vars in `line` with keys for backup; reverse for restore
            var = key_list[key]
            if ftconfig.sync in ['backup']:
                line = line.replace(var, key)
            if ftconfig.sync in ['status', 'restore']:
                line = line.replace(key, var)

        # Update filetailor tags
        cline = LineAttributes(line, current_line_number, key_list=key_list)
        if cline.action is not None and xfile.device_id in cline.devices:
            if cline.action == '':
                # Single-line edit
                line = update_comments(line, cline.comment_char, cline.indent)
            elif cline.action in ['begin ', 'end ']:
                if cline.action == 'begin ':
                    # Check for multi-line start
                    multiline.append(cline.comment_char)
                    multiline_begin = LineAttributes(line, current_line_number)
                elif cline.action == 'end ':
                    # Check for multi-line stop
                    del multiline[-1]
        elif len(multiline) > 0:
            # Update multi-line edits
            cline.comment_char = multiline[-1]
            line = update_comments(line, cline.comment_char, multiline_begin.indent)

        source_tailored.append(line)

    if len(multiline) > 0:
        # Multi-line error
        cprint.error(f'ERROR: In "{xfile.file_id}", multi-line control begun '
                     + 'but not ended.', xfile)
        input('Press return to continue.')

    return source_tailored
