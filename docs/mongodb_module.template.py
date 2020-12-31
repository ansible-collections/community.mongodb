#!/usr/bin/python

# Copyright: (c) <YEAR>, <AUTHOR NAME> <EMAIL>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r'''
---
module: mongodb_module
short_description: A short description about the module.
description:
  - A short description about the module.
  - A description of a module feature.
  - A description of another module feature.
author: <AUTHOR NAME> (<GITHUB HANDLE>)
version_added: "<VERSION ADDED>"

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  option_name:
    description: A short description of the parameter.
    type: <DATA TYPE>
    default: <DEFAULT>

notes:
- Requires the pymongo Python package on the remote host, version 2.4.2+. This
  can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
- pymongo
'''

EXAMPLES = r'''
- name: An example of how to use the module
  community.mongodb.mongodb_module:
    login_host: localhost
    login_user: admin
    login_password: admin
    option_name: 999
'''

RETURN = r'''
mongodb_value:
  description: A description of the value returned.
  returned: <RETURNED WHEN>
  type: <DATA TYPE>
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
    MongoClient
)


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        option_name=dict(type='<DATA TYPE>', default='<VALUE>')
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
    option_name = module.params['option_name']

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

    # main logic of module here
    if module.check_mode:
        pass
    else:
        pass

    module.exit_json(**result)


if __name__ == '__main__':
    main()
