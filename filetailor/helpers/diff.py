#!/usr/bin/env python3
"""Determines diff program then runs diff on two files"""

import difflib
import logging
import subprocess

import filetailor.config as ftconfig


def get_git_program(cmd):
    """Determine diff program based on Git settings"""

    output = subprocess.run(['git', 'config', cmd],
                            stdout=subprocess.PIPE, check=False)
    if output.stdout:
        diff_program = output.stdout.decode('utf-8')
    else:
        diff_program = False
    return diff_program


def get_diff_program(src, dst, ftconfig_name, gitconfig_name):
    """Run diff on two files"""

    logging.debug('Getting diff program')

    # Get diff program from ftconfig
    diff_program = ftconfig.tools.get('diff_pager', 'none')
    if diff_program.lower() == 'none':
        # Ignore the default placeholder text of "None"
        diff_program = None

    # Get diff program from Git config
    if not diff_program:
        diff_program = get_git_program(gitconfig_name)
        if diff_program:
            diff_program = diff_program.strip()
            logging.debug('Selected %s as diff program', diff_program)

    # Get diff program by using default
    if not diff_program:
        logging.debug('Using "diff" as diff program')
        with open(src) as src_file:
            src_text = src_file.readlines()
        with open(dst) as dst_file:
            dst_text = dst_file.readlines()
        for line in difflib.unified_diff(src_text, dst_text,
                                         fromfile=str(src), tofile=str(dst)):
            print(line, end='')
    else:
        logging.debug('Using "%s" as diff program', diff_program)
        subprocess.run([diff_program, src, dst], check=False)


def diff(src, dst):
    """Run diff in terminal"""
    get_diff_program(src, dst, 'diff_program', 'core.pager')


def difftool(src, dst):
    """Run diff in external tool"""
    get_diff_program(src, dst, 'difftool', 'diff.tool')
