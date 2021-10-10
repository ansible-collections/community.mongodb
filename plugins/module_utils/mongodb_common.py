from __future__ import absolute_import, division, print_function
__metaclass__ = type
from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible.module_utils.six.moves import configparser
from ansible.module_utils._text import to_native
from distutils.version import LooseVersion
import traceback
import os
import ssl as ssl_lib

MongoClient = None
PYMONGO_IMP_ERR = None
pymongo_found = None
PyMongoVersion = None
ConnectionFailure = None
OperationFailure = None

try:
    from pymongo.errors import ConnectionFailure
    from pymongo.errors import OperationFailure
    from pymongo import version as PyMongoVersion
    from pymongo import MongoClient
    pymongo_found = True
except ImportError:
    PYMONGO_IMP_ERR = traceback.format_exc()
    pymongo_found = False


def check_compatibility(module, srv_version, driver_version):
    """Check the compatibility between the driver and the database.

    See: https://docs.mongodb.com/ecosystem/drivers/driver-compatibility-reference/#python-driver-compatibility

    Args:
        module: Ansible module.
        srv_version (LooseVersion): MongoDB server version.
        driver_version (LooseVersion): Pymongo version.
    """
    msg = 'pymongo driver version and MongoDB version are incompatible: '

    if srv_version >= LooseVersion('5.0') and driver_version < LooseVersion('3.12'):
        msg += 'you must use pymongo 3.12+ with MongoDB >= 5.0'
        module.fail_json(msg=msg)
    elif srv_version >= LooseVersion('4.4') and driver_version < LooseVersion('3.11'):
        msg += 'you must use pymongo 3.11+ with MongoDB >= 4.4'
        module.fail_json(msg=msg)
    elif srv_version >= LooseVersion('4.2') and driver_version < LooseVersion('3.9'):
        msg += 'you must use pymongo 3.9+ with MongoDB >= 4.2'
        module.fail_json(msg=msg)
    elif srv_version >= LooseVersion('4.0') and driver_version < LooseVersion('3.7'):
        msg += 'you must use pymongo 3.7+ with MongoDB >= 4.0'
        module.fail_json(msg=msg)
    elif srv_version >= LooseVersion('3.6') and driver_version < LooseVersion('3.6'):
        msg += 'you must use pymongo 3.6+ with MongoDB >= 3.6'
        module.fail_json(msg=msg)
    elif srv_version >= LooseVersion('3.4') and driver_version < LooseVersion('3.4'):
        msg += 'you must use pymongo 3.4+ with MongoDB >= 3.4'
        module.fail_json(msg=msg)
    elif srv_version >= LooseVersion('3.2') and driver_version < LooseVersion('3.2'):
        msg += 'you must use pymongo 3.2+ with MongoDB >= 3.2'
        module.fail_json(msg=msg)
    elif srv_version >= LooseVersion('3.0') and driver_version <= LooseVersion('2.8'):
        msg += 'you must use pymongo 2.8+ with MongoDB 3.0'
        module.fail_json(msg=msg)
    elif srv_version >= LooseVersion('2.6') and driver_version <= LooseVersion('2.7'):
        msg += 'you must use pymongo 2.7+ with MongoDB 2.6'
        module.fail_json(msg=msg)


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


def index_exists(client, database, collection, index_name):
    """
    Returns true if an index on the collection exists with the given name
    @client: MongoDB connection.
    @database: MongoDB Database.
    @collection: MongoDB collection.
    @index_name: The index name.
    """
    exists = False
    indexes = client[database][collection].list_indexes()
    for index in indexes:
        if index["name"] == index_name:
            exists = True
    return exists


def create_index(client, database, collection, keys, options):
    """
    Creates an index on the given collection
    @client: MongoDB connection.
    @database: MongoDB Database - str.
    @collection: MongoDB collection - str.
    @keys: Specification of index - dict.
    """
    client[database][collection].create_index(list(keys.items()),
                                              **options)


def drop_index(client, database, collection, index_name):
    client[database][collection].drop_index(index_name)


def member_state(client):
    """Check if a replicaset exists.

    Args:
        client (cursor): Mongodb cursor on admin database.

    Returns:
        str: member state i.e. PRIMARY, SECONDARY
    """
    state = None
    doc = client['admin'].command('replSetGetStatus')
    for member in doc["members"]:
        if "self" in member.keys():
            state = str(member['stateStr'])
    return state


def mongodb_common_argument_spec(ssl_options=True):
    """
    Returns a dict containing common options shared across the MongoDB modules.
    """
    options = dict(
        login_user=dict(type='str', required=False),
        login_password=dict(type='str', required=False, no_log=True),
        login_database=dict(type='str', required=False, default='admin'),
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=27017),
    )
    ssl_options_dict = dict(
        ssl=dict(type='bool', required=False, default=False),
        ssl_cert_reqs=dict(type='str',
                           required=False,
                           default='CERT_REQUIRED',
                           choices=['CERT_NONE',
                                    'CERT_OPTIONAL',
                                    'CERT_REQUIRED']),
        ssl_ca_certs=dict(type='str', default=None),
        ssl_crlfile=dict(type='str', default=None),
        ssl_certfile=dict(type='str', default=None),
        ssl_keyfile=dict(type='str', default=None, no_log=True),
        ssl_pem_passphrase=dict(type='str', default=None, no_log=True),
        auth_mechanism=dict(type='str',
                            required=False,
                            default=None,
                            choices=['SCRAM-SHA-256',
                                     'SCRAM-SHA-1',
                                     'MONGODB-X509',
                                     'GSSAPI',
                                     'PLAIN']),
        connection_options=dict(type='list',
                                elements='raw',
                                default=None)
    )
    if ssl_options:
        options.update(ssl_options_dict)
    return options


def add_option_if_not_none(param_name, module, connection_params):
    '''
    @param_name - The parameter name to check
    @module - The ansible module object
    @connection_params - Dict containing the connection params
    '''
    if module.params[param_name] is not None:
        connection_params[param_name] = module.params[param_name]
    return connection_params


def ssl_connection_options(connection_params, module):
    connection_params['ssl'] = True
    if module.params['ssl_cert_reqs'] is not None:
        connection_params['ssl_cert_reqs'] = getattr(ssl_lib, module.params['ssl_cert_reqs'])
    connection_params = add_option_if_not_none('ssl_ca_certs', module, connection_params)
    connection_params = add_option_if_not_none('ssl_crlfile', module, connection_params)
    connection_params = add_option_if_not_none('ssl_certfile', module, connection_params)
    connection_params = add_option_if_not_none('ssl_keyfile', module, connection_params)
    connection_params = add_option_if_not_none('ssl_pem_passphrase', module, connection_params)
    if module.params['auth_mechanism'] is not None:
        connection_params['authMechanism'] = module.params['auth_mechanism']
    if module.params['connection_options'] is not None:
        for item in module.params['connection_options']:
            if isinstance(item, dict):
                for key, value in item.items():
                    connection_params[key] = value
            elif isinstance(item, str) and "=" in item:
                connection_params[item.split('=')[0]] = item.split('=')[1]
            else:
                raise ValueError("Invalid value supplied in connection_options: {0} .".format(str(item)))
    return connection_params


def check_srv_version(module, client):
    try:
        srv_version = LooseVersion(client.server_info()['version'])
    except Exception as excep:
        module.fail_json(msg='Unable to get MongoDB server version: %s' % to_native(excep))
    return srv_version


def check_driver_compatibility(module, client, srv_version):
    try:
        # Get driver version::
        driver_version = LooseVersion(PyMongoVersion)
        # Check driver and server version compatibility:
        check_compatibility(module, srv_version, driver_version)
    except Exception as excep:
        module.fail_json(msg='Unable to check driver compatibility: %s' % to_native(excep))


def mongo_auth(module, client):
    """
    TODO: This function was extracted from code form the mongodb_replicaset module.
    We should refactor other modules to use this where appropriate.
    @module - The calling Ansible module
    @client - The MongoDB connection object
    """
    login_user = module.params['login_user']
    login_password = module.params['login_password']
    login_database = module.params['login_database']
    # If we have auth details use then otherwise attempt without
    if login_user is None and login_password is None:
        mongocnf_creds = load_mongocnf()
        if mongocnf_creds is not False:
            login_user = mongocnf_creds['user']
            login_password = mongocnf_creds['password']
    elif login_password is None or login_user is None:
        module.fail_json(msg="When supplying login arguments, both 'login_user' and 'login_password' must be provided")

    if 'create_for_localhost_exception' not in module.params:
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
            module.fail_json(msg='unable to connect to database: %s' % to_native(excep))
        # Get server version:
        srv_version = check_srv_version(module, client)
        check_driver_compatibility(module, client, srv_version)
    else:  # this is the mongodb_user module
        if login_user is not None and login_password is not None:
            client.admin.authenticate(login_user, login_password, source=login_database)
            # Get server version:
            srv_version = check_srv_version(module, client)
            check_driver_compatibility(module, client, srv_version)
        elif LooseVersion(PyMongoVersion) >= LooseVersion('3.0'):
            if module.params['database'] != "admin":
                module.fail_json(msg='The localhost login exception only allows the first admin account to be created')
            # else: this has to be the first admin user added
    return client


def member_dicts_different(conf, member_config):
    '''
    Returns if there is a difference in the replicaset configuration that we care about
    @con - The current MongoDB Replicaset configure document
    @member_config - The member dict config provided by the module. List of dicts
    '''
    current_member_config = conf['members']
    member_config_defaults = {
        "arbiterOnly": False,
        "buildIndexes": True,
        "hidden": False,
        "priority": {"nonarbiter": 1.0, "arbiter": 0},
        "tags": {},
        "secondardDelaySecs": 0,
        "votes": 1
    }
    different = False
    msg = "None"
    current_member_hosts = []
    for member in current_member_config:
        current_member_hosts.append(member['host'])
    member_config_hosts = []
    for member in member_config:
        if ':' not in member['host']:  # no port supplied
            member_config_hosts.append(member['host'] + ":27017")
        else:
            member_config_hosts.append(member['host'])
    if sorted(current_member_hosts) != sorted(member_config_hosts):  # compare if members are the same
        different = True
        msg = "hosts different"
    else:  # Compare dict key to see if votes, tags etc have changed. We also default value if key is not specified
        for host in current_member_hosts:
            member_index = next((index for (index, d) in enumerate(current_member_config) if d["host"] == host), None)
            new_member_index = next((index for (index, d) in enumerate(member_config) if d["host"] == host), None)
            for config_item in member_config_defaults:
                if config_item != "priority":
                    if current_member_config[member_index].get(config_item, member_config_defaults[config_item]) != \
                            member_config[new_member_index].get(config_item, member_config_defaults[config_item]):
                        different = True
                        msg = "var different {0} {1} {2}".format(config_item,
                                                                 current_member_config[member_index].get(config_item, member_config_defaults[config_item]),
                                                                 member_config[new_member_index].get(config_item, member_config_defaults[config_item]))
                        break
                else:  # priority a special case
                    role = "nonarbiter"
                    if current_member_config[member_index]["arbiterOnly"]:
                        role = "arbiter"
                        if current_member_config[member_index][config_item] != \
                                member_config[new_member_index].get(config_item, member_config_defaults[config_item][role]):
                            different = True
                            msg = "var different {0}".format(config_item)
                            break
    return different  # , msg


def lists_are_different(list1, list2):
    diff = False
    if sorted(list1) != sorted(list2):
        diff = True
    return diff
