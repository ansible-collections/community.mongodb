#!/usr/bin/python

# Copyright: (c) 2021, Rhys Campbell rhyscampbell@blueiwn.ch
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r'''
---
module: mongodb_monitoring
short_description: Manages the free monitoring feature.
description:
  - Manages the free monitoring feature.
  - Optionally return the monitoring url.
author: Rhys rhyscampbell (rhysmeister)
version_added: "1.3.0"

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  state:
    description: Manage the free monitoring feature.
    type: str
    choices:
      - "started"
      - "stopped"
    default: "started"
  return_url:
    description: When true return the monitoring url if available.
    type: bool
    default: false

notes:
- Requires the pymongo Python package on the remote host, version 2.4.2+. This
  can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
  - pymongo
'''

EXAMPLES = r'''
- name: Enable monitoring
  community.mongodb.mongodb_monitoring:
    state: "started"

- name: Disable monitoring
  community.mongodb.mongodb_monitoring:
    state: "stopped"

- name: Enable monitoring and return the monitoring url
  community.mongodb_monitoring:
    state: "started"
    return_url: "yes"
'''

RETURN = r'''
changed:
  description: Whether the monitoring status changed.
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
url:
  description: The MongoDB instance Monitoring url.
  returned: When requested and available.
  type: str
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import binary_type, text_type
from ansible.module_utils.six.moves import configparser
from ansible.module_utils._text import to_native
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    check_compatibility,
    missing_required_lib,
    load_mongocnf,
    mongodb_common_argument_spec,
    ssl_connection_options,
    PyMongoVersion,
    PYMONGO_IMP_ERR,
    pymongo_found,
    MongoClient,
    LooseVersion
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

def stop_monitoring(client):
    '''
    Stops MongoDB Free Monitoring
    '''
    cmd_doc = OrderedDict([
        ('setFreeMonitoring', 1),
        ('action', 'disable')
        ])
    client['admin'].command(cmd_doc)

def start_monitoring(client):
    '''
    Stops MongoDB Free Monitoring
    '''
    cmd_doc = OrderedDict([
        ('setFreeMonitoring', 1),
        ('action', 'enable')
        ])
    client['admin'].command(cmd_doc)

def get_monitoring_status(client):
    '''
    Gets the state of MongoDB Monitoring.
    N.B. If Monitoring has never been enabled the
    free_monitoring record in admin.system.version
    will not yet exist.
    '''
    monitoring_state = None
    url = None
    result = client["admin"]['system.version'].find_one({"_id": "free_monitoring"})
    if not result:
        monitoring_state = "stopped"
    else:
        url = result["informationalURL"]
        if result["state"] == "enabled":
            monitoring_state = "started"
        else:
            monitoring_state = "stopped"
    return monitoring_state, url


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='started', choices=['started', 'stopped']),
        return_url=dict(type='bool', default=False)
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[['login_user', 'login_password']],
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
    ssl = module.params['ssl']
    state = module.params['state']
    return_url = module.params['return_url']

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
        # If we have auth details use then otherwise attempt without
        if login_user is None and login_password is None:
            mongocnf_creds = load_mongocnf()
            if mongocnf_creds is not False:
                login_user = mongocnf_creds['user']
                login_password = mongocnf_creds['password']
        elif login_password is None or login_user is None:
            module.fail_json(msg="When supplying login arguments, both 'login_user' and 'login_password' must be provided")
    except Exception as e:
        module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(e))

    if login_user is not None and login_password is not None:
        try:
            client.admin.authenticate(login_user, login_password, source=login_database)
        except Exception as excep:
            module.fail_json(msg='Unable to authenticate with MongoDB: %s' % to_native(excep))
    try:
        srv_version = LooseVersion(client.server_info()['version'])
    except Exception as e:
        module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(e))

    # Get driver version::
    driver_version = LooseVersion(PyMongoVersion)

    # Check driver and server version compatibility:
    try:
        check_compatibility(module, srv_version, driver_version)
    except Exception as e:
        module.fail_json(msg='Unable to validate MongoDB driver compatibility: %s' % to_native(e))

    current_monitoring_state, url = get_monitoring_status(client)
    result = {}
    if state == "started":
        if current_monitoring_state == "started":
            result['changed'] = False
            result['msg'] = "Free monitoring is already started"
        else:
            if module.check_mode is False:
                start_monitoring(client)
            result['changed'] = True
            result['msg'] = "Free monitoring has been started"
    else:
        if current_monitoring_state == "started":
            if module.check_mode is False:
                stop_monitoring(client)
            result['changed'] = True
            result['msg'] = "Free monitoring has been stopped"
        else:
            result['changed'] = False
            result['msg'] = "Free monitoring is already stopped"

    if return_url and url:
        result['url'] = url

    module.exit_json(**result)


if __name__ == '__main__':
    main()
