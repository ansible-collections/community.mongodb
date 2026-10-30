from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import contextlib
import io
import json
import unittest
import sys
import os
from unittest import mock
from ansible.module_utils.testing import patch_module_args
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

    def test_merge_roles_appends_missing_roles(self):
        uinfo = {
            'roles': [
                {'db': 'foo', 'role': 'read'},
                {'db': 'admin', 'role': 'clusterMonitor'},
            ]
        }
        roles = [
            'read',
            'readWrite',
            {'db': 'bar', 'role': 'read'},
        ]

        self.assertEqual(
            [
                {'db': 'foo', 'role': 'read'},
                {'db': 'admin', 'role': 'clusterMonitor'},
                {'role': 'readWrite', 'db': 'foo'},
                {'db': 'bar', 'role': 'read'},
            ],
            mongodb_user.merge_roles(uinfo, roles, 'foo'),
        )

    def test_merge_roles_keeps_existing_roles_when_nothing_is_new(self):
        uinfo = {
            'roles': [
                {'db': 'foo', 'role': 'read'},
                {'db': 'bar', 'role': 'readWrite'},
            ]
        }
        merged = mongodb_user.merge_roles(uinfo, ['read'], 'foo')

        self.assertEqual(uinfo['roles'], merged)
        self.assertFalse(mongodb_user.check_if_roles_changed(uinfo, merged, 'foo'))

    def test_merge_roles_without_existing_roles(self):
        self.assertEqual(
            [{'role': 'read', 'db': 'foo'}],
            mongodb_user.merge_roles({}, ['read'], 'foo'),
        )

    def _run_main(self, args, existing_user):
        stdout = io.StringIO()
        with patch_module_args(args), \
                mock.patch.object(mongodb_user, 'pymongo_found', True), \
                mock.patch.object(mongodb_user, 'get_mongodb_client', return_value=mock.MagicMock()), \
                mock.patch.object(mongodb_user, 'mongo_auth', side_effect=lambda module, client, **kwargs: client), \
                mock.patch.object(mongodb_user, 'user_find', return_value=existing_user), \
                mock.patch.object(mongodb_user, 'user_add') as user_add, \
                contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit):
                mongodb_user.main()
        return json.loads(stdout.getvalue()), user_add

    def test_main_append_adds_roles_to_existing_user(self):
        existing_user = {
            'user': 'bob',
            'db': 'foo',
            'roles': [{'db': 'foo', 'role': 'read'}],
        }
        result, user_add = self._run_main({
            'database': 'foo',
            'name': 'bob',
            'roles': ['readWrite'],
            'append': True,
            'update_password': 'on_create',
        }, existing_user)

        self.assertTrue(result['changed'])
        user_add.assert_called_once()
        self.assertEqual(
            [{'db': 'foo', 'role': 'read'}, {'role': 'readWrite', 'db': 'foo'}],
            user_add.call_args[0][5],
        )

    def test_main_append_is_idempotent_when_user_has_roles(self):
        existing_user = {
            'user': 'bob',
            'db': 'foo',
            'roles': [{'db': 'foo', 'role': 'read'}, {'db': 'bar', 'role': 'readWrite'}],
        }
        result, user_add = self._run_main({
            'database': 'foo',
            'name': 'bob',
            'roles': ['read'],
            'append': True,
            'update_password': 'on_create',
        }, existing_user)

        self.assertFalse(result['changed'])
        user_add.assert_not_called()

    def test_main_without_append_replaces_roles(self):
        existing_user = {
            'user': 'bob',
            'db': 'foo',
            'roles': [{'db': 'foo', 'role': 'read'}],
        }
        result, user_add = self._run_main({
            'database': 'foo',
            'name': 'bob',
            'roles': ['readWrite'],
            'update_password': 'on_create',
        }, existing_user)

        self.assertTrue(result['changed'])
        self.assertEqual(['readWrite'], user_add.call_args[0][5])

    def test_main_append_always_mode_keeps_existing_roles(self):
        existing_user = {
            'user': 'bob',
            'db': 'foo',
            'roles': [{'db': 'admin', 'role': 'clusterMonitor'}],
        }
        result, user_add = self._run_main({
            'database': 'foo',
            'name': 'bob',
            'password': 'secret',
            'roles': ['read'],
            'append': True,
        }, existing_user)

        self.assertTrue(result['changed'])
        self.assertEqual('secret', user_add.call_args[0][4])
        self.assertEqual(
            [{'db': 'admin', 'role': 'clusterMonitor'}, {'role': 'read', 'db': 'foo'}],
            user_add.call_args[0][5],
        )


if __name__ == '__main__':
    unittest.main()
