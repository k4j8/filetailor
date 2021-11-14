#!/usr/bin/env python3

from appdirs import AppDirs

# https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules
args = ''
data = ''
config_ini_path = ''
override_filetailor_ini_path = ''
filetailor_ini_path = ''
paths = {}
tools = {}
yaml_default = ''
yaml_devices = ''
yaml_files = ''
sync = ''
dirs = AppDirs('filetailor', False)
device_id = None
