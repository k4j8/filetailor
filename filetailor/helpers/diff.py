#!/usr/bin/env python3
"""Determines diff tool then runs diff on two files"""

import difflib
import logging
import subprocess

import filetailor.config as ftconfig


def get_diff_tool(cmd):
    """Determine diff tool based on Git settings"""

    output = subprocess.run(['git', 'config', cmd],
                            stdout=subprocess.PIPE, check=False)
    if output.stdout:
        diff_tool = output.stdout.decode('utf-8')
    else:
        diff_tool = False
    return diff_tool


def main(src, dst):
    """Run diff on two files"""

    logging.debug('Getting diff tool')
    diff_tool = ftconfig.tools.get('diff_tool', False)
    if diff_tool.lower() == 'none':
        # Ignore the default placeholder text of "None"
        diff_tool = None

    if not diff_tool:
        cmds = ['core.pager']
        for cmd in cmds:
            diff_tool = get_diff_tool(cmd)
            if diff_tool:
                diff_tool = diff_tool.strip()
                logging.debug('Selected %s as diff tool', diff_tool)
                break

    if not diff_tool:
        logging.debug('Using "diff" as diff tool')
        with open(src) as src_file:
            src_text = src_file.readlines()
        with open(dst) as dst_file:
            dst_text = dst_file.readlines()
        for line in difflib.unified_diff(src_text, dst_text,
                                         fromfile=str(src), tofile=str(dst)):
            print(line, end='')
    else:
        logging.debug('Using "%s" as diff tool', diff_tool)
        subprocess.run([diff_tool, src, dst], check=False)
