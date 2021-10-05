#!/usr/bin/python

# Copyright: (c) 2020, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_maintenance
short_description: Enables or disables maintenance mode for a secondary member.
description:
  - Enables or disables maintenance mode for a secondary member.
  - Wrapper around the replSetMaintenance command.
  - Performs no actions against a PRIMARY member.
  - When enabled SECONDARY members will not service reads.
author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  maintenance:
    description: Enable or disable maintenance mode.
    type: bool
    default: false
notes:
  - Requires the pymongo Python package on the remote host, version 2.4.2+. This
    can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
  - pymongo
'''

EXAMPLES = r'''
- name: Enable maintenance mode
  community.mongodb.mongodb_maintenance:
    maintenance: true

- name: Disable maintenance mode
  community.mongodb.mongodb_maintenance:
    maintenance: false
'''

RETURN = r'''
changed:
  description: Whether the member was placed into maintenance mode or not.
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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    missing_required_lib,
    mongodb_common_argument_spec,
    member_state,
    ssl_connection_options,
    mongo_auth
)
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    PYMONGO_IMP_ERR,
    pymongo_found,
    MongoClient
)


def put_in_maint_mode(client):
    client['admin'].command('replSetMaintenance', True)


def remove_maint_mode(client):
    client['admin'].command('replSetMaintenance', False)


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        maintenance=dict(type='bool', default=False)
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
        connection_params = ssl_connection_options(connection_params, module)

    try:
        client = MongoClient(**connection_params)
    except Exception as excep:
        module.fail_json(msg='Unable to connect to MongoDB: %s' % to_native(excep))

    mongo_auth(module, client)

    try:
        state = member_state(client)
        if state == "PRIMARY":
            result["msg"] = "no action taken as member state was PRIMARY"
        elif state == "SECONDARY":
            if maintenance:
                if module.check_mode:
                    result["changed"] = True
                    result["msg"] = "member was placed into maintenance mode"
                else:
                    put_in_maint_mode(client)
                    result["changed"] = True
                    result["msg"] = "member was placed into maintenance mode"
            else:
                result["msg"] = "No action taken as maintenance parameter is false and member state is SECONDARY"
        elif state == "RECOVERING":
            if maintenance:
                result["msg"] = "no action taken as member is already in a RECOVERING state"
            else:
                if module.check_mode:
                    result["changed"] = True
                    result["msg"] = "the member was removed from maintenance mode"
                else:
                    remove_maint_mode(client)
                    result["changed"] = True
                    result["msg"] = "the member was removed from maintenance mode"
        else:
            result["msg"] = "no action taken as member state was {0}".format(state)
    except Exception as excep:
        module.fail_json(msg='module encountered an error: %s' % to_native(excep))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
