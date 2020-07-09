#!/usr/bin/python

# Copyright: (c) 2020, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_replicaset_maintenance
short_description: Enables or disables maintnenance mode for a secondary member.
description:
- Enables or disables maintnenance mode for a secondary member.
- Has no effect when executed against a PRIMARY member.
- When enabled the SECONDARY member will not service reads.
author: Rhys Campbell (@rhysmeister)
options:
  login_user:
    description:
    - The username to authenticate with.
    - If auth is not enabled do not supply this value.
    type: str
  login_password:
    description:
    - The password to authenticate with.
    - If auth is not enabled do not supply this value.
    type: str
  login_database:
    description:
    - The database where login credentials are stored.
    type: str
    default: admin
  login_host:
    description:
    - The MongoDB hostname.
    type: str
    default: localhost
  login_port:
    description:
    - The MongoDB port to login to.
    type: int
    default: 27017
  maintenance:
    description: Enable or disable maintnenance mode.
    type: bool
    default: false
  ssl:
    description:
    - Whether to use an SSL connection when connecting to the database
    type: bool
    default: no
  ssl_cert_reqs:
    description:
    - Specifies whether a certificate is required from the other side of the connection, and whether it will be validated if provided.
    type: str
    default: CERT_REQUIRED
    choices: [ CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED ]
notes:
- Requires the pymongo Python package on the remote host, version 2.4.2+. This
  can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
- pymongo
'''

EXAMPLES = r'''
- name: Enable maintenance mode
  mongodb_replicaset_maintenance:
    maintenance: true

- name: Disable maintenance mode
  mongodb_replicaset_maintenance:
    maintnenance: false

'''

RETURN = r'''
changed: Whether the member was placed into maintnenance mode or not.
  returned: success
  type: bool
msg: A short description of what happened.
  returned: success
  type: str
failed: If something went wrong
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
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import check_compatibility, missing_required_lib, load_mongocnf
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import PyMongoVersion, PYMONGO_IMP_ERR, pymongo_found, MongoClient


def member_state(client):
    """Check if a replicaset exists.

    Args:
        client (cursor): Mongodb cursor on admin database.

    Returns:
        str: member state i.e. PRIMARY, SECONDARY
    """
    state = None
    doc = client['admin'].command('replSetGetStatus')
    for member in doc["members"]:
        if "self" in member.keys():
            state = str(member['stateStr'])
    return state


def put_in_maint_mode(client):
    client['admin'].command('replSetMaintenance', True)


def remove_maint_mode(client):
    client['admin'].command('replSetMaintenance', False)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            login_user=dict(type='str'),
            login_password=dict(type='str', no_log=True),
            login_database=dict(type='str', default="admin"),
            login_host=dict(type='str', default="localhost"),
            login_port=dict(type='int', default=27017),
            maintenance=dict(type='bool', default=False),
            ssl=dict(type='bool', default=False),
            ssl_cert_reqs=dict(type='str', default='CERT_REQUIRED', choices=['CERT_NONE', 'CERT_OPTIONAL', 'CERT_REQUIRED']),
        ),
        supports_check_mode=True,
    )

    if not pymongo_found:
        module.fail_json(msg=missing_required_lib('pymongo'),
                         exception=PYMONGO_IMP_ERR)

    login_user = module.params['login_user']
    login_password = module.params['login_password']
    login_database = module.params['login_database']
    login_host = module.params['login_host']
    login_port = module.params['login_port']
    maintenance = module.params['maintenance']
    ssl = module.params['ssl']

    result = dict(
        changed=False,
    )

    connection_params = dict(
        host=login_host,
        port=int(login_port),
    )

    if ssl:
        connection_params["ssl"] = ssl
        connection_params["ssl_cert_reqs"] = getattr(ssl_lib, module.params['ssl_cert_reqs'])

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
            except Exception as excep:
                module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(excep))

            # Get driver version::
            driver_version = LooseVersion(PyMongoVersion)
            # Check driver and server version compatibility:
            check_compatibility(module, srv_version, driver_version)
        except Exception as excep:
            module.fail_json(msg='Unable to authenticate with MongoDB: %s' % to_native(excep))

    try:
        state = member_state(client)
        if state == "PRIMARY":
            result["msg"] = "no action taken as member state was PRIMARY"
        elif state == "SECONDARY":
            if module.check_mode:
                result["changed"] = True
                result["msg"] = "member was placed into maintnenance mode"
            else:
                put_in_maint_mode(client)
                result["changed"] = True
                result["msg"] = "member was placed into maintnenance mode"
        elif state == "RECOVERING":
            result["msg"] = "no action taken as member is already in a RECOVERING state"
        else:
            result["msg"] = "no action taken as member state was {0}".format(state)
    except Exception as excep:
        module.fail_json(msg='module encountered an error: %s' % to_native(excep))

    module.exit_json(**result)

if __name__ == '__main__':
    main()
