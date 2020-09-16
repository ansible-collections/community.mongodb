#!/usr/bin/python

# Copyright: (c) 2018, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_replicaset
short_description: Initialises a MongoDB replicaset.
description:
  - Initialises a MongoDB replicaset in a new deployment.
  - Validates the replicaset name for existing deployments.
  - Advanced replicaset member configuration possible (see examples).
author: Rhys Campbell (@rhysmeister)
version_added: "1.0.0"

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  replica_set:
    description:
    - Replicaset name.
    type: str
    default: rs0
  members:
    description:
    - Yaml list consisting of the replicaset members.
    - Csv string will also be accepted i.e. mongodb1:27017,mongodb2:27017,mongodb3:27017.
    - A dictionary can also be used to specify advanced replicaset member options.
    - If a port number is not provided then 27017 is assumed.
    type: list
    elements: raw
  validate:
    description:
    - Performs some basic validation on the provided replicaset config.
    type: bool
    default: yes
  arbiter_at_index:
    description:
    - Identifies the position of the member in the array that is an arbiter.
    type: int
  chaining_allowed:
    description:
    - When I(settings.chaining_allowed=true), the replicaset allows secondary members to replicate from other
      secondary members.
    - When I(settings.chaining_allowed=false), secondaries can replicate only from the primary.
    type: bool
    default: yes
  heartbeat_timeout_secs:
    description:
    - Number of seconds that the replicaset members wait for a successful heartbeat from each other.
    - If a member does not respond in time, other members mark the delinquent member as inaccessible.
    - The setting only applies when using I(protocol_version=0). When using I(protocol_version=1) the relevant
      setting is I(settings.election_timeout_millis).
    type: int
    default: 10
  election_timeout_millis:
    description:
    - The time limit in milliseconds for detecting when a replicaset's primary is unreachable.
    type: int
    default: 10000
  protocol_version:
    description: Version of the replicaset election protocol.
    type: int
    choices: [ 0, 1 ]
    default: 1
notes:
- Requires the pymongo Python package on the remote host, version 2.4.2+. This
  can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
- pymongo
'''

EXAMPLES = r'''
# Create a replicaset called 'rs0' with the 3 provided members
- name: Ensure replicaset rs0 exists
  community.mongodb.mongodb_replicaset:
    login_host: localhost
    login_user: admin
    login_password: admin
    replica_set: rs0
    members:
    - mongodb1:27017
    - mongodb2:27017
    - mongodb3:27017
  when: groups.mongod.index(inventory_hostname) == 0

# Create two single-node replicasets on the localhost for testing
- name: Ensure replicaset rs0 exists
  community.mongodb.mongodb_replicaset:
    login_host: localhost
    login_port: 3001
    login_user: admin
    login_password: secret
    login_database: admin
    replica_set: rs0
    members: localhost:3001
    validate: no

- name: Ensure replicaset rs1 exists
  community.mongodb.mongodb_replicaset:
    login_host: localhost
    login_port: 3002
    login_user: admin
    login_password: secret
    login_database: admin
    replica_set: rs1
    members: localhost:3002
    validate: no

- name: Create a replicaset and use a custom priority for each member
  community.mongodb.mongodb_replicaset:
    login_host: localhost
    login_user: admin
    login_password: admin
    replica_set: rs0
    members:
    - host: "localhost:3001"
      priority: 1
    - host: "localhost:3002"
      priority: 0.5
    - host: "localhost:3003"
      priority: 0.5
  when: groups.mongod.index(inventory_hostname) == 0

- name: Create replicaset rs1 with options and member tags
  community.mongodb.mongodb_replicaset:
    login_host: localhost
    login_port: 3001
    login_database: admin
    replica_set: rs1
    members:
    - host: "localhost:3001"
      priority: 1
      tags:
        dc: "east"
        usage: "production"
    - host: "localhost:3002"
      priority: 1
      tags:
        dc: "east"
        usage: "production"
    - host: "localhost:3003"
      priority: 0
      hidden: true
      slaveDelay: 3600
      tags:
        dc: "west"
        usage: "reporting"
'''

RETURN = r'''
mongodb_replicaset:
  description: The name of the replicaset that has been created.
  returned: success
  type: str
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
    ssl_connection_options
)
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import PyMongoVersion, PYMONGO_IMP_ERR, pymongo_found, MongoClient


def replicaset_find(client):
    """Check if a replicaset exists.

    Args:
        client (cursor): Mongodb cursor on admin database.

    Returns:
        dict: when user exists, False otherwise.
    """
    doc = client['admin'].command('isMaster')
    if 'setName' in doc.keys():
        return str(doc['setName'])
    return False


def replicaset_add(module, client, replica_set, members, arbiter_at_index, protocol_version,
                   chaining_allowed, heartbeat_timeout_secs, election_timeout_millis):

    try:
        from collections import OrderedDict
    except ImportError as excep:
        try:
            from ordereddict import OrderedDict
        except ImportError as excep:
            module.fail_json(msg='Cannot import OrderedDict class. You can probably install with: pip install ordereddict: %s'
                             % to_native(excep))

    members_dict_list = []
    index = 0
    settings = {
        "chainingAllowed": bool(chaining_allowed),
    }
    if protocol_version == 0:
        settings['heartbeatTimeoutSecs'] = heartbeat_timeout_secs
    else:
        settings['electionTimeoutMillis'] = election_timeout_millis
    for member in members:
        if isinstance(member, str):
            if ':' not in member:  # No port supplied. Assume 27017
                member += ":27017"
            members_dict_list.append(OrderedDict([("_id", int(index)), ("host", member)]))
            if index == arbiter_at_index:
                members_dict_list[index]['arbiterOnly'] = True
            index += 1
        elif isinstance(member, dict):
            hostname = member["host"]
            if ':' not in hostname:
                hostname += ":27017"
            members_dict_list.append(OrderedDict([("_id", int(index)), ("host", hostname)]))
            for key in list(member.keys()):
                if key != "host":
                    members_dict_list[index][key] = member[key]
            if index == arbiter_at_index:
                members_dict_list[index]['arbiterOnly'] = True
            index += 1
        else:
            raise ValueError("member should be a str or dict. Instead found: {0}".format(str(type(members))))

    conf = OrderedDict([("_id", replica_set),
                        ("protocolVersion", protocol_version),
                        ("members", members_dict_list),
                        ("settings", settings)])
    try:
        client["admin"].command('replSetInitiate', conf)
    except Exception as excep:
        raise Exception("Some problem {0} | {1}".format(str(excep), str(conf)))


def replicaset_remove(module, client, replica_set):
    raise NotImplementedError
    # exists = replicaset_find(client, replica_set)
    # if exists:
    #    if module.check_mode:
    #        module.exit_json(changed=True, replica_set=replica_set)
    #    db = client[db_name]
    #    db.remove_user(replica_set)
    # else:
    #    module.exit_json(changed=False, user=user)


# =========================================
# Module execution.
#


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        arbiter_at_index=dict(type='int'),
        chaining_allowed=dict(type='bool', default=True),
        election_timeout_millis=dict(type='int', default=10000),
        heartbeat_timeout_secs=dict(type='int', default=10),
        members=dict(type='list', elements='raw'),
        protocol_version=dict(type='int', default=1, choices=[0, 1]),
        replica_set=dict(type='str', default="rs0"),
        validate=dict(type='bool', default=True)
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
    replica_set = module.params['replica_set']
    members = module.params['members']
    arbiter_at_index = module.params['arbiter_at_index']
    validate = module.params['validate']
    ssl = module.params['ssl']
    protocol_version = module.params['protocol_version']
    chaining_allowed = module.params['chaining_allowed']
    heartbeat_timeout_secs = module.params['heartbeat_timeout_secs']
    election_timeout_millis = module.params['election_timeout_millis']

    if validate:
        if len(members) <= 2 or len(members) % 2 == 0:
            module.fail_json(msg="MongoDB Replicaset validation failed. Invalid number of replicaset members.")
        if arbiter_at_index is not None and len(members) - 1 < arbiter_at_index:
            module.fail_json(msg="MongoDB Replicaset validation failed. Invalid arbiter index.")

    result = dict(
        changed=False,
        replica_set=replica_set,
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
        rs = replicaset_find(client)
    except Exception as e:
        module.fail_json(msg='Unable to connect to query replicaset: %s' % to_native(e))

    if isinstance(rs, str):
        if replica_set == rs:
            result['changed'] = False
            result['replica_set'] = rs
            module.exit_json(**result)
        else:
            module.fail_json(msg="The replica_set name of {0} does not match the expected: {1}".format(rs, replica_set))
    else:  # replicaset does not exit

        # Some validation stuff
        if len(replica_set) == 0:
            module.fail_json(msg="Parameter replica_set must not be an empty string")

        if module.check_mode is False:
            try:
                # If we have auth details use then otherwise attempt without
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
                        except Exception as e:
                            module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(e))

                        # Get driver version::
                        driver_version = LooseVersion(PyMongoVersion)
                        # Check driver and server version compatibility:
                        check_compatibility(module, srv_version, driver_version)
                    except Exception as excep:
                        module.fail_json(msg='Unable to authenticate with MongoDB: %s' % to_native(excep))
                replicaset_add(module, client, replica_set, members,
                               arbiter_at_index, protocol_version,
                               chaining_allowed, heartbeat_timeout_secs,
                               election_timeout_millis)
                result['changed'] = True
            except Exception as e:
                module.fail_json(msg='Unable to create replica_set: %s' % to_native(e))
        else:
            result['changed'] = True

        module.exit_json(**result)


if __name__ == '__main__':
    main()
