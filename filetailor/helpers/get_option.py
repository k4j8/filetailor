#!/usr/bin/env python3
"""Gets active option based on CLI and YAML"""

import filetailor.config as ftconfig


def main(option, obj1=None, obj2=None):
    """Gets active option based on CLI and YAML"""

    yaml_default = ftconfig.yaml_default
    args = ftconfig.args

    # Use option in file, device, CLI args, then default
    result = None
    for obj in [obj1, obj2]:
        # Check obj1 then, if not found, obj2
        if obj is None:
            continue
        if (obj.type in ['file', 'subfile']
                and obj.yaml_file
                and option in obj.yaml_file):
            result = obj.yaml_file[option]
            break
        if (obj.type in ['device']
                and obj.yaml_device is not None
                and option in obj.yaml_device):
            result = obj.yaml_device[option]
            break

    if result is None:
        # If not in obj2 or obj1, check CLI args then default
        if option in vars(args):
            result = vars(args)[option]
        elif (yaml_default is not None) and (option in yaml_default):
            result = yaml_default[option]
        else:
            result = False

    return result
