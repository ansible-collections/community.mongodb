#!/usr/bin/python

# Copyright: (c) 2020, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_oplog
short_description: Resizes the MongoDB oplog.
description:
  - Resizes the MongoDB oplog.
  - This module should only be used with MongoDB 3.6 and above.
  - Old MongoDB versions should use an alternative method.
  - Consult U(https://docs.mongodb.com/manual/tutorial/change-oplog-size) for further info.
author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  oplog_size_mb:
    description:
      - Desired new size on MB of the oplog.
    type: int
    required: true
  compact:
    description:
      - Runs compact against the oplog.rs collection in the local database to reclaim disk space.
      - Will not run against PRIMARY members.
      - The MongoDB user must have the compact role on the local database for this feature to work.
    type: bool
    default: false
    required: false
  ver:
    description:
      - Version of MongoDB this module is supported from.
      - You probably don't want to modifiy this.
      - Included here for internal testing.
    type: str
    default: "3.6"
notes:
- Requires the pymongo Python package on the remote host, version 2.4.2+. This
  can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
- pymongo
'''

EXAMPLES = r'''
- name: Resize oplog to 16 gigabytes, or 16000 megabytes
  community.mongodb.mongodb_oplog:
    oplog_size_mb:  16000

- name: Resize oplog to 8 gigabytes and compact secondaries to reclaim space
  mongodb_maintenance:
    oplog_size_mb:  8000
    compact: true
'''

RETURN = r'''
changed:
  description: Whether the member oplog was modified.
  returned: success
  type: bool
compacted:
  description: Whether the member oplog was compacted.
  returned: success
  type: bool
msg:
  description: A short description of what happened.
  returned: success
  type: str
failed:
  description: If something went wrong
  returned: failed
  type: bool
'''

from copy import deepcopy

import os
import ssl as ssl_lib
from distutils.version import LooseVersion


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import binary_type, text_type
from ansible.module_utils.six.moves import configparser
from ansible.module_utils._text import to_native
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    check_compatibility,
    missing_required_lib,
    load_mongocnf,
    mongodb_common_argument_spec,
    member_state,
    ssl_connection_options
)
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import PyMongoVersion, PYMONGO_IMP_ERR, pymongo_found, MongoClient


def get_olplog_size(client):
    return int(client["local"].command("collStats", "oplog.rs")["maxSize"]) / 1024 / 1024


def set_oplog_size(client, oplog_size_mb):
    client["admin"].command({"replSetResizeOplog": 1, "size": oplog_size_mb})


def compact_oplog(client):
    client["local"].command("compact", "oplog.rs")


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        compact=dict(type='bool', default=False),
        oplog_size_mb=dict(type='int', required=True),
        ver=dict(type='str', default='3.6')
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[['login_user', 'login_password']],
    )

    if not pymongo_found:
        module.fail_json(msg=missing_required_lib('pymongo'),
                         exception=PYMONGO_IMP_ERR)

    login_user = module.params['login_user']
    login_password = module.params['login_password']
    login_database = module.params['login_database']
    login_host = module.params['login_host']
    login_port = module.params['login_port']
    oplog_size_mb = module.params['oplog_size_mb']
    compact = module.params['compact']
    ver = module.params['ver']
    ssl = module.params['ssl']

    result = dict(
        changed=False,
    )

    connection_params = dict(
        host=login_host,
        port=int(login_port),
    )

    if ssl:
        connection_params = ssl_connection_options(connection_params, module)

    try:
        client = MongoClient(**connection_params)
    except Exception as excep:
        module.fail_json(msg='Unable to connect to MongoDB: %s' % to_native(excep))

    if login_user is None and login_password is None:
        mongocnf_creds = load_mongocnf()
        if mongocnf_creds is not False:
            login_user = mongocnf_creds['user']
            login_password = mongocnf_creds['password']
    elif login_password is None or login_user is None:
        module.fail_json(msg="When supplying login arguments, both 'login_user' and 'login_password' must be provided")

    if login_user is not None and login_password is not None:
        try:
            client.admin.authenticate(login_user, login_password, source=login_database)
            # Get server version:
            try:
                srv_version = LooseVersion(client.server_info()['version'])
                if srv_version < LooseVersion(ver):
                    module.fail_json(msg="This module does not support MongoDB {0}".format(srv_version))
            except Exception as excep:
                module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(excep))

            # Get driver version::
            driver_version = LooseVersion(PyMongoVersion)
            # Check driver and server version compatibility:
            check_compatibility(module, srv_version, driver_version)
        except Exception as excep:
            module.fail_json(msg='Unable to authenticate with MongoDB: %s' % to_native(excep))

        try:
            current_oplog_size = get_olplog_size(client)
        except Exception as excep:
            module.fail_json(msg='Unable to get current oplog size: %s' % to_native(excep))
        if oplog_size_mb == current_oplog_size:
            result["msg"] = "oplog_size_mb is already {0} mb".format(oplog_size_mb)
            result["compacted"] = False
        else:
            try:
                state = member_state(client)
            except Exception as excep:
                module.fail_json(msg='Unable to get member state: %s' % to_native(excep))
            if module.check_mode:
                result["changed"] = True
                result["msg"] = "oplog has been resized from {0} mb to {1} mb".format(round(current_oplog_size, 0),
                                                                                      round(oplog_size_mb, 0))
                if state == "SECONDARY" and compact and current_oplog_size > oplog_size_mb:
                    result["compacted"] = True
                else:
                    result["compacted"] = False
            else:
                try:
                    set_oplog_size(client, oplog_size_mb)
                    result["changed"] = True
                    result["msg"] = "oplog has been resized from {0} mb to {1} mb".format(round(current_oplog_size, 0),
                                                                                          round(oplog_size_mb, 0))
                except Exception as excep:
                    module.fail_json(msg='Unable to set oplog size: %s' % to_native(excep))
                if state == "SECONDARY" and compact and current_oplog_size > oplog_size_mb:
                    try:
                        compact_oplog(client)
                        result["compacted"] = True
                    except Exception as excep:
                        module.fail_json(msg='Error compacting member oplog: %s' % to_native(excep))
                else:
                    result["compacted"] = False

    module.exit_json(**result)


if __name__ == '__main__':
    main()
