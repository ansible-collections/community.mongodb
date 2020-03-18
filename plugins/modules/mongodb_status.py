#!/usr/bin/python

# Copyright: (c) 2018, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: mongodb_status
short_description: Validates the status of the cluster.
description:
- Validates the status of the cluster.
- The module expects all replicaset nodes to be PRIMARY, SECONDARY or ARBITER.
- Will wait until a timeout for the replicaset state to converge if required.
author: Rhys Campbell (@rhysmeister)
version_added: "2.9"
options:
  login_user:
    description:
    - The username to authenticate with.
    type: str
  login_password:
    description:
    - The password to authenticate with.
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
  replica_set:
    description:
    - Replicaset name.
    type: str
    default: rs0
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
  poll:
    description:
      - The maximum number of times query for the replicaset status.
    type: int
    default: 1
  interval:
    description:
      - The number of seconds to wait between poll executions.
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
  mongodb_status:
    replicaset: rs0
  when: ansible_hostname == "mongodb1"

- name: Wait for the replicaset rs0 to converge, check 5 times, 10 second interval
  mongodb_status:
    replicaset: rs0
    poll: 5
    interval: 10
  when: ansible_hostname == "mongodb1"
'''

RETURN = r'''
failed:
  description: If the mnodule had failed or not.
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

try:
    from pymongo.errors import ConnectionFailure
    from pymongo.errors import OperationFailure
    from pymongo import version as PyMongoVersion
    from pymongo import MongoClient
    HAS_PYMONGO = True
except ImportError:
    try:  # for older PyMongo 2.2
        from pymongo import Connection as MongoClient
        HAS_PYMONGO = True
    except ImportError:
        HAS_PYMONGO = False

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import binary_type, text_type
from ansible.module_utils.six.moves import configparser
from ansible.module_utils._text import to_native


# =========================================
# MongoDB module specific support methods.
#

def check_compatibility(module, client):
    """Check the compatibility between the driver and the database.

       See: https://docs.mongodb.com/ecosystem/drivers/driver-compatibility-reference/#python-driver-compatibility

    Args:
        module: Ansible module.
        client (cursor): Mongodb cursor on admin database.
    """
    loose_srv_version = LooseVersion(client.server_info()['version'])
    loose_driver_version = LooseVersion(PyMongoVersion)

    if loose_srv_version >= LooseVersion('3.2') and loose_driver_version < LooseVersion('3.2'):
        module.fail_json(msg=' (Note: you must use pymongo 3.2+ with MongoDB >= 3.2)')

    elif loose_srv_version >= LooseVersion('3.0') and loose_driver_version <= LooseVersion('2.8'):
        module.fail_json(msg=' (Note: you must use pymongo 2.8+ with MongoDB 3.0)')

    elif loose_srv_version >= LooseVersion('2.6') and loose_driver_version <= LooseVersion('2.7'):
        module.fail_json(msg=' (Note: you must use pymongo 2.7+ with MongoDB 2.6)')

    elif LooseVersion(PyMongoVersion) <= LooseVersion('2.5'):
        module.fail_json(msg=' (Note: you must be on mongodb 2.4+ and pymongo 2.5+ to use the roles param)')


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
    if len(statuses) % 2 == 1:  # Odd number of servers is good
        if (statuses.count("PRIMARY") == 1
                and ((statuses.count("SECONDARY")
                     + statuses.count("ARBITER")) % 2 == 0)):
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


def load_mongocnf():
    config = configparser.RawConfigParser()
    mongocnf = os.path.expanduser('~/.mongodb.cnf')

    try:
        config.readfp(open(mongocnf))
    except (configparser.NoOptionError, IOError):
        return False

    creds = dict(
        user=config.get('client', 'user'),
        password=config.get('client', 'pass')
    )

    return creds


# =========================================
# Module execution.
#


def main():
    module = AnsibleModule(
        argument_spec=dict(
            login_user=dict(type='str'),
            login_password=dict(type='str', no_log=True),
            login_database=dict(type='str', default="admin"),
            login_host=dict(type='str', default="localhost"),
            login_port=dict(type='int', default=27017),
            replica_set=dict(type='str', default="rs0"),
            ssl=dict(type='bool', default=False),
            ssl_cert_reqs=dict(type='str', default='CERT_REQUIRED', choices=['CERT_NONE', 'CERT_OPTIONAL', 'CERT_REQUIRED']),
            poll=dict(type='int', default=1),
            interval=dict(type='int', default=30)),
        supports_check_mode=False)

    if HAS_PYMONGO is False:
        module.fail_json(msg='the python pymongo module is required')

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
        connection_params["ssl"] = ssl
        connection_params["ssl_cert_reqs"] = getattr(ssl_lib, module.params['ssl_cert_reqs'])

    try:
        client = MongoClient(**connection_params)
    except Exception as e:
        module.fail_json(msg='Unable to connect to database: %s' % to_native(e))

    try:
        check_compatibility(module, client)
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
