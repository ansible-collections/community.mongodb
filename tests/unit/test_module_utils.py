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


class FakeAnsibleModule:

    params = {
        "ssl": False,
        "ssl_cert_reqs": "CERT_REQUIRED",
        "ssl_ca_certs": None,
        "ssl_crlfile": None,
        "ssl_certfile": None,
        "ssl_keyfile": None,
        "ssl_pem_passphrase": None
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
            ('4.2', '3.9')
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


if __name__ == '__main__':
    unittest.main()
