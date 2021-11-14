#!/usr/bin/env python3
"""Test loading the YAML"""

# pylint: disable=too-few-public-methods

import os
from pathlib import Path
import pytest

import filetailor.config as ftconfig
import filetailor.helpers.load_yaml

ROOT = Path(__file__).parent.parent


@pytest.fixture
def paths():
    """Define paths"""
    test_paths = {'sync_dir': os.path.join(ROOT, 'tests/sync'),
                  'yaml_dir': os.path.join(ROOT, 'tests/yaml'),
                  'in-progress_dir': os.path.join(ROOT, 'tests/in-progress')}
    return test_paths


def test_test_dir(paths):
    """Ensure the files in the test directory exist"""
    assert 'file1.txt' in os.listdir(paths['sync_dir'])


class Args():
    """User arguments"""
    quiet = False


def test_load_yaml(paths):
    """Load the YAML"""
    ftconfig.args = Args()
    (_, yaml_devices, _) = filetailor.helpers.load_yaml.main(paths)
    assert 'device1' in yaml_devices
