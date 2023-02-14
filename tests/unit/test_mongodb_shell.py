from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import unittest
import sys
import os
script_path = os.path.dirname(os.path.realpath(__file__))
path = "{0}/../../plugins/module_utils".format(script_path)
sys.path.append(path)
import mongodb_shell


class TestMongoDBCommonMethods(unittest.TestCase):

    def test_escape_param(self):
        param = "'"
        s = mongodb_shell.escape_param(param)
        assert isinstance(s, str)
        print(s)
        assert '"' in s

    def test_add_arg_to_cmd1(self):
        cmd_list = []
        param_name = "--append"
        param_value = "Text"
        omit = []
        cmd_list = mongodb_shell.add_arg_to_cmd(cmd_list, param_name, param_value, is_bool=False, omit=omit)
        assert isinstance(cmd_list, list)
        assert len(cmd_list) == 2
        assert cmd_list[0] == "--append"
        assert cmd_list[1] == "Text"

    def test_add_arg_to_cmd2(self):
        cmd_list = []
        param_name = "--append"
        param_value = "Text"
        omit = ["append"]
        cmd_list = mongodb_shell.add_arg_to_cmd(cmd_list, param_name, param_value, is_bool=False, omit=omit)
        assert len(cmd_list) == 0

    def test_add_arg_to_cmd3(self):
        cmd_list = []
        param_name = "--append"
        cmd_list = mongodb_shell.add_arg_to_cmd(cmd_list, param_name, None, is_bool=True, omit=[])
        assert len(cmd_list) == 1

    def test_add_arg_to_cmd4(self):
        cmd_list = []
        param_name = "--eval"
        param_value = "Text"
        omit = []
        cmd_list = mongodb_shell.add_arg_to_cmd(cmd_list, param_name, param_value, is_bool=False, omit=omit)
        assert isinstance(cmd_list, list)
        assert len(cmd_list) == 2
        assert cmd_list[0] == "--eval"
        assert cmd_list[1] == "Text"

    def test_extract_json_document1(self):
        output = """
            WriteResult({
              "nInserted" : 0,
              "writeError" : {
                      "code" : 11000,
                      "errmsg" : "E11000 duplicate key error collection: state.hosts index: _id_ dup key: { _id: \"r1\" }"
              }
      })"""
        doc = mongodb_shell.extract_json_document(output)
        # Returns a string that should look like a json doc
        assert isinstance(doc, str)
        print(doc)
        assert doc[0] == "{"
        assert doc[-1] == "}"

    # TODO Function returns string when we expect a dict
    def test_transform_output1(self):
        output = '''WriteResult({
              "nInserted" : 0,
              "writeError" : {
                      "code" : 11000,
                      "errmsg" : "E11000 duplicate key error collection: state.hosts index: _id_ dup key: { _id: \"r1\" }"
              }
      })'''
        doc = mongodb_shell.extract_json_document(output)
        json_doc = mongodb_shell.transform_output(doc, "json", None)
        assert 'nInserted' in json_doc
        assert 'writeError' in json_doc

    def test_get_hash_value(self):

        class FakeModule:

            params = {"file": None, "eval": "XXXXX"}

            def __init__(self):
                pass

        fake_module = FakeModule()

        h = mongodb_shell.get_hash_value(fake_module)
        assert isinstance(h, str)

    def test_touch(self):
        assert mongodb_shell.touch("/dev/null") is None

    def test_detect_if_cmd_exist1(self):
        assert mongodb_shell.detect_if_cmd_exist(cmd="mongosh") is False

    def test_detect_if_cmd_exist1(self):
        assert mongodb_shell.detect_if_cmd_exist(cmd="cp")

    def test_transform_output_files(self):
        for f in os.listdir("{0}/files/".format(script_path)):
            myfile = open("{0}/files/{1}".format(script_path, f))
            s = myfile.read()
            myfile.close()
            doc = mongodb_shell.extract_json_document(s)
            json_doc = mongodb_shell.transform_output(doc, "json", None)
            assert isinstance(json_doc, str)  # we want this to return dict...


if __name__ == '__main__':
    unittest.main()
