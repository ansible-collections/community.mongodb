#!/usr/bin/python

# Copyright: (c) 2020, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_stepdown
short_description: Step down the MongoDB node from a PRIMARY state.
description: >
  Step down the MongoDB node from the PRIMARY state if it has that status.
  Returns OK immediately if the member is already in the SECONDARY or ARBITER states.
  Will wait until a timeout for the member state to reach SECONDARY or PRIMARY,
  if the member state is currently STARTUP, RECOVERING, STARTUP2 or ROLLBACK,
  before taking any needed action.
author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  poll:
    description:
      - The maximum number of times query for the member status.
    type: int
    default: 1
  interval:
    description:
      - The number of seconds to wait between poll executions.
    type: int
    default: 30
  stepdown_seconds:
    description:
      - The number of seconds to step down the primary, during which time the stepdown member is ineligible for becoming primary.
    type: int
    default: 60
  secondary_catch_up:
    description:
      - The secondaryCatchUpPeriodSecs parameter for the stepDown command.
      - The number of seconds that mongod will wait for an electable secondary to catch up to the primary.
    type: int
    default: 10
  force:
    description:
      - Optional. A boolean that determines whether the primary steps down if no electable and up-to-date secondary exists within the wait period.
    type: bool
    default: false
notes:
  - Requires the pymongo Python package on the remote host, version 2.4.2+. This
    can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
  - pymongo
'''

EXAMPLES = r'''
- name: Step down the current MongoDB member
  community.mongodb.mongodb_stepdown:
    login_user: admin
    login_password: secret

- name: Step down the current MongoDB member, poll a maximum of 5 times if member state is recovering
  community.mongodb.mongodb_stepdown:
    login_user: admin
    login_password: secret
    poll: 5
    interval: 10
'''

RETURN = r'''
failed:
  description: If the module had failed or not.
  returned: always
  type: bool
iteration:
  description: Number of times the module has queried the replicaset status.
  returned: always
  type: int
msg:
  description: Status message.
  returned: always
  type: str
'''


from copy import deepcopy
import time

import os
import ssl as ssl_lib
from distutils.version import LooseVersion
import traceback


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import binary_type, text_type
from ansible.module_utils.six.moves import configparser
from ansible.module_utils._text import to_native
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    check_compatibility,
    missing_required_lib,
    load_mongocnf,
    mongodb_common_argument_spec,
    ssl_connection_options
)
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import PyMongoVersion, PYMONGO_IMP_ERR, pymongo_found, MongoClient


def member_status(client):
    """
    Return the member status string
    # https://docs.mongodb.com/manual/reference/command/replSetGetStatus/
    """
    myStateStr = None
    rs = client.admin.command('replSetGetStatus')
    for member in rs["members"]:
        if "self" in member.keys():
            myStateStr = member["stateStr"]
    return myStateStr


def member_stepdown(client, module):
    """
    client - MongoDB Client
    module - Ansible module object
    """

    try:
        from collections import OrderedDict
    except ImportError as excep:
        try:
            from ordereddict import OrderedDict
        except ImportError as excep:
            module.fail_json(msg='Cannot import OrderedDict class. You can probably install with: pip install ordereddict: %s'
                             % to_native(excep))

    iterations = 0  # How many times we have queried the member
    failures = 0  # Number of failures when querying the replicaset
    poll = module.params['poll']
    interval = module.params['interval']
    stepdown_seconds = module.params['stepdown_seconds']
    secondary_catch_up = module.params['secondary_catch_up']
    force = module.params['force']
    return_doc = {}
    status = None

    while iterations < poll:
        try:
            iterations += 1
            return_doc['iterations'] = iterations
            myStateStr = member_status(client)
            if myStateStr == "PRIMARY":
                # Run step down command
                if module.check_mode:
                    return_doc["msg"] = "member was stepped down"
                    return_doc['changed'] = True
                    status = True
                    break
                else:
                    cmd_doc = OrderedDict([
                        ('replSetStepDown', stepdown_seconds),
                        ('secondaryCatchUpPeriodSecs', secondary_catch_up),
                        ('force', force)
                    ])
                    try:
                        client.admin.command(cmd_doc)  # For now we assume the stepDown was successful
                    except Exception as excep:
                        # 4.0 and below close the connection as part of the stepdown.
                        # This code should be removed once we support 4.2+ onwards
                        # https://tinyurl.com/yc79g9ay
                        if str(excep) == "connection closed":
                            pass
                        else:
                            raise excep
                    return_doc['changed'] = True
                    status = True
                    return_doc["msg"] = "member was stepped down"
                    break
            elif myStateStr in ["SECONDARY", "ARBITER"]:
                return_doc["msg"] = "member was already at {0} state".format(myStateStr)
                return_doc['changed'] = False
                status = True
                break
            elif myStateStr in ["STARTUP", "RECOVERING", "STARTUP2", "ROLLBACK"]:
                time.sleep(interval)  # Wait for interval
            else:
                return_doc["msg"] = "Unexpected member state {0}".format(myStateStr)
                return_doc['changed'] = False
                status = False
                break
        except Exception as e:
            failures += 1
            return_doc['failed'] = True
            return_doc['changed'] = False
            return_doc['msg'] = str(e)
            status = False
            if iterations == poll:
                break
            else:
                time.sleep(interval)

    return status, return_doc['msg'], return_doc


# =========================================
# Module execution.
#


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        force=dict(type='bool', default=False),
        interval=dict(type='int', default=30),
        poll=dict(type='int', default=1),
        secondary_catch_up=dict(type='int', default=10),
        stepdown_seconds=dict(type='int', default=60)
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
    ssl = module.params['ssl']
    poll = module.params['poll']
    interval = module.params['interval']
    stepdown_seconds = module.params['stepdown_seconds']
    secondary_catch_up = module.params['secondary_catch_up']

    result = dict(
        failed=False,
    )

    connection_params = dict(
        host=login_host,
        port=int(login_port),
    )

    if ssl:
        connection_params = ssl_connection_options(connection_params, module)

    try:
        client = MongoClient(**connection_params)
    except Exception as e:
        module.fail_json(msg='Unable to connect to database: %s' % to_native(e))

    try:
        # Get server version:
        try:
            srv_version = LooseVersion(client.server_info()['version'])
        except Exception as e:
            module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(e))

        # Get driver version::
        driver_version = LooseVersion(PyMongoVersion)

        # Check driver and server version compatibility:
        check_compatibility(module, srv_version, driver_version)
    except Exception as excep:
        if "not authorized on" not in str(excep) and "there are no users authenticated" not in str(excep):
            raise excep
        if login_user is None or login_password is None:
            raise excep
        client.admin.authenticate(login_user, login_password, source=login_database)
        check_compatibility(module, client)

    if login_user is None and login_password is None:
        mongocnf_creds = load_mongocnf()
        if mongocnf_creds is not False:
            login_user = mongocnf_creds['user']
            login_password = mongocnf_creds['password']
    elif login_password is None or login_user is None:
        module.fail_json(msg="When supplying login arguments, both 'login_user' and 'login_password' must be provided")

    try:
        client['admin'].command('listDatabases', 1.0)  # if this throws an error we need to authenticate
    except Exception as excep:
        if "not authorized on" in str(excep) or "command listDatabases requires authentication" in str(excep):
            if login_user is not None and login_password is not None:
                try:
                    client.admin.authenticate(login_user, login_password, source=login_database)
                except Exception as excep:
                    module.fail_json(msg='unable to connect to database: %s' % to_native(excep), exception=traceback.format_exc())
            else:
                module.fail_json(msg='unable to connect to database: %s' % to_native(excep), exception=traceback.format_exc())
        else:
            module.fail_json(msg='unable to connect to database: %s' % to_native(excep), exception=traceback.format_exc())

    try:
        status, msg, return_doc = member_stepdown(client, module)
        iterations = return_doc['iterations']
        changed = return_doc['changed']
    except Exception as e:
        module.fail_json(msg='Unable to query replica_set info: %s' % str(e))

    if status is False:
        module.fail_json(msg=msg, iterations=iterations, changed=changed)
    else:
        module.exit_json(msg=msg, iterations=iterations, changed=changed)


if __name__ == '__main__':
    main()
