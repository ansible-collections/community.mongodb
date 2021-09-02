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

    def get_msg(self):
        return self.msg

    def fail_json(self, msg):
        self.msg = msg


class TestMongoDBCommonMethods(unittest.TestCase):

    def test_check_compatibility_old_pymongo_version(self):
        # (mongo version, pymongo version, msg)
        versions = [
            ('2.6', '2.0', 'you must use pymongo 2.7+ with MongoDB 2.6'),
            ('3.0', '2.7', 'you must use pymongo 2.8+ with MongoDB 3.0'),
            ('3.2', '3.0', 'you must use pymongo 3.2+ with MongoDB >= 3.2'),
            ('3.4', '3.3', 'you must use pymongo 3.4+ with MongoDB >= 3.4'),
            ('3.6', '3.5', 'you must use pymongo 3.6+ with MongoDB >= 3.6'),
            ('4.0', '3.6', 'you must use pymongo 3.7+ with MongoDB >= 4.0'),
            ('4.2', '3.8', 'you must use pymongo 3.9+ with MongoDB >= 4.2')
            ('4.4', '3.10', 'you must use pymongo 3.9+ with MongoDB >= 4.4')
            ('5.0', '3.11', 'you must use pymongo 3.9+ with MongoDB >= 5.0')
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


if __name__ == '__main__':
    unittest.main()
