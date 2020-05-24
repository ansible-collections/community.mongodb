import unittest
import sys
import os
path = os.path.dirname(os.path.realpath(__file__))
path = "{0}/../../plugins/module_utils".format(path)
sys.path.append(path)
import mongodb_common
from distutils.version import LooseVersion


class FakeAnsibleModule:

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
          assert msg == "" # Up-to-date pymongo versions get no message


    def test_load_mongocnf(self):
        with open(os.path.expanduser("~/.mongodb.cnf"), "w+") as w:
            w.write("""\
                    [client]
                    user = mongo_user
                    pass = 123456
                    """)
        creds = mongodb_common.load_mongocnf()
        creds['user'] == "mongo_user"
        creds['password'] == "123456"


if __name__ == '__main__':
    unittest.main()
