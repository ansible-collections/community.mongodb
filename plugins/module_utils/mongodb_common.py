from __future__ import absolute_import, division, print_function
__metaclass__ = type
from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible.module_utils.six.moves import configparser
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

    if srv_version >= LooseVersion('4.2') and driver_version < LooseVersion('3.9'):
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


def mongodb_common_argument_spec():
    """
    Returns a dict containing common options shared across the MongoDB modules.
    """
    return dict(
        login_user=dict(type='str', required=False),
        login_password=dict(type='str', required=False, no_log=True),
        login_database=dict(type='str', required=False, default='admin'),
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=27017),
        ssl=dict(type='bool', required=False, default=False),
        ssl_cert_reqs=dict(type='str', required=False, default='CERT_REQUIRED',
                           choices=['CERT_NONE',
                                    'CERT_OPTIONAL',
                                    'CERT_REQUIRED']),
        ssl_ca_certs=dict(type='str', default=None),
        ssl_crlfile=dict(type='str', default=None),
        ssl_certfile=dict(type='str', default=None),
        ssl_keyfile=dict(type='str', default=None),
        ssl_pem_passphrase=dict(type='str', default=None, no_log=True),
    )


def ssl_connection_options(connection_params, module):
    connection_params['ssl'] = True
    connection_params['ssl_cert_reqs'] = getattr(ssl_lib, module.params['ssl_cert_reqs'])
    connection_params['ssl_ca_certs'] = module.params['ssl_ca_certs']
    connection_params['ssl_crlfile'] = module.params['ssl_crlfile']
    connection_params['ssl_certfile'] = module.params['ssl_certfile']
    connection_params['ssl_keyfile'] = module.params['ssl_keyfile']
    connection_params['ssl_pem_passphrase'] = module.params['ssl_pem_passphrase']
    return connection_params
