#!/usr/bin/python

# Copyright: (c) 2020, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_balancer
short_description: Manages the MongoDB Sharded Cluster Balancer.
description:
  - Manages the MongoDB Sharded Cluster Balancer.
  - Start or stop the balancer.
  - Enable or disable the autosplit feature.
author: Rhys Campbell (@rhysmeister)

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  state:
    description:
      - Manage the Balancer for the Cluster
    required: false
    type: str
    choices: ["started", "stopped"]
    default: "started"
  autosplit:
    description:
      - Disable or enable the autosplit flag in the config.settings collection.
    required: false
    type: bool
  mongos_process:
    description:
      - Provide a custom name for the mongos process you are connecting to.
      - Most users can ignore this setting.
    required: false
    type: str
    default: "mongos"
notes:
- Requires the pymongo Python package on the remote host, version 2.4.2+. This
  can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
- pymongo
'''

EXAMPLES = r'''
- name: Stop the balancer
  community.mongodb.mongodb_balancer:
    state: started

- name: Stop the balancer and disable autosplit
  community.mongodb.mongodb_balancer:
    state: stopped
    autosplit: false

- name: Enable autosplit
  community.mongodb.mongodb_balancer:
    autosplit: true
'''

RETURN = r'''
changed:
  description: Whether the balancer state or autosplit changed.
  returned: success
  type: bool
old_balancer_state:
  description: The previous state of the balancer
  returned: When balancer state is changed
  type: str
new_balancer_state:
  description: The new state of the balancer.
  returned: When balancer state is changed
  type: str
old_autosplit:
  description: The previous state of autosplit.
  returned: When autosplit is changed.
  type: str
new_autosplit:
  description: The new state of autosplit.
  returned: When autosplit is changed.
  type: str
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
import time


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
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    PyMongoVersion,
    PYMONGO_IMP_ERR,
    pymongo_found,
    MongoClient
)


def get_balancer_state(client):
    '''
    Gets the state of the MongoDB balancer. The config.settings collection does
    not exist until the balancer has been started for the first time
    { "_id" : "balancer", "mode" : "full", "stopped" : false }
    { "_id" : "autosplit", "enabled" : true }
    '''
    balancer_state = "stopped"
    result = client["config"].settings.find_one({"_id": "balancer"})
    if not result:
        balancer_state = "stopped"
    else:
        if result['stopped'] is False:
            balancer_state = "started"
        else:
            balancer_state = "stopped"
    return balancer_state


def stop_balancer(client):
    '''
    Stops MongoDB balancer
    '''
    client['admin'].command({'balancerStop': 1, 'maxTimeMS': 60000})
    time.sleep(1)


def start_balancer(client):
    '''
    Starts MongoDB balancer
    '''
    client['admin'].command({'balancerStart': 1, 'maxTimeMS': 60000})
    time.sleep(1)


def enable_autosplit(client):
    client["config"].settings.update({"_id": "autosplit"},
                                     {"$set": {"enabled": True}},
                                     upsert=True,
                                     w="majority")


def disable_autosplit(client):
    client["config"].settings.update({"_id": "autosplit"},
                                     {"$set": {"enabled": False}},
                                     upsert=True,
                                     w="majority")


def get_autosplit(client):
    autosplit = False
    result = client["config"].settings.find_one({"_id": "autosplit"})
    if result is not None:
        autosplit = result['enabled']
    return autosplit


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        autosplit=dict(type='bool', default=None),
        mongos_process=dict(type='str', required=False, default="mongos"),
        state=dict(type='str', default="started", choices=["started", "stopped"]),
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
    balancer_state = module.params['state']
    autosplit = module.params['autosplit']
    mongos_process = module.params['mongos_process']
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




        try:
            client['admin'].command('listDatabases', 1.0)  # if this throws an error we need to authenticate
        except Exception as excep:
            if excep.code == 13:
                if login_user is not None and login_password is not None:
                    client.admin.authenticate(login_user, login_password, source=login_database)
                else:
                    module.fail_json(msg='No credentials to authenticate: %s' % to_native(excep))
            else:
                module.fail_json(msg='Unknown error: %s' % to_native(excep))
        # Get server version:
        try:
            srv_version = LooseVersion(client.server_info()['version'])
        except Exception as excep:
            module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(excep))
        try:
            # Get driver version::
            driver_version = LooseVersion(PyMongoVersion)
            # Check driver and server version compatibility:
            check_compatibility(module, srv_version, driver_version)
        except Exception as excep:
            module.fail_json(msg='Unable to authenticate with MongoDB: %s' % to_native(excep))

        cluster_autosplit = None
        old_balancer_state = None
        new_balancer_state = None
        old_autosplit = None
        new_autosplit = None

        try:

            if client["admin"].command("serverStatus")["process"] != mongos_process:
                module.fail_json(msg="Process running on {0}:{1} is not a {2}".format(login_host, login_port, mongos_process))

            cluster_balancer_state = get_balancer_state(client)
            if autosplit is not None:
                cluster_autosplit = get_autosplit(client)

            if module.check_mode:
                if balancer_state != cluster_balancer_state:
                    old_balancer_state = cluster_balancer_state
                    new_balancer_state = balancer_state
                    changed = True
                if (autosplit is not None
                        and autosplit != cluster_autosplit):
                    old_autosplit = cluster_autosplit
                    new_autosplit = autosplit
                    changed = True
            else:
                if balancer_state is not None \
                        and balancer_state != cluster_balancer_state:
                    if balancer_state == "started":
                        start_balancer(client)
                        old_balancer_state = cluster_balancer_state
                        new_balancer_state = get_balancer_state(client)
                        changed = True
                    else:
                        stop_balancer(client)
                        old_balancer_state = cluster_balancer_state
                        new_balancer_state = get_balancer_state(client)
                        changed = True
                    if autosplit is not None \
                            and autosplit != cluster_autosplit:
                        if autosplit:
                            enable_autosplit(client)
                            old_autosplit = cluster_autosplit
                            new_autosplit = autosplit
                            changed = True
                        else:
                            disable_autosplit(client)
                            old_autosplit = cluster_autosplit
                            new_autosplit = autosplit
                            changed = True
        except Exception as excep:
            result["msg"] = "An error occurred: {0}".format(excep)

    if old_balancer_state is not None:
        result['old_balancer_state'] = old_balancer_state
        result['new_balancer_state'] = new_balancer_state
    if old_autosplit is not None:
        result['old_autosplit'] = old_autosplit
        result['new_autosplit'] = new_autosplit

    module.exit_json(**result)


if __name__ == '__main__':
    main()
