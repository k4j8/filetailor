#!/usr/bin/env python3
"""Asks user how to proceed"""

import filetailor.helpers.get_option
from filetailor.helpers import cprint
from filetailor.helpers.diff import difftool


def get_response(msg, default, obj1=None, obj2=None):
    """Get user response"""

    # Check if `--assumeyes` is applied in default, device, file, or arg
    # settings
    if filetailor.helpers.get_option.main('assumeyes', obj1, obj2):
        return 'a'

    # Determine the options
    valid_input = ['a', 'y', 'n']
    if default == 'a':
        flags = '[A]ll, [Y]es, [N]o'
    elif default == 'y':
        flags = '[Y/n]'
    elif default == 'n':
        flags = '[y/N]'
    elif default == 'd':
        flags = '[Y]es, [N]o, show [D]ifftool'
        valid_input.append('d')

    result = None
    while result is None:
        # Get input from user
        user_input = input(f'{msg} {flags} ')

        if user_input == '':
            # Apply defaults
            result = default
        else:
            # Get first letter of input as lowercase only
            user_input = user_input[0].lower()

            # Determine result
            if user_input in valid_input:
                result = user_input
            else:
                cprint.error('Invalid input, try again.', obj1, obj2)

    return result


def main(msg, default, obj1=None, obj2=None, src=None, dst=None):
    """Convert response to True/False"""

    result = get_response(msg, default, obj1, obj2)

    if result == 'd':
        result = 'n'
        difftool(src, dst)

    return result != 'n'
