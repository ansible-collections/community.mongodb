#!/usr/bin/python

# (c) 2018, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
---
module: mongodb_shard
short_description: Add or remove shards from a MongoDB Cluster
description:
    -  Add or remove shards from a MongoDB Cluster.
author: Rhys Campbell (@rhysmeister)

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  shard:
    description:
      - The shard connection string.
      - Should be supplied in the form <replicaset>/host:port as detailed in U(https://docs.mongodb.com/manual/tutorial/add-shards-to-shard-cluster/).
      - For example rs0/example1.mongodb.com:27017.
    required: true
    type: str
  sharded_databases:
    description:
      - Enable sharding on the listed database.
      - Can be supplied as a string or a list of strings.
      - Sharding cannot be disabled on a database.
    required: false
    type: raw
  balancer_state:
    description:
      - Manage the Balancer for the Cluster
    required: false
    type: str
    choices: ["started", "stopped", None]
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
  state:
    description:
      - Whether the shard should be present or absent from the Cluster.
    required: false
    type: str
    default: present
    choices: [absent, present]

notes:
    - Requires the pymongo Python package on the remote host, version 2.4.2+.
requirements: [ pymongo ]
'''

EXAMPLES = '''
- name: Add a replicaset shard named rs1 with a member running on port 27018 on mongodb0.example.net
  mongodb_shard:
    login_user: admin
    login_password: admin
    shard: "rs1/mongodb0.example.net:27018"
    state: present

- name: Add a standalone mongod shard running on port 27018 of mongodb0.example.net
  mongodb_shard:
    login_user: admin
    login_password: admin
    shard: "mongodb0.example.net:27018"
    state: present

- name: To remove a shard called 'rs1'
  mongodb_shard:
    login_user: admin
    login_password: admin
    shard: rs1
    state: absent

# Single node shard running on localhost
- name: Ensure shard rs0 exists
  mongodb_shard:
    login_user: admin
    login_password: secret
    shard: "rs0/localhost:3001"
    state: present

# Single node shard running on localhost
- name: Ensure shard rs1 exists
  mongodb_shard:
    login_user: admin
    login_password: secret
    shard: "rs1/localhost:3002"
    state: present

# Enable sharding on a few databases when creating the shard
- name: To remove a shard called 'rs1'
  mongodb_shard:
    login_user: admin
    login_password: admin
    shard: rs1
    sharded_databases:
      - db1
      - db2
    state: present
'''

RETURN = '''
mongodb_shard:
    description: The name of the shard to create.
    returned: success
    type: str
sharded_enabled:
    description: Databases that have had sharding enabled during module execution.
    returned: success when sharding is enabled
    type: list
'''

import os
import ssl as ssl_lib
from distutils.version import LooseVersion
import traceback
import time


from ansible.module_utils.basic import AnsibleModule, missing_required_lib
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


def shard_find(client, shard):
    """Check if a shard exists.

    Args:
        client (cursor): Mongodb cursor on admin database.
        shard (str): shard to check.

    Returns:
        dict: when user exists, False otherwise.
    """
    if '/' in shard:
        s = shard.split('/')[0]
    else:
        s = shard
    for shard in client["config"].shards.find({"_id": s}):
        return shard
    return False


def shard_add(client, shard):
    try:
        sh = client["admin"].command('addShard', shard)
    except Exception as excep:
        raise excep
    return sh


def shard_remove(client, shard):
    try:
        sh = client["admin"].command('removeShard', shard)
    except Exception as excep:
        raise excep
    return sh


def sharded_dbs(client):
    '''
    Returns the sharded databases
    Args:
        client (cursor): Mongodb cursor on admin database.
    Returns:
        a list of database names that are sharded
    '''
    sharded_databases = []
    for entry in client["config"].databases.find({"partitioned": True}, {"_id": 1}):
        sharded_databases.append(entry["_id"])
    return sharded_databases


def enable_database_sharding(client, database):
    '''
    Enables sharding on a database
    Args:
        client (cursor): Mongodb cursor on admin database.
    Returns:
        true on success, false on failure
    '''
    s = False
    db = client["admin"].command('enableSharding', database)
    if db:
        s = True
    return s


def any_dbs_to_shard(client, sharded_databases):
    '''
    Return a list of databases that need to have sharding enabled
    sharded_databases - Provided by module
    cluster_sharded_databases - List of sharded dbs from the mongos
    '''
    dbs_to_shard = []
    cluster_sharded_databases = sharded_dbs(client)
    for db in sharded_databases:
        if db not in cluster_sharded_databases:
            dbs_to_shard.append(db)
    return dbs_to_shard


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


# =========================================
# Module execution.
#


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        autosplit=dict(type='bool', required=False, default=None),
        balancer_state=dict(type='str', required=False, choices=["started", "stopped", None], default=None),
        mongos_process=dict(type='str', required=False, default="mongos"),
        shard=dict(type='str', required=True),
        sharded_databases=dict(type="raw", required=False),
        state=dict(type='str', required=False, default='present', choices=['absent', 'present'])
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
    shard = module.params['shard']
    state = module.params['state']
    sharded_databases = module.params['sharded_databases']
    balancer_state = module.params['balancer_state']
    autosplit = module.params['autosplit']
    mongos_process = module.params['mongos_process']

    try:
        connection_params = {
            "host": login_host,
            "port": int(login_port)
        }

        if ssl:
            connection_params = ssl_connection_options(connection_params, module)

        client = MongoClient(**connection_params)

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
            if excep.code == 13:
                if login_user is not None and login_password is not None:
                    client.admin.authenticate(login_user, login_password, source=login_database)
                    check_compatibility(module, client)
                else:
                    raise excep
            else:
                raise excep

        if login_user is None and login_password is None:
            mongocnf_creds = load_mongocnf()
            if mongocnf_creds is not False:
                login_user = mongocnf_creds['user']
                login_password = mongocnf_creds['password']
        elif login_password is None or login_user is None:
            module.fail_json(msg='when supplying login arguments, both login_user and login_password must be provided')

        try:
            client['admin'].command('listDatabases', 1.0)  # if this throws an error we need to authenticate
        except Exception as excep:
            if excep.code == 13:
                if login_user is not None and login_password is not None:
                    client.admin.authenticate(login_user, login_password, source=login_database)
                else:
                    raise excep
            else:
                raise excep

    except Exception as e:
        module.fail_json(msg='unable to connect to database: %s' % to_native(e), exception=traceback.format_exc())

    try:
        if client["admin"].command("serverStatus")["process"] != mongos_process:
            module.fail_json(msg="Process running on {0}:{1} is not a {2}".format(login_host, login_port, mongos_process))
        shard_created = False
        dbs_to_shard = []
        cluster_autosplit = None
        old_balancer_state = None
        new_balancer_state = None
        old_autosplit = None
        new_autosplit = None
        if sharded_databases is not None:
            if isinstance(sharded_databases, str):
                sharded_databases = list(sharded_databases)
            dbs_to_shard = any_dbs_to_shard(client, sharded_databases)
        if balancer_state is not None:
            cluster_balancer_state = get_balancer_state(client)
        if autosplit is not None:
            cluster_autosplit = get_autosplit(client)
        if module.check_mode:
            if state == "present":
                changed = False
                if not shard_find(client, shard) or len(dbs_to_shard) > 0:
                    changed = True
                if (balancer_state is not None
                        and balancer_state != cluster_balancer_state):
                    old_balancer_state = cluster_balancer_state
                    new_balancer_state = balancer_state
                    changed = True
                if (autosplit is not None
                        and autosplit != cluster_autosplit):
                    old_autosplit = cluster_autosplit
                    new_autosplit = autosplit
                    changed = True
            elif state == "absent":
                if not shard_find(client, shard):
                    changed = False
                else:
                    changed = True
        else:
            if state == "present":
                if not shard_find(client, shard):
                    shard_add(client, shard)
                    changed = True
                else:
                    changed = False
                if len(dbs_to_shard) > 0:
                    for db in dbs_to_shard:
                        enable_database_sharding(client, db)
                    changed = True
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
            elif state == "absent":
                if shard_find(client, shard):
                    shard_remove(client, shard)
                    changed = True
                else:
                    changed = False
    except Exception as e:
        action = "add"
        if state == "absent":
            action = "remove"
        module.fail_json(msg='Unable to {0} shard: %s'.format(action) % to_native(e), exception=traceback.format_exc())

    result = {
        "changed": changed,
        "shard": shard,
    }
    if len(dbs_to_shard) > 0:
        result['sharded_enabled'] = dbs_to_shard
    if old_balancer_state is not None:
        result['old_balancer_state'] = old_balancer_state
        result['new_balancer_state'] = new_balancer_state
    if old_autosplit is not None:
        result['old_autosplit'] = old_autosplit
        result['new_autosplit'] = new_autosplit

    module.exit_json(**result)


if __name__ == '__main__':
    main()
