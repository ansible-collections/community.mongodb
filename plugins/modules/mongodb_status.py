#!/usr/bin/python

# Copyright: (c) 2018, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_status
short_description: Validates the status of the cluster.
description:
  - Validates the status of the cluster.
  - The module expects all replicaset nodes to be PRIMARY, SECONDARY or ARBITER.
  - Will wait until a timeout for the replicaset state to converge if required.
  - Can also be used to lookup the current PRIMARY member (see examples).
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
  poll:
    description:
      - The maximum number of times to query for the replicaset status before the set converges or we fail.
    type: int
    default: 1
  interval:
    description:
      - The number of seconds to wait between polling executions.
    type: int
    default: 30
notes:
- Requires the pymongo Python package on the remote host, version 2.4.2+. This
  can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
- pymongo
'''

EXAMPLES = r'''
- name: Check replicaset is healthy, fail if not after first attempt
  community.mongodb.mongodb_status:
    replica_set: rs0
  when: ansible_hostname == "mongodb1"

- name: Wait for the replicaset rs0 to converge, check 5 times, 10 second interval between checks
  community.mongodb.mongodb_status:
    replica_set: rs0
    poll: 5
    interval: 10
  when: ansible_hostname == "mongodb1"

# Get the replicaset status and then lookup the primary's hostname and save to a variable
- name: Ensure replicaset is stable before beginning
  community.mongodb.mongodb_status:
    login_user: "{{ admin_user }}"
    login_password: "{{ admin_user_password }}"
    poll: 3
    interval: 10
  register: rs

- name: Lookup PRIMARY replicaset member
  set_fact:
    primary: "{{ item.key.split('.')[0] }}"
  loop: "{{ lookup('dict', rs.replicaset) }}"
  when: "'PRIMARY' in item.value"
'''

RETURN = r'''
failed:
  description: If the mnodule had failed or not.
  returned: always
  type: bool
iterations:
  description: Number of times the module has queried the replicaset status.
  returned: always
  type: int
msg:
  description: Status message.
  returned: always
  type: str
replicaset:
  description: The last queried status of all the members of the replicaset if obtainable.
  returned: always
  type: dict
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


def replicaset_status(client, module):
    """
    Return the replicaset status document from MongoDB
    # https://docs.mongodb.com/manual/reference/command/replSetGetStatus/
    """
    rs = client.admin.command('replSetGetStatus')
    return rs


def replicaset_members(replicaset_document):
    """
    Returns the members section of the MongoDB replicaset document
    """
    return replicaset_document["members"]


def replicaset_friendly_document(members_document):
    """
    Returns a version of the members document with
    only the info this module requires: name & stateStr
    """
    friendly_document = {}

    for member in members_document:
        friendly_document[member["name"]] = member["stateStr"]
    return friendly_document


def replicaset_statuses(members_document, module):
    """
    Return a list of the statuses
    """
    statuses = []
    for member in members_document:
        statuses.append(members_document[member])
    return statuses


def replicaset_good(statuses, module):
    """
    Returns true if the replicaset is in a "good" condition.
    Good is defined as an odd number of servers >= 3, with
    max one primary, and any even amount of
    secondary and arbiter servers
    """
    module.debug(msg=str(statuses))
    msg = "Unset"
    status = None
    valid_statuses = ["PRIMARY", "SECONDARY", "ARBITER"]
    # Odd number of servers is good
    if len(statuses) % 2 == 1:
        if (statuses.count("PRIMARY") == 1
            and ((statuses.count("SECONDARY")
                  + statuses.count("ARBITER")) % 2 == 0)
                and len(set(statuses) - set(valid_statuses)) == 0):
            status = True
            msg = "replicaset is in a converged state"
        else:
            status = False
            msg = "replicaset is not currently in a converged state"
    else:
        msg = "Even number of servers currently in replicaset."
        status = False
    return status, msg


def replicaset_status_poll(client, module):
    """
    client - MongoDB Client
    poll - Number of times to poll
    interval - interval between polling attempts
    """
    iterations = 0  # How many times we have queried the cluster
    failures = 0  # Number of failures when querying the replicaset
    poll = module.params['poll']
    interval = module.params['interval']
    status = None
    return_doc = {}

    while iterations < poll:
        try:
            iterations += 1
            replicaset_document = replicaset_status(client, module)
            members = replicaset_members(replicaset_document)
            friendly_document = replicaset_friendly_document(members)
            statuses = replicaset_statuses(friendly_document, module)
            status, msg = replicaset_good(statuses, module)
            if status:  # replicaset looks good
                return_doc = {"failures": failures,
                              "poll": poll,
                              "iterations": iterations,
                              "msg": msg,
                              "replicaset": friendly_document}
                break
            else:
                failures += 1
                return_doc = {"failures": failures,
                              "poll": poll,
                              "iterations": iterations,
                              "msg": msg,
                              "replicaset": friendly_document,
                              "failed": True}
                if iterations == poll:
                    break
                else:
                    time.sleep(interval)
        except Exception as e:
            failures += 1
            return_doc['failed'] = True
            return_doc['msg'] = str(e)
            status = False
            if iterations == poll:
                break
            else:
                time.sleep(interval)

    return_doc['failures'] = failures
    return status, return_doc['msg'], return_doc


# =========================================
# Module execution.
#


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        interval=dict(type='int', default=30),
        poll=dict(type='int', default=1),
        replica_set=dict(type='str', default="rs0"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False,
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
    ssl = module.params['ssl']
    poll = module.params['poll']
    interval = module.params['interval']

    result = dict(
        failed=False,
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
        if excep.code != 13:
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

    if len(replica_set) == 0:
        module.fail_json(msg="Parameter 'replica_set' must not be an empty string")

    try:
        status, msg, return_doc = replicaset_status_poll(client, module)  # Sort out the return doc
        replicaset = return_doc['replicaset']
        iterations = return_doc['iterations']
    except Exception as e:
        module.fail_json(msg='Unable to query replica_set info: %s' % str(e))

    if status is False:
        module.fail_json(msg=msg, replicaset=replicaset, iterations=iterations)
    else:
        module.exit_json(msg=msg, replicaset=replicaset, iterations=iterations)


if __name__ == '__main__':
    main()
