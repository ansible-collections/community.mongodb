#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Rhys Campbell (@rhysmeister) <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_index

short_description: Creates or drops indexes on MongoDB collections.

description:
- Creates or drops indexes on MongoDB collections.

author: Rhys Campbell (@rhysmeister)


options:
  login_user:
    description:
    - The MongoDB user to login with.
    - Required when I(login_password) is specified.
    required: no
    type: str
  login_password:
    description:
    - The password used to authenticate with.
    - Required when I(login_user) is specified.
    required: no
    type: str
  login_database:
    description:
    - The database where login credentials are stored.
    required: no
    type: str
    default: 'admin'
  login_host:
    description:
    - The host running MongoDB instance to login to.
    required: no
    type: str
    default: 'localhost'
  login_port:
    description:
    - The MongoDB server port to login to.
    required: no
    type: int
    default: 27017
  ssl:
    description:
    - Whether to use an SSL connection when connecting to the database.
    required: no
    type: bool
    default: no
  ssl_cert_reqs:
    description:
    - Specifies whether a certificate is required from the other side of the connection,
      and whether it will be validated if provided.
    required: no
    type: str
    default: 'CERT_REQUIRED'
    choices: ['CERT_NONE', 'CERT_OPTIONAL', 'CERT_REQUIRED']
  indexes:
    description:
      - List of indexes to create or drop
    type: list
    elements: raw
notes:
    - Requires the pymongo Python package on the remote host, version 2.4.2+.

requirements: [ 'pymongo' ]
'''

EXAMPLES = r'''
- name: Create a single index on a collection
  mongodb_index:
    login_user: admin
    login_password: secret
    indexes:
      - database: mydb
        collection: test
        keys:
          username: 1
          last_login: -1
        options:
          name: myindex

- name: Drop an index on a collection
  mongodb_index:
    login_user: admin
    login_password: secret
    indexes:
      - database: mydb
        collection: test
        options:
          index_name: myindex
        state: absent

- name: Create multiple indexes
  mongodb_index:
    login_user: admin
    login_password: secret
    indexes:
      - database: mydb
        collection: test
        keys:
          username: 1
          last_login: -1
        options:
          name: myindex
      - database: mydb
        collection: test
        keys:
          email: 1
          last_login: -1
        options:
          name: myindex2
'''

RETURN = r'''
indexes_created:
  description: List of indexes created.
  returned: always
  type: list
  sample: ["myindex", "myindex2"]
indexes_dropped:
  description: List of indexes dropped.
  returned: always
  type: list
  sample: ["myindex", "myindex2"]
changed:
  description: Indicates the module has changed something.
  returned: When the module has changed something.
  type: bool
failed:
  description: Indicates the module has failed.
  returned: When the module has encountered an error.
  type: bool
'''

from uuid import UUID

import ssl as ssl_lib
from distutils.version import LooseVersion

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils.six import iteritems
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import check_compatibility, missing_required_lib
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import PyMongoVersion, PYMONGO_IMP_ERR, pymongo_found, MongoClient
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import index_exists, create_index, drop_index

# ================
# Module execution
#

def main():
    argument_spec = dict(
        login_user=dict(type='str', required=False),
        login_password=dict(type='str', required=False, no_log=True),
        login_database=dict(type='str', required=False, default='admin'),
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=27017),
        ssl=dict(type='bool', required=False, default=False),
        ssl_cert_reqs=dict(type='str', required=False, default='CERT_REQUIRED',
                           choices=['CERT_NONE', 'CERT_OPTIONAL', 'CERT_REQUIRED']),
        indexes=dict(type='list', elements='raw', required=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[['login_user', 'login_password']],
    )

    if not pymongo_found:
        module.fail_json(msg=missing_required_lib('pymongo'),
                         exception=PYMONGO_IMP_ERR)
    if len(indexes) == 0:
        module.fail_json(msg="One or more indexes must be specified")
    if not all(isinstance(i, dict) for i in indexes):
        module.fail_json(msg="Indexes must be supplied as dictionaries")
    required_index_keys = [
        "database",
        "collection"
        "keys",
        "options",
        "state"
    ]
    # Ensure keys are present in index spec
    for k in required_index_keys:
        for i in indexes:
            if k not in i.keys()
                module.fail_json(msg="Missing required index key: {0}".format(k))
    # Check index subkeys look correct
    for i in indexes:
        if not isinstance(i["database"], str):
            module.fail_json(msg="Database key should be str")
        elif not isinstance(i["collection"], str):
            module.fail_json(msg="Collection key should be str")
        elif not isinstance(i["keys"], dict):
            module.fail_json(msg="Keys key should be dict")
        elif not isinstance(i["options"], dict):
            module.fail_json(msg="Options key should be dict")
        elif not i["options"].has_key("name"):
            module.fail_json(msg="The options dict must contain a name field")

    login_user = module.params['login_user']
    login_password = module.params['login_password']
    login_database = module.params['login_database']
    login_host = module.params['login_host']
    login_port = module.params['login_port']
    ssl = module.params['ssl']
    indexes = module.params['indexes']

    connection_params = {
        'host': login_host,
        'port': login_port,
    }

    if ssl:
        connection_params['ssl'] = ssl
        connection_params['ssl_cert_reqs'] = getattr(ssl_lib, module.params['ssl_cert_reqs'])

    client = MongoClient(**connection_params)

    if login_user:
        try:
            client.admin.authenticate(login_user, login_password, source=login_database)
        except Exception as e:
            module.fail_json(msg='Unable to authenticate: %s' % to_native(e))

    # Get server version:
    try:
        srv_version = LooseVersion(client.server_info()['version'])
    except Exception as e:
        module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(e))

    # Get driver version::
    driver_version = LooseVersion(PyMongoVersion)

    # Check driver and server version compatibility:
    check_compatibility(module, srv_version, driver_version)

    # Pre flight checks done
    indexes_created = []
    indexes_dropped = []
    changed = None
    for i in indexes:
        if module.check_mode:
            if index_exists(i["database"], i["collection"], i["options"]["name"]):
                if i["state"] == "present":
                    changed = False
                elif i["state"] == "absent":
                    indexes_dropped.append("{0}.{1}.{2}".format(i["database"],
                                                                i["collection"],
                                                                i["options"]["name"]))
                    changed = True
            else:
                if state == "present":
                    indexes_created.append("{0}.{1}.{2}".format(i["database"],
                                                                i["collection"],
                                                                i["options"]["name"])
                    changed = True
                elif i["state"] == "absent":
                    changed = False
        else:
            if index_exists(i["database"], i["collection"], i["options"]["name"]):
                if i["state"] == "present":
                    changed = False
                elif i["state"] == "absent":
                    drop_index(client, i["database"], i["collection"],
                               i["options"]["name"])
                    indexes_dropped.append("{0}.{1}.{2}".format(i["database"],
                                                                i["collection"],
                                                                i["options"]["name"]))
                    changed = True
            else:
                if state == "present":
                    create_index(client=client,
                                 database=i["database"],
                                 collection=i["collection"],
                                 keys=i["keys"],
                                 **options)
                    indexes_created.append("{0}.{1}.{2}".format(i["database"],
                                                                i["collection"],
                                                                i["options"]["name"])
                    changed = True
                elif i["state"] == "absent":
                    changed = False

    module.exit_json(changed=changed,
                     indexes_created=indexes_created,
                     indexes_dropped=indexes_dropped)


if __name__ == '__main__':
    main()
