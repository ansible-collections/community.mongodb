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

    def test_user_add_omits_empty_authentication_restrictions_on_create(self):
        class FakeDB:
            def __init__(self):
                self.calls = []

            def command(self, command_name, user, **kwargs):
                self.calls.append((command_name, user, kwargs))

        class FakeClient(dict):
            pass

        db = FakeDB()
        client = FakeClient({'admin': db})
        original_user_find = mongodb_user.user_find

        try:
            mongodb_user.user_find = lambda client, user, db_name: False
            mongodb_user.user_add(None, client, 'admin', 'alice', 'secret', ['root'], [])
        finally:
            mongodb_user.user_find = original_user_find

        self.assertEqual(1, len(db.calls))
        command_name, user, kwargs = db.calls[0]
        self.assertEqual('createUser', command_name)
        self.assertEqual('alice', user)
        self.assertNotIn('authenticationRestrictions', kwargs)

    def test_user_add_keeps_empty_authentication_restrictions_on_update(self):
        class FakeDB:
            def __init__(self):
                self.calls = []

            def command(self, command_name, user, **kwargs):
                self.calls.append((command_name, user, kwargs))

        class FakeClient(dict):
            pass

        db = FakeDB()
        client = FakeClient({'admin': db})
        original_user_find = mongodb_user.user_find

        try:
            mongodb_user.user_find = lambda client, user, db_name: {'user': user}
            mongodb_user.user_add(None, client, 'admin', 'alice', None, ['root'], [])
        finally:
            mongodb_user.user_find = original_user_find

        self.assertEqual(1, len(db.calls))
        command_name, user, kwargs = db.calls[0]
        self.assertEqual('updateUser', command_name)
        self.assertEqual('alice', user)
        self.assertEqual([], kwargs['authenticationRestrictions'])

    def test_user_find_uses_exact_match_users_info_query(self):
        class FakeDB:
            def __init__(self):
                self.calls = []

            def command(self, payload):
                self.calls.append(payload)
                return {
                    'users': [
                        {'user': 'alice', 'db': 'admin', 'roles': []},
                    ]
                }

        class FakeClient(dict):
            pass

        db = FakeDB()
        client = FakeClient({'admin': db})

        result = mongodb_user.user_find(client, 'alice', 'admin')

        self.assertEqual('alice', result['user'])
        self.assertEqual(
            {
                'usersInfo': {'user': 'alice', 'db': 'admin'},
                'showAuthenticationRestrictions': True,
            },
            db.calls[0],
        )


if __name__ == '__main__':
    unittest.main()
