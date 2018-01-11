#!/usr/bin/python

import unittest
from ermresolve.config import get_service_config, ResolverConfig, ResolverTarget
import json

_config1 = None

class TestConfig1 (unittest.TestCase):
    def test_0(self):
        global _config1
        _config1 = get_service_config('./data/config1.json')
        self.assertIsInstance(_config1, ResolverConfig)

    def test_targets_list(self):
        self.assertIsInstance(_config1.targets, list)
        for target in _config1.targets:
            self.assertIsInstance(target, ResolverTarget)

    def test_targets_count(self):
        self.assertEqual(len(_config1.targets), 22)

    def test_no_sugar_simple(self):
        self.assertTupleEqual(
            _config1.targets[0].astuple()[1:],
            ("http://localhost", 1, "S1", "T1", "c1")
        )

    def test_no_sugar_embedded(self):
        self.assertTupleEqual(
            _config1.targets[11].astuple()[1:],
            ("http://localhost", 7, "S7", "T7", "c7")
        )

    def test_match_unversioned(self):
        parts = _config1.targets[0].match_parts('1-2RW0')
        self.assertEqual(parts, {"server_url": "http://localhost", "catalog": '1', "schema": "S1", "table": "T1", "column": "c1", "key": '1-2RW0'})
        self.assertEqual(
            _config1.targets[0].ermrest_url_template % parts,
            'http://localhost/ermrest/catalog/1/entity/S1:T1/c1=1-2RW0'
        )
        self.assertEqual(
            _config1.targets[0].chaise_url_template % parts,
            'http://localhost/chaise/record/#1/S1:T1/c1=1-2RW0'
        )

    def test_match_versioned(self):
        parts = _config1.targets[0].match_parts('1-2RW0@123')
        self.assertEqual(parts, {"server_url": "http://localhost", "catalog": '1@123', "schema": "S1", "table": "T1", "column": "c1", "key": '1-2RW0'})
        self.assertEqual(
            _config1.targets[0].ermrest_url_template % parts,
            'http://localhost/ermrest/catalog/1@123/entity/S1:T1/c1=1-2RW0'
        )
        self.assertEqual(
            _config1.targets[0].chaise_url_template % parts,
            'http://localhost/chaise/record/#1@123/S1:T1/c1=1-2RW0'
        )

    def test_nonmatch_unversioned(self):
        parts = _config1.targets[0].match_parts('1-2RW0_')
        self.assertIsNone(parts)
        
    def test_nonmatch_versioned(self):
        parts = _config1.targets[0].match_parts('1-2RW0@123_')
        self.assertIsNone(parts)
        
class TestConfig2 (unittest.TestCase):
    # Config2 is a flattened version of Config1...
    
    def test_0(self):
        global _config2
        _config2 = get_service_config('./data/config2.json')
        self.assertIsInstance(_config2, ResolverConfig)

    def test_equivalence(self):
        self.assertEqual(
            [ target.astuple() for target in _config1.targets ],
            [ target.astuple() for target in _config2.targets ]
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)
