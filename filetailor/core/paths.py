#!/usr/bin/env python3
"""Shows configuration paths for filetailor"""

import filetailor.config as ftconfig

def main():
    """Print paths"""

    print(f'config.ini: {ftconfig.config_ini_path}')
    print(f'filetailor.ini: {ftconfig.filetailor_ini_path}')
    print()
    for path in ftconfig.paths:
        print(f'{path}: {ftconfig.paths[path]}')
