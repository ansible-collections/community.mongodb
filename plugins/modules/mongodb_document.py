#!/usr/bin/python

# Copyright: (c) 2020, Rhys Campbell <rhys.james.campbell@googlemail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: mongodb_document
short_description: Inserts or deletes a document in a MongoDB collection.
description: >
  - Inserts or deletes a document in a MongoDB collection.
  - Provides an upsert option.
  - Optionally ensure an index exists.
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
  database:
    description:
      - The database to insert the document into.
    type: str
    default: "test"
  collection:
    description:
      - The collection to insert the document into.
    type: str
    required: true
  document:
    description:
      - The document to insert.
    type: raw
    required: true
  upsert:
    description:
      - Activate the upsert option.
    type: bool
    default: false
  index:
    description:
      - Specify an index to create.
    type: raw
  index_name:
    description:
      - Name of the index to create.
    type: str
    default: idx_mongodb_document
  state:
    description:
      - Indicates whether the document should be absent or present.
    required: false
    type: str
    default: present
    choices: [absent, present]
notes:
- Requires the pymongo Python package on the remote host, version 2.4.2+. This
  can be installed using pip or the OS package manager. @see U(http://api.mongodb.org/python/current/installation.html)
requirements:
- pymongo
'''

EXAMPLES = r'''
- name: Insert a document into the orders collection
  mongodb_document:
    database: "test"
    collection: "orders"
    document:
      "_id": 10
      "order_id": "XXX"
      customer_id: 1

- name: Insert a document into the customer collection and ensure the index exists
  mongodb_document:
    database: "crm"
    collection: "customers"
    document:
      name: "Rhys Campbell"
      address: "Nirgendwostrasse 99"
      city: "Zürich"
      postcode: "9999"
    index:
      name: -1
      city: 1
    index_name: idx_name_city

- name: Delete a document from the customer collection
  mongodb_document:
    database: "crm"
    collection: "customers"
    document:
      name: "ACME Ltd"
      state: absent
'''

RETURN = r'''
failed:
  description: If the module had failed or not.
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
    import bson.objectid
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


def insert_document(client, database, collection, document):
    """
    Insert a document into the specified collection
    @client: MongoDB connection.
    @database: MongoDB Database.
    @collection: MongoDB collection.
    @document: The MongoDB document to insert.
    """
    status = None
    inserted_id = None
    if "_id" not in document.keys():
        result = client[database][collection].insert_one(document)
        inserted_id = str(bson.objectid.ObjectId(result.inserted_id))
        status = True
    else:
        result = client[database][collection].update_one({"_id": document["_id"]},
                                                         document,
                                                         upsert=True)
        if result.modified_count == 0:
            status = False
        elif result.modified_count == 1:
            status = True
    return status, inserted_id


def delete_document(client, database, collection, document):
    """
    Insert a document into the specified collection
    @client: MongoDB connection.
    @database: MongoDB Database.
    @collection: MongoDB collection.
    @document: The MongoDB document to insert.
    """
    status = None
    result = client[database][collection].delete_one(document)
    if result.deleted_count == 1:
        status = True
    else:
        status = False
    return status


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


def create_index(client, database, collection, index_name, index):
    """
    Creates an index on the given collection
    @client: MongoDB connection.
    @database: MongoDB Database.
    @collection: MongoDB collection.
    @index_name: The index name.
    @index: Specification of index.
    """
    client[database][collection].create_index(index,
                                              name=index_name)


def document_exists(client, database, collection, document):
    exists = None
    if "_id" not in document.keys():
        exists = False  # Alwyays a new doc if no _id given
    else:
        count = client[database][collection].count_documents({"_id": document["_id"]})
        if count == 1:
            exists = True
        else:
            exists = False
    return exists


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
            ssl=dict(type='bool', default=False),
            ssl_cert_reqs=dict(type='str', default='CERT_REQUIRED', choices=['CERT_NONE', 'CERT_OPTIONAL', 'CERT_REQUIRED']),
            database=dict(type='str', default="test"),
            collection=dict(type='str', required=True),
            document=dict(type='raw', required=True),
            state=dict(type='str', required=False, default='present', choices=['absent', 'present']),
            index=dict(type='raw'),
            index_name=dict(type='str', default="idx_mongodb_document"),
            upsert=dict(type='bool', default=False)),
        supports_check_mode=True)

    if HAS_PYMONGO is False:
        module.fail_json(msg='the python pymongo module is required')

    login_user = module.params['login_user']
    login_password = module.params['login_password']
    login_database = module.params['login_database']
    login_host = module.params['login_host']
    login_port = module.params['login_port']
    ssl = module.params['ssl']
    database = module.params['database']
    collection = module.params['collection']
    document = module.params['document']
    state = module.params['state']
    index = module.params['index']
    index_name = module.params['index_name']
    upsert = module.params['upsert']

    result = dict(
        failed=False,
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

    try:
        if module.check_mode:
            if state == "present":
                if document_exists(client, database, collection, document):
                    result["changed"] = False
                    result["msg"] = "Document already exists"
                else:
                    result["changed"] = True
                    result["msg"] = "Document was inserted"
                    result["_id"] = "dummy_id"
            elif state == "absent":
                if document_exists(client, database, collection, document):
                    result["changed"] = True
                    result["msg"] = "Document was deleted"
                else:
                    result["changed"] = False
                    result["msg"] = "Document does not exist in collection"
        else:
            if state == "present":
                rs, inserted_id = insert_document(client, database, collection, document)
                if rs:
                    result["changed"] = True
                    if inserted_id is not None:
                        result["inserted_id"] = inserted_id
                        result["msg"] = "Document was inserted"
                    else:
                        result["msg"] = "Document was updated"
                else:
                    result["changed"] = False
                    result["msg"] = "Document already exists"
            elif state == "absent":
                delete_count = delete_document(client, database, collection, document)
                if delete_count > 0:
                    result["changed"] = True
                    result["msg"] = "Document was deleted"
                else:
                    result["changed"] = False
                    result["msg"] = "Document does not exist in collection"

    except Exception as e:
        module.fail_json(msg='Error running module: %s' % str(e))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
