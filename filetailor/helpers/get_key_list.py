#!/usr/bin/env python3
"""Get the list of keys in both the device and file, or just the device if
there are none in the key
"""


def get_var_phrase(var_type):
    """Converts variable type to corresponding phrase in the YAML"""
    if var_type == 'vars':
        var_phrase = 'vars'
    elif var_type == 'yaml':
        var_phrase = 'yaml_only'
    elif var_type == 'file':
        var_phrase = 'file_only'

    return var_phrase


def is_valid(yaml, var_type):
    """Checks if `var_type` is in `yaml`"""

    valid = False
    if yaml:
        # `yaml` exists
        var_phrase = get_var_phrase(var_type)
        if var_phrase in yaml and yaml[var_phrase]:
            valid = True

    return valid


def get_key_val_dict(yaml_default, yaml_device, yaml_file, var_type):
    """Checks which file keys are in device and default, then returns the
    pairs
    """

    key_list = {}
    if yaml_file['vars']:
        # `vars` is not an empty list
        var_phrase = get_var_phrase(var_type)
        for key in yaml_file['vars']:
            if (is_valid(yaml_device, var_type)
                    and key in yaml_device[var_phrase]):
                key_list.update({key: yaml_device[var_phrase][key]})
            elif (is_valid(yaml_default, var_type)
                    and key in yaml_default[var_phrase]):
                key_list.update({key: yaml_default[var_phrase][key]})

    return key_list


def main(yaml_default, yaml_device, yaml_file, var_type):
    """Get the list of {key: value} corresponding to the device
    and file (if provided)

    Called by `update_line` and `tailor_yaml`
    """

    key_list = {}

    if yaml_file and 'vars' in yaml_file:
        # `vars` in both file and devices, so use common vars
        key_list.update(get_key_val_dict(yaml_default, yaml_device, yaml_file,
                                         'vars'))
        key_list.update(get_key_val_dict(yaml_default, yaml_device, yaml_file,
                                         var_type))
    else:
        # `vars` in device only, so use that list
        if is_valid(yaml_default, 'vars'):
            key_list.update(yaml_default['vars'])
        if is_valid(yaml_device, 'vars'):
            key_list.update(yaml_device['vars'])
        if is_valid(yaml_device, var_type):
            key_list.update(yaml_device[get_var_phrase(var_type)])
        if is_valid(yaml_default, var_type):
            key_list.update(yaml_default[get_var_phrase(var_type)])

    return key_list
