#!/usr/bin/python

# 2020 Rhys Campbell <rhys.james.campbell@googlemail.com>
# https://github.com/rhysmeister
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function


DOCUMENTATION = '''
---
module: mongodb_shell
author: Rhys Campbell (@rhysmeister)
short_description: Run commands via the MongoDB shell.
requirements:
  - mongo
description:
    - Run commands via the MongoDB shell.
    - Commands provided with the eval parameter or included in a Javascript file.
    - Attempts to parse returned data into a format that Ansible can use.

extends_documentation_fragment:
  - community.mongodb.login_options

options:
  mongo_cmd:
    description:
      - The MongoDB shell command.
    type: str
    default: "mongo"
  db:
    description:
      - The database to run commands against
    type: str
    required: false
    default: "test"
  file:
    description:
      - Path to a file containing MongoDB commands.
    type: str
  eval:
    description:
      - A MongoDB command to run.
    type: str
  nodb:
    description:
      - Specify a non-default encoding for output.
    type: bool
    default: false
  norc:
    description:
      - Prevents the shell from sourcing and evaluating ~/.mongorc.js on start up.
    type: bool
    default: false
  quiet:
    description:
      - Silences output from the shell during the connection process..
    type: bool
    default: true
  debug:
    description:
      - show additional debug info.
    type: bool
    default: false
  transform:
    description:
      - Transform the output returned to the user.
      - auto - Attempt to automatically decide the best tranformation.
      - split - Split output on a character.
      - json - parse as json.
      - raw - Return the raw output.
    type: str
    choices:
      - "auto"
      - "split"
      - "json"
      - "raw"
    default: "auto"
  split_char:
    description:
      - Used by the split action in the transform stage.
    type: str
    default: " "
  stringify:
    description:
      - Wraps the command in eval in JSON.stringify(<js cmd>).
      - Useful for escaping documents that are returned in Extended JSON format.
    type: bool
    default: false
  additional_args:
    description:
      - Additional arguments to supply to the mongo command.
      - Supply as key-value pairs.
      - If the parameter is a valueless flag supply an empty string as the value.
    type: raw
'''

EXAMPLES = '''
- name: Run the listDatabases command
  community.mongodb.mongodb_shell:
    login_user: user
    login_password: secret
    eval: "db.adminCommand('listDatabases')"

- name: List collections and stringify the output
  community.mongodb.mongodb_shell:
    login_user: user
    login_password: secret
    eval: "db.adminCommand('listCollections')"
    stringify: yes

- name: Run the showBuiltinRoles command
  community.mongodb.mongodb_shell:
    login_user: user
    login_password: secret
    eval: "db.getRoles({showBuiltinRoles: true})"

- name: Run a js file containing MongoDB commands
  community.mongodb.mongodb_shell:
    login_user: user
    login_password: secret
    file: "/path/to/mongo/file.js"

- name: Provide a couple of additional cmd args
  community.mongodb.mongodb_shell:
    login_user: user
    login_password: secret
    eval: "db.adminCommand('listDatabases')"
    additional_args:
      verbose: True
      networkMessageCompressors: "snappy"
'''

RETURN = '''
file:
  description: JS file that was executed successfully.
  returned: When a js file is used.
  type: str
msg:
  description: A message indicating what has happened.
  returned: always
  type: str
transformed_output:
  description: Output from the mongo command. We attempt to parse this into a list or json where possible.
  returned: on success
  type: list
changed:
  description: Change status.
  returned: always
  type: bool
failed:
  description: Something went wrong.
  returned: on failure
  type: bool
out:
  description: Raw stdout from mongo.
  returned: when debug is set to true
  type: str
err:
  description: Raw stderr from mongo.
  returned: when debug is set to true
  type: str
rc:
  description: Return code from mongo.
  returned: when debug is set to true
  type: int
'''

from ansible.module_utils.basic import AnsibleModule, load_platform_subclass
import socket
import re
import time
import json
__metaclass__ = type

from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    mongodb_common_argument_spec
)


def add_arg_to_cmd(cmd_list, param_name, param_value, is_bool=False):
    """
    @cmd_list - List of cmd args.
    @param_name - Param name / flag.
    @param_value - Value of the parameter
    @is_bool - Flag is a boolean and has no value.
    """
    if is_bool is False and param_value is not None:
        cmd_list.append(param_name)
        if param_name == "--eval":
            cmd_list.append("\"{0}\"".format(param_value))
        else:
            cmd_list.append(param_value)
    elif is_bool is True:
        cmd_list.append(param_name)
    return cmd_list


def transform_output(output, transform_type, split_char):
    if transform_type == "auto":  # determine what transform_type to perform
        if output.strip().startswith("{") or output.strip().startswith("["):
            transform_type = "json"
        elif isinstance(output.strip().split(None), list):  # Splits on whitespace
            transform_type = "split"
            split_char = None
        elif isinstance(output.strip().split(","), list):
            transform_type = "split"
            split_char = ","
        elif isinstance(output.strip().split(" "), list):
            transform_type = "split"
            split_char = " "
        elif isinstance(output.strip().split("|"), list):
            transform_type = "split"
            split_char = "|"
        elif isinstance(output.strip().split("\t"), list):
            transform_type = "split"
            split_char = "\t"
        else:
            tranform_type = "raw"
    if transform_type == "json":
        output = json.loads(output)
    elif transform_type == "split":
        output = output.strip().split(split_char)
    elif transform_type == "raw":
        output = output.strip()
    return output


def main():
    argument_spec = mongodb_common_argument_spec(ssl_options=False)
    argument_spec.update(
        mongo_cmd=dict(type='str', default="mongo"),
        file=dict(type='str', required=False),
        eval=dict(type='str', required=False),
        db=dict(type='str', required=False, default="test"),
        nodb=dict(type='bool', required=False, default=False),
        norc=dict(type='bool', required=False, default=False),
        quiet=dict(type='bool', required=False, default=True),
        debug=dict(type='bool', required=False, default=False),
        transform=dict(type='str', choices=["auto", "split", "json", "raw"], default="auto"),
        split_char=dict(type='str', default=" "),
        stringify=dict(type='bool', default=False),
        additional_args=dict(type='raw'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[['login_user', 'login_password']],
        mutually_exclusive=[["eval", "file"]]
    )

    args = [
        module.params['mongo_cmd'],
        module.params['db']
    ]

    if not module.params['file']:
        if module.params['eval'].startswith("show "):
            msg = "You cannot use any shell helper (e.g. use <dbname>, show dbs, etc.)"\
                  " inside the eval parameter because they are not valid JavaScript."
            module.fail_json(msg=msg)
        if module.params['stringify']:
            module.params['eval'] = "JSON.stringify({0})".format(module.params['eval'])

    args = add_arg_to_cmd(args, "--host", module.params['login_host'])
    args = add_arg_to_cmd(args, "--port", module.params['login_port'])
    args = add_arg_to_cmd(args, "--username", module.params['login_user'])
    args = add_arg_to_cmd(args, "--password", module.params['login_password'])
    args = add_arg_to_cmd(args, "--authenticationDatabase", module.params['login_database'])
    args = add_arg_to_cmd(args, "--eval", module.params['eval'])
    args = add_arg_to_cmd(args, "--nodb", None, module.params['nodb'])
    args = add_arg_to_cmd(args, "--norc", None, module.params['norc'])
    args = add_arg_to_cmd(args, "--quiet", None, module.params['quiet'])

    additional_args = module.params['additional_args']
    if additional_args is not None:
        for key, value in additional_args.items():
            if isinstance(value, bool):
                args.append(" --{0}".format(key))
            elif isinstance(value, str) or isinstance(value, int):
                args.append(" --{0} {1}".format(key, value))
    if module.params['file']:
        args.pop(1)
        args.append(module.params['file'])

    rc = None
    out = ''
    err = ''
    result = {}
    cmd = " ".join(str(item) for item in args)

    (rc, out, err) = module.run_command(cmd, check_rc=False)

    if module.params['debug']:
        result['out'] = out
        result['err'] = err
        result['rc'] = rc
        result['cmd'] = cmd

    if rc != 0:
        if err is None or err == "":
            err = out
        module.fail_json(msg=err.strip(), **result)
    else:
        result['changed'] = True
        try:
            output = transform_output(out,
                                      module.params['transform'],
                                      module.params['split_char'])
            result['transformed_output'] = output
            result['msg'] = "transform type was {0}".format(module.params['transform'])
            if module.params['file'] is not None:
                result['file'] = module.params['file']
        except Exception as excep:
            result['msg'] = "Error tranforming output: {0}".format(str(excep))
            result['transformed_output'] = None

    module.exit_json(**result)


if __name__ == '__main__':
    main()
