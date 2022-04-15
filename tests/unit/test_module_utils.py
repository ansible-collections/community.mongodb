from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import unittest
import sys
import os
path = os.path.dirname(os.path.realpath(__file__))
path = "{0}/../../plugins/module_utils".format(path)
sys.path.append(path)
import mongodb_common
from distutils.version import LooseVersion
from pymongo import MongoClient


class FakeAnsibleModule:

    params = {
        "login_host": "localhost",
        "login_port": 27017,
        "replica_set": "rs0",
        "reconfigure": True,
        "ssl": False,
        "ssl_cert_reqs": "CERT_REQUIRED",
        "ssl_ca_certs": "/tmp/ca.crt",
        "ssl_crlfile": "/tmp/tmp.crl",
        "ssl_certfile": "/tmp/tls.key",
        "ssl_keyfile": "/tmp/tls.key",
        "ssl_pem_passphrase": "secret",
        "auth_mechanism": None,
        "connection_options": [{"one": 1},
                               {"two": 2},
                               {"three": 3},
                               {"four": 4},
                               {"five": 5}]
    }

    def __init__(self):
        self.msg = ""

    def fail_json(self, msg):
        self.msg = msg

    def get_msg(self):
        return self.msg


class TestMongoDBCommonMethods(unittest.TestCase):

    member_config_defaults = {
        "arbiterOnly": False,
        "buildIndexes": True,
        "hidden": False,
        "priority": {"nonarbiter": 1.0, "arbiter": 0},
        "tags": {},
        "secondardDelaySecs": 0,
        "votes": 1
    }

    def test_check_compatibility_old_pymongo_version(self):
        # (mongo version, pymongo version, msg)
        versions = [
            ('2.6', '2.0', 'you must use pymongo 2.7+ with MongoDB 2.6'),
            ('3.0', '2.7', 'you must use pymongo 2.8+ with MongoDB 3.0'),
            ('3.2', '3.0', 'you must use pymongo 3.2+ with MongoDB >= 3.2'),
            ('3.4', '3.3', 'you must use pymongo 3.4+ with MongoDB >= 3.4'),
            ('3.6', '3.5', 'you must use pymongo 3.6+ with MongoDB >= 3.6'),
            ('4.0', '3.6', 'you must use pymongo 3.7+ with MongoDB >= 4.0'),
            ('4.2', '3.8', 'you must use pymongo 3.9+ with MongoDB >= 4.2'),
            ('4.4', '3.10', 'you must use pymongo 3.11+ with MongoDB >= 4.4'),
            ('5.0', '3.11', 'you must use pymongo 3.12+ with MongoDB >= 5.0')
        ]

        for tuple in versions:
            fake_module = FakeAnsibleModule()
            mongodb_common.check_compatibility(fake_module, LooseVersion(tuple[0]), LooseVersion(tuple[1]))
            msg = fake_module.get_msg()
            assert tuple[2] in msg

    def test_check_compatibility_correct_pymongo_version(self):
        # (mongo version, pymongo version)
        versions = [
            ('2.6', '2.8'),
            ('3.0', '2.9'),
            ('3.2', '3.2'),
            ('3.4', '3.4'),
            ('3.6', '3.6'),
            ('4.0', '3.7'),
            ('4.2', '3.9'),
            ('4.4', '3.11'),
            ('5.0', '3.12')
        ]

        for tuple in versions:
            fake_module = FakeAnsibleModule()
            mongodb_common.check_compatibility(fake_module, LooseVersion(tuple[0]), LooseVersion(tuple[1]))
            msg = fake_module.get_msg()
            assert msg == ""  # Up-to-date pymongo versions get no message

    def test_load_mongocnf(self):
        with open(os.path.expanduser("~/.mongodb.cnf"), "w+") as w:
            w.write("""
            [client]
            user = mongo_user
            pass = 123456
            """)
        creds = mongodb_common.load_mongocnf()
        assert creds['user'] == "mongo_user"
        assert creds['password'] == "123456"

    def test_mongodb_common_argument_spec(self):
        mongo_dict = mongodb_common.mongodb_common_argument_spec()
        assert "login_user" in mongo_dict
        assert "login_password" in mongo_dict
        assert "login_host" in mongo_dict
        assert "login_port" in mongo_dict
        assert "ssl" in mongo_dict
        assert "ssl_cert_reqs" in mongo_dict
        assert "ssl_ca_certs" in mongo_dict
        assert "ssl_crlfile" in mongo_dict
        assert "ssl_certfile" in mongo_dict
        assert "ssl_keyfile" in mongo_dict
        assert "ssl_pem_passphrase" in mongo_dict
        assert "auth_mechanism" in mongo_dict
        assert mongo_dict["login_port"]["default"] == 27017
        assert mongo_dict["login_host"]["default"] == "localhost"
        assert mongo_dict["login_database"]["default"] == "admin"

    def test_ssl_connection_options(self):
        connection_params = dict()
        fake_module = FakeAnsibleModule()
        ssl_dict = mongodb_common.ssl_connection_options(connection_params, fake_module)
        assert isinstance(ssl_dict, dict)
        assert ssl_dict["ssl"] is True
        assert "ssl_cert_reqs" in ssl_dict
        assert "ssl_ca_certs" in ssl_dict
        assert "ssl_crlfile" in ssl_dict
        assert "ssl_certfile" in ssl_dict
        assert "ssl_keyfile" in ssl_dict
        assert "ssl_pem_passphrase" in ssl_dict
        assert "authMechanism" not in ssl_dict

    def test_ssl_connection_options_auth_mechanism(self):
        connection_params = dict()
        fake_module = FakeAnsibleModule()
        fake_module.params["auth_mechanism"] = "MONGODB-X509"
        ssl_dict = mongodb_common.ssl_connection_options(connection_params, fake_module)
        assert isinstance(ssl_dict, dict)
        assert ssl_dict["ssl"] is True
        assert "ssl_cert_reqs" in ssl_dict
        assert "ssl_ca_certs" in ssl_dict
        assert "ssl_crlfile" in ssl_dict
        assert "ssl_certfile" in ssl_dict
        assert "ssl_keyfile" in ssl_dict
        assert "ssl_pem_passphrase" in ssl_dict
        assert "authMechanism" in ssl_dict
        assert ssl_dict["one"] == 1
        assert ssl_dict["two"] == 2
        assert ssl_dict["three"] == 3
        assert ssl_dict["four"] == 4
        assert ssl_dict["five"] == 5
        assert ssl_dict["authMechanism"] == "MONGODB-X509"

    def test_ssl_connection_options_auth_mechanism_strings(self):
        connection_params = dict()
        fake_module = FakeAnsibleModule()
        fake_module.params["auth_mechanism"] = "MONGODB-X509"
        fake_module.params["connection_options"] = [
            "one=1",
            "two=2",
            "three=3",
            "four=4",
            "five=5"
        ]
        ssl_dict = mongodb_common.ssl_connection_options(connection_params, fake_module)
        assert isinstance(ssl_dict, dict)
        assert ssl_dict["ssl"] is True
        assert "ssl_cert_reqs" in ssl_dict
        assert "ssl_ca_certs" in ssl_dict
        assert "ssl_crlfile" in ssl_dict
        assert "ssl_certfile" in ssl_dict
        assert "ssl_keyfile" in ssl_dict
        assert "ssl_pem_passphrase" in ssl_dict
        assert "authMechanism" in ssl_dict
        assert ssl_dict["one"] == '1'
        assert ssl_dict["two"] == '2'
        assert ssl_dict["three"] == '3'
        assert ssl_dict["four"] == '4'
        assert ssl_dict["five"] == '5'
        assert ssl_dict["authMechanism"] == "MONGODB-X509"

    def test_member_state(self):
        client = MongoClient(host=['localhost:27017'],
                             username='user',
                             password='password',
                             replicaSet='replset')
        ms = mongodb_common.member_state(client)
        assert ms == "PRIMARY" or ms == "SECONDARY"

    def test_index_exists(self):
        client = MongoClient(host=['localhost:27017'],
                             username='user',
                             password='password',
                             replicaSet='replset')
        mongodb_common.create_index(client,
                                    'test',
                                    'rhys',
                                    {'username': 1},
                                    {"name": "test_index"})
        index_exists = mongodb_common.index_exists(client,
                                                   'test',
                                                   'rhys',
                                                   'test_index')
        assert isinstance(index_exists, bool) and index_exists
        mongodb_common.drop_index(client,
                                  'test',
                                  'rhys',
                                  'test_index')
        index_exists = mongodb_common.index_exists(client,
                                                   'test',
                                                   'rhys',
                                                   'test_index')
        assert isinstance(index_exists, bool) and not index_exists

    def test_mongodb_auth(self):
        fake_module = FakeAnsibleModule()
        fake_module.params["login_user"] = "user"
        fake_module.params["login_password"] = "password"
        fake_module.params["login_database"] = "test"

        client = MongoClient(host=['localhost:27017'],
                             username=None,
                             password=None,
                             replicaSet='replset')

        success = mongodb_common.mongo_auth(fake_module, client)
        assert success

        with open(os.path.expanduser("~/.mongodb.cnf"), "w+") as w:
            w.write("""
            [client]
            user = mongo_user
            pass = 123456
            """)
            fake_module.params["login_user"] = "user"
            fake_module.params["login_password"] = "password"
            fake_module.params["login_database"] = "test"
            client = MongoClient(host=['localhost:27017'],
                                 username=None,
                                 password=None,
                                 replicaSet='replset')

            success = mongodb_common.mongo_auth(fake_module, client)
            assert success

        with open(os.path.expanduser("~/.mongodb.cnf"), "w+") as w:
            w.write("""
            [client]
            user = mongo_user
            pass = 123456
            """)
            fake_module.params["login_user"] = None
            fake_module.params["login_password"] = "password"
            fake_module.params["login_database"] = "test"
            client = MongoClient(host=['localhost:27017'],
                                 username=None,
                                 password=None,
                                 replicaSet='replset')

            success = mongodb_common.mongo_auth(fake_module, client)
            assert success

    def test_mongo_auth(self):
        client = MongoClient(host=['localhost:27017'],
                             username='user',
                             password='password',
                             directConnection=True)
        fake_module = FakeAnsibleModule()
        fake_module.params["login_user"] = "dummy"
        fake_module.params["login_password"] = None
        fake_module.params["login_database"] = "test"
        fake_module.params["replica_set"] = None
        mongodb_common.mongo_auth(fake_module, client)
        msg = fake_module.get_msg()
        assert "When supplying login arguments" in msg

        fake_module.params["login_password"] = "password"
        fake_module.params["login_database"] = "test"
        client = mongodb_common.mongo_auth(fake_module, client)
        assert "MongoClient" in str(client)

        fake_module.params["'create_for_localhost_exception"] = None
        client = mongodb_common.mongo_auth(fake_module, client)
        assert "MongoClient" in str(client)

        if os.path.exists(os.path.expanduser('~/.mongodb.cnf')):
            os.remove(os.path.expanduser('~/.mongodb.cnf'))
        fake_module.params["login_user"] = None
        fake_module.params["login_password"] = None
        client = mongodb_common.mongo_auth(fake_module, client)
        fail_msg = fake_module.get_msg()
        self.assertTrue('No credentials to authenticate' in fail_msg, msg='{0}'.format(fail_msg))

        fake_module.params['create_for_localhost_exception'] = None
        fake_module.params["login_user"] = None
        fake_module.params["login_password"] = None
        fake_module.params["login_database"] = "test"
        fake_module.params["database"] = "test"
        client = mongodb_common.mongo_auth(fake_module, client)
        fail_msg = fake_module.get_msg()
        print(fail_msg)
        self.assertTrue('The localhost login exception only allows the first admin account to be created' in fail_msg)

        fake_module.params['create_for_localhost_exception'] = None
        fake_module.params["login_user"] = None
        fake_module.params["login_password"] = None
        fake_module.params["login_database"] = "admin"
        fake_module.params["database"] = "admin"
        client = mongodb_common.mongo_auth(fake_module, client)
        assert "MongoClient" in str(client)

        client = MongoClient(host=['localhost:27017'],
                             replicaSet='replset')
        fake_module.params['create_for_localhost_exception'] = None
        fake_module.params["login_user"] = "user"
        fake_module.params["login_password"] = "password"
        fake_module.params["login_database"] = "test"
        try:
            client = mongodb_common.mongo_auth(fake_module, client)
        except Exception as excep:
            assert 'Authentication failed' in str(excep)
            assert "MongoClient" in str(client)

    def test_member_dicts_different_1(self):
        # mongodb replicaset config document format
        conf = {
            "members": [
                {"_id": 1, "host": "localhost:3001"},
                {"_id": 2, "host": "localhost:3002"},
                {"_id": 3, "host": "localhost:3003"}
            ]
        }
        for member in conf["members"]:
            member.update(self.member_config_defaults)
        # list of dicts
        members = [{"host": "localhost:3001"},
                   {"host": "localhost:3002"},
                   {"host": "localhost:3003"}]
        self.assertFalse(mongodb_common.member_dicts_different(conf, members))

    def test_member_dicts_different_2(self):
        # mongodb replicaset config document format
        conf = {
            "members": [
                {"_id": 1, "host": "localhost:3001"},
                {"_id": 2, "host": "localhost:3002"}
            ]
        }
        for member in conf["members"]:
            member.update(self.member_config_defaults)
        # list of dicts
        members = [{"host": "localhost:3001"},
                   {"host": "localhost:3002"},
                   {"host": "localhost:3004"}]
        self.assertTrue(mongodb_common.member_dicts_different(conf, members))

    def test_member_dicts_different_3(self):
        # mongodb replicaset config document format
        conf = {
            "members": [{"_id": 1, "host": "localhost:3001"},
                        {"_id": 2, "host": "localhost:3002"},
                        {"_id": 3, "host": "localhost:3003"}]
        }
        for member in conf["members"]:
            member.update(self.member_config_defaults)
        # list of dicts
        members = [{"host": "localhost:3001"},
                   {"host": "localhost:3002"}]
        self.assertTrue(mongodb_common.member_dicts_different(conf, members))

    def test_member_dicts_different_4(self):
        # mongodb replicaset config document format
        conf = {
            "members": [
                {"_id": 1, "host": "localhost:3001"},
                {"_id": 2, "host": "localhost:3002"}
            ]
        }
        for member in conf["members"]:
            member.update(self.member_config_defaults)
        # list of dicts
        members = [{"host": "localhost:3001"},
                   {"host": "localhost:3002"},
                   {"host": "localhost:3004", "votes": 0, "priority": 0, "hidden": True}]
        # 3004 using non-default values
        self.assertTrue(mongodb_common.member_dicts_different(conf, members))

    def test_member_dicts_different_5(self):
        # mongodb replicaset config document format
        conf = {
            "members": [
                {"_id": 1, "host": "localhost:3001"},
                {"_id": 2, "host": "localhost:3002"},
                {"_id": 2, "host": "localhost:3004"}
            ]
        }
        for member in conf["members"]:
            member.update(self.member_config_defaults)
        # list of dicts
        members = [{"host": "localhost:3001"},
                   {"host": "localhost:3002"},
                   {"host": "localhost:3004", "votes": 1, "priority": 1, "hidden": False}]
        # Should return false as the additonal dict keys are default values
        self.assertFalse(mongodb_common.member_dicts_different(conf, members))

    def test_lists_are_different1(self):
        l1 = [
            "localhost:3001",
            "localhost:3002",
            "localhost:3003"
        ]
        l2 = [
            "localhost:3001",
            "localhost:3002",
            "localhost:3003"
        ]
        self.assertFalse(mongodb_common.lists_are_different(l1, l2))

    def test_lists_are_different2(self):
        l1 = [
            "localhost:3001",
            "localhost:3002"
        ]
        l2 = [
            "localhost:3001",
            "localhost:3002",
            "localhost:3003"
        ]
        self.assertTrue(mongodb_common.lists_are_different(l1, l2))

    def test_lists_are_different1(self):
        l1 = [
            "localhost:3001",
            "localhost:3002",
            "localhost:3003"
        ]
        l2 = [
            "localhost:3002",
            "localhost:3003"
        ]
        self.assertTrue(mongodb_common.lists_are_different(l1, l2))

    def test_get_mongodb_client_1(self):
        fake_module = FakeAnsibleModule()
        client = mongodb_common.get_mongodb_client(fake_module)
        assert "MongoClient" in str(client)

    # def test_get_mongodb_client_2(self):
    #     fake_module = FakeAnsibleModule()
    #     fake_module.params['ssl'] = True
    #     client = mongodb_common.get_mongodb_client(fake_module)
    #     assert "MongoClient" in str(client)

    def test_get_mongodb_client_3(self):
        fake_module = FakeAnsibleModule()
        del fake_module.params['reconfigure']
        client = mongodb_common.get_mongodb_client(fake_module)
        assert "MongoClient" in str(client)

    def test_is_auth_enabled(self):
        fake_module = FakeAnsibleModule()
        fake_module.params['replica_set'] = 'replset'
        result = mongodb_common.is_auth_enabled(fake_module)
        print("result = {0}".format(result))
        assert result

    def test_is_auth_enabled_no_auth(self):
        fake_module = FakeAnsibleModule()
        fake_module.params['login_port'] = 27999
        fake_module.params['replica_set'] = None
        result = mongodb_common.is_auth_enabled(fake_module)
        assert result is False


if __name__ == '__main__':
    unittest.main()
