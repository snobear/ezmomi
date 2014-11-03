#!/usr/bin/env python
__author__ = ','.join((
    'Maxim Kovgan <maxk@fortscale.com>',
))
# File Name: ezmomi_test
#    Created on: 02/11/14 at 12:49
#    Copyright by Fortscale Security ltd. 2014

import ezmomi

import os
import sys
import copy
# import pytest
import tempfile
import unittest
import hashlib


def always_nay(path):
    return False


def new_exit(val):
    raise ValueError(val)


def checksum_file(path, blocksize=65536):
    if not os.path.exists(path):
        return None

    checksum = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(blocksize), ""):
            checksum.update(block)
    return checksum.hexdigest()


class TestEZMomi(unittest.TestCase):

    def setUp(self):
        self._old_isfile = os.path.isfile
        self._old_exit = sys.exit
        self.old_env = copy.deepcopy(os.environ)

    def tearDown(self):
        os.path.isfile = self._old_isfile
        sys.exit = self._old_exit
        os.environ = copy.deepcopy(self.old_env)

    def test_find_config_name(self):
        cfg_dir = os.path.join(os.path.expanduser("~"), ".config/ezmomi")
        expected = os.path.join(cfg_dir, "config.yml")
        actual = ezmomi.EZMomi().find_config_name()
        self.assertEqual(expected, actual)

        expected = '/tmp/config.yml'
        k = 'EZMOMI_CONFIG'
        os.environ.update({k: expected})
        actual = ezmomi.EZMomi().find_config_name()
        self.assertEqual(expected, actual)

    def test_gen_default_example_config_name(self):
        # copy example config
        expected = os.path.join(
            os.path.dirname(os.path.abspath(ezmomi.__file__)),
            "config/config.yml.example"
        )
        actual = ezmomi.EZMomi().gen_default_example_config_name()
        self.assertEqual(expected, actual)

    def test_gen_cfg_example(self):
        new_dir = '/tmp/.config/'
        new_file = os.path.join(tempfile.mktemp(prefix=new_dir, suffix='.yml'))
        ezmomi.sys.exit = new_exit
        ezmomi.EZMomi().gen_cfg_example(new_file)

        example_default = ezmomi.EZMomi().gen_default_example_config_name()
        expected = checksum_file(example_default)
        actual = checksum_file(new_file + '.example')
        self.assertEqual(expected, actual)
        os.system('rm -fr {new_dir}'.format(**locals()))

#    def test_ezmomi(self):
#        myezmomi = ezmomi.EZMomi()
#        unexpected = None
#        actual = myezmomi.config
#        self.assertNotEqual(unexpected, actual)
#        os.path.isfile = self._old_isfile
#        sys.exit = self._old_exit
#        os.environ = copy.deepcopy(self.old_env)
#        myezmomi.clone_as_template()


def main():
    return unittest.main()


if __name__ == '__main__':
    sys.exit(main())
