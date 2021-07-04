#!/usr/bin/python

# Copyright: (c) 2021, Rhys Campbell <rhyscampbell@blueiwn.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: mongodb_shard_zone
short_description: Manage Shard Zones.
description:
  - Manage Shard Zones.
  - Add and remove shard zones.
author: Rhys Campbell (@rhysmeister)
version_added: "1.3.0"

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  name:
    description:
      - The name of the zone.
    required: true
    type: str
  namespace:
    description:
      - The namespace the zone is assigned to
      - Should be given in the form database.collection.
    type: str
  ranges:
    description:
      - The ranges assigned to the Zone.
    type: list
    elements: list
  state:
    description:
      - The state of the zone.
    required: false
    type: str
    choices:
      - "present"
      - "absent"
    default: "present"
  mongos_process:
    description:
      - Provide a custom name for the mongos process.
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
- name: Add a shard zone for NYC
  community.mongodb.mongodb_shard_zone:
    name: "NYC"
    namespace: "records.users"
    ranges:
      - [{ zipcode: "10001" }, { zipcode: "10281" }]
      - [{ zipcode: "11201" }, { zipcode: "11240" }]
    state: "present"

- name: Remove all zone ranges
  community.mongodb.mongodb_shard_zone:
    name: "NYC"
    namespace: "records.users"
    state: "absent"

- name: Remove a specific zone range
  community.mongodb.mongodb_shard_zone:
    name: "NYC"
    namespace: "records.users"
    ranges:
      - [{ zipcode: "11201" }, { zipcode: "11240" }]
    state: "absent"
'''

RETURN = r'''
changed:
  description: True when a change has happened
  returned: success
  type: bool
msg:
  description: A short description of what happened.
  returned: failure
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
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    PyMongoVersion,
    PYMONGO_IMP_ERR,
    pymongo_found,
    MongoClient
)

has_ordereddict = False
try:
    from collections import OrderedDict
    has_ordereddict = True
except ImportError as excep:
    try:
        from ordereddict import OrderedDict
        has_ordereddict = True
    except ImportError as excep:
        pass

def zone_range_exists(client, namespace, min, max, tag):
    '''
    Returns true if a particular zone range exists
    @client - MongoDB connection
    @namespace - In the form database.collection
    @min - The min range value
    @max - The max range value
    @tag - The tag or Zone name
    '''
    query = OrderedDict([
        ("_id", OrderedDict([('ns', namespace),
                            ('min', min)]),
        ('ns', namespace),
        ('min', min),
        ('max', max),
        ('tag', tag)])
    status = None
    result = client["config"].tags.find(query)
    if result:
        status = True
    else:
        status = False
    return status


def zone_exists(client, tag):
    '''
    Returns True if the given zone exists
    @client - MongoDB connection
    @tag - The zone to check for
    '''
    status = None
    result = client["config"].shards.find({"tags": tag})
    if result:
        status = True
    else:
        status = False
    return status


def add_zone_range(client, namespace, min, max, tag):
    '''
    Adds a zone range
    @client - MongoDB connection
    @namespace - In the form database.collection
    @min - The min range value
    @max - The max range value
    @tag - The tag or Zone name
    '''
    cmd_doc = OrderedDict([
        ('updateZoneKeyRange', namespace),
        ('min', min),
        ('max', max),
        ('zone', tag),
    ])
    client['admin'].command(cmd_doc)


def remove_zone_range(client, namespace, min, max):
    '''
    Remove a zone range.
    We do this by setting the zone to None
    @client - MongoDB connection
    @namespace - In the form database.collection
    @min - The min range value
    @max - The max range value
    '''
    cmd_doc = OrderedDict([
        ('updateZoneKeyRange', namespace),
        ('min', min),
        ('max', max),
        ('zone', None),
    ])
    client['admin'].command(cmd_doc)


def remove_all_zone_range_by_tag(client, tag):
    result = client["config"].tags.find({"tag": tag})
    for r in result:
        remove_zone_range(client, r['ns'], r['min'], r['max'])


def zone_range_count(client, tag):
    '''
    Returns the count of records that exists for the given tag in config.tags
    '''
    return client['config'].tags.count({"tag": tag})


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        namespace=dict(type='str'),
        ranges=dict(type='list', elements='list'),
        mongos_process=dict(type='str', required=False, default="mongos"),
        state=dict(type='str', default="present", choices=["present", "absent"]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[['login_user', 'login_password']],
        required_if=[("state", "present", ("namespace", "ranges"))]
    )

    if not has_ordereddict:
        module.fail_json(msg='Cannot import OrderedDict class. You can probably install with: pip install ordereddict')

    if not pymongo_found:
        module.fail_json(msg=missing_required_lib('pymongo'),
                         exception=PYMONGO_IMP_ERR)

    login_user = module.params['login_user']
    login_password = module.params['login_password']
    login_database = module.params['login_database']
    login_host = module.params['login_host']
    login_port = module.params['login_port']
    state = module.params['state']
    zone_name = module.params['name']
    namespace = module.params['namespace']
    ranges = module.params['ranges']
    mongos_process = module.params['mongos_process']
    ssl = module.params['ssl']

    if ranges is not None:
        if not isinstance(ranges, list) or not isinstance(ranges[0], list) or not isinstance(ranges[0][0], dict):
            module.fail_json(msg="Provided ranges are invalid {0} {1} {2}".format(str(type(ranges)),
                                                                                  str(type(ranges[0])),
                                                                                  str(type(ranges[0][0]))))

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
        try:
            client['admin'].command('listDatabases', 1.0)  # if this throws an error we need to authenticate
        except Exception as excep:
            if hasattr(excep, 'code') and excep.code == 13:
                if login_user is not None and login_password is not None:
                    client.admin.authenticate(login_user, login_password, source=login_database)
                else:
                    module.fail_json(msg='No credentials to authenticate: %s' % to_native(excep))
            else:
                module.fail_json(msg='Unknown error: %s' % to_native(excep))
    except Exception as excep:
        module.fail_json(msg='unable to connect to database: %s' % to_native(excep), exception=traceback.format_exc())
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

    try:
        if not zone_exists(client, zone_name):
            module.fail_json(msg="The tag {0} does not exist. You need to associate a tag with a shard before using this module. You can do that with the mongodb_shard_tag module.".format(zone_name))
        else:
            # first check if the ranges exist
            range_count = 0
            if state == "present":
                for range in ranges:
                    if zone_range_exists(client, namespace, range[0], range[1], zone_name):
                        range_count += 1
                if range_count == len(ranges):  # All ranges are the same
                    result['changed'] = False
                    result['msg'] = "All Zone Ranges present for {0}".format(zone_name)
                else:
                    for range in ranges:
                        if not module.check_mode:
                            add_zone_range(client, namespace, range[0], range[1], zone_name)
                        result['changed'] = True
                        result['msg'] = "Added zone ranges for {0}".format(zone_name)
            elif state == "absent":
                range_count = zone_range_count(client, zone_name)
                deleted_count = 0
                if range_count > 0 and ranges is None:
                    if not module.check_mode:
                        remove_all_zone_range_by_tag(client, zone_name)
                    deleted_count = range_count
                    result['changed'] = True
                    result['msg'] = "{0} zone ranges for {1} deleted.".format(deleted_count, zone_name)
                elif ranges is not None:
                    for range in ranges:
                        if zone_range_exists(client, namespace, range[0], range[1], zone_name):
                            if not module.check_mode:
                                remove_zone_range(client, namespace, range[0], range[1])
                            deleted_count += 1
                    if deleted_count > 0:
                        result['changed'] = True
                        result['msg'] = "{0} zone ranges for {1} deleted.".format(deleted_count, zone_name)
                    else:
                        result['changed'] = False
                        result['msg'] = "The provided zone ranges are not present for {0}".format(zone_name)
                else:
                    result['changed'] = False
                    result['msg'] = "No zone ranges present for {0}".format(zone_name)
    except Exception as excep:
        module.fail_json(msg="An error occurred: {0}".format(excep))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
