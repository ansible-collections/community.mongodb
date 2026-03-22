from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import unittest
import sys
import os
path = os.path.dirname(os.path.realpath(__file__))
path = "{0}/../../plugins/modules".format(path)
sys.path.append(path)
import mongodb_user


class TestMongoDBUserMethods(unittest.TestCase):

    def test_check_if_roles_changed_single_db(self):
        uinfo = {
            'roles': [
                {'db': 'foo', 'role': 'foo'},
                {'db': 'foo', 'role': 'bar'},
                {'db': 'foo', 'role': 'baz'},
            ]
        }
        roles_ordered = [
            'foo',
            'bar',
            'baz',
        ]
        roles_disordered = [
            'baz',
            'bar',
            'foo',
        ]

        self.assertFalse(mongodb_user.check_if_roles_changed(uinfo, roles_ordered, 'foo'))
        self.assertFalse(mongodb_user.check_if_roles_changed(uinfo, roles_disordered, 'foo'))

    def test_check_if_roles_changed_multiple_db(self):
        uinfo = {
            'roles': [
                {'db': 'foo', 'role': 'foo'},
                {'db': 'foo', 'role': 'bar'},
                {'db': 'bar', 'role': 'baz'},
            ]
        }
        roles_ordered = [
            {'db': 'foo', 'role': 'foo'},
            {'db': 'foo', 'role': 'bar'},
            {'db': 'bar', 'role': 'baz'},
        ]
        roles_disordered = [
            {'db': 'bar', 'role': 'baz'},
            {'db': 'foo', 'role': 'bar'},
            {'db': 'foo', 'role': 'foo'},
        ]

        self.assertFalse(mongodb_user.check_if_roles_changed(uinfo, roles_ordered, ''))
        self.assertFalse(mongodb_user.check_if_roles_changed(uinfo, roles_disordered, ''))

    def test_check_if_authentication_restrictions_changed_same_values(self):
        uinfo = {
            'authenticationRestrictions': [
                [{'clientSource': ['127.0.0.1', '::1'], 'serverAddress': []}],
                [{'clientSource': ['10.0.0.0/8'], 'serverAddress': ['192.168.1.10']}],
            ]
        }
        restrictions = [
            {'clientSource': ['10.0.0.0/8'], 'serverAddress': ['192.168.1.10']},
            {'clientSource': ['::1', '127.0.0.1'], 'serverAddress': []},
        ]

        self.assertFalse(
            mongodb_user.check_if_authentication_restrictions_changed(uinfo, restrictions)
        )

    def test_check_if_authentication_restrictions_changed_detects_difference(self):
        uinfo = {
            'authenticationRestrictions': [
                {'clientSource': ['127.0.0.1'], 'serverAddress': []},
            ]
        }
        restrictions = [
            {'clientSource': ['127.0.0.1'], 'serverAddress': ['10.0.0.0/8']},
        ]

        self.assertTrue(
            mongodb_user.check_if_authentication_restrictions_changed(uinfo, restrictions)
        )


if __name__ == '__main__':
    unittest.main()
