===============================
Community.MongoDB Release Notes
===============================

.. contents:: Topics

v1.3.2
=======

Release Summary
---------------

This release is a maintenance release.

Minor Changes
---------------

- 413 - mongodb_shell - Adds escape_param function that will work better across various python versions.
- 414-416 - Minor documentation improvements.
- 411 - mongodb_shell - FIx missing db parameter when fiel parmeter is used.
- 403 - Make db path configurable in roles.
- 401 - mongodb_replicaset - Add further examples.
- 399 - Removes unused imports from modules.
- 396 - Add tags to roles.
- 387 - Fix doucmentation for mongod cache plugin.

Major Changes
---------------

- 397 & 376 - mongodb_replicaset - Add reconfigure abilities to module. Add and removes members from replicasets.

v1.3.1
======

Release Summary
---------------

This release is a maintenance release. The GitHub CI has been updated to include MongoDB 5.0 as well
as a few new features. The mongosh shell is now supported in the mongodb_shell module. Support for the
old mongo shell will be removed in a future release.

Minor Changes
-------------

- 360 - mongodb_shell - Adds support for the mongosh shell now available with MongoDB 5.0.
- 368 - mongodb_shell - Use shlex escape function.
- 370 - mongodb_install - Adds mongodb_hold_packages variable. Runs the lock_mongodb_packages.sh script
  to either lock mongodb-org packages at a specific version or to release the lock.
  Set to "HOLD" or "NOHOLD" as desired. No checks are made to see if the hold already exists or not.
  By default this variable is undefined and the script is not executed.
  The task is executed at the end and it is possible that packages could be upgraded
  before the lock is initially applied.

Deprecated Features
-------------------

- mongodb_shell - Support for the mongo shell is deprecated and will be removed in a future version.

v1.3.0
======

Release Summary
---------------

This release improves sharded cluster management, and adds schema validator management.
Several bug fixes improve compatibility with python3.6.


Minor Changes
-------------

- 338 - role monogdb_repository - Variablize repository details.
- 345 - roles mongodb_config, mongodb_mongod, mongodb_mongos - Make security.keyFile configurable.
- 346 - roles mongodb_config, mongodb_mongod, mongodb_mongos - Allow using net.bindIpAll instead of net.bindIp.
- 347 - roles mongodb_config, mongodb_mongod, mongodb_mongos - Allow overriding net.compression.compressors in mongo*.conf

Security Fixes
--------------

- 312 - Set no_log True for ssl_keyfile.

Bugfixes
--------

- 315 - Fix exception handling for mongodb_stepdown module on python3.6
- 320 - Fix exception handling for modules mongodb_balancer, mongodb_shard, and mongodb_status.
- 352 - Add ansible.posix collection to dependencies list.

New Modules
-----------

- community.mongodb.mongodb_monitoring - Manages the free monitoring feature.
- community.mongodb.mongodb_schema - Manages MongoDB Document Schema Validators.
- community.mongodb.mongodb_shard_tag - Manage Shard Tags.
- community.mongodb.mongodb_shard_zone - Manage Shard Zones.

v1.2.1
======

Minor Changes
-------------

- 304 - Adds validate parameter to mongodb_status module.

v1.2.0
======

Release Summary
---------------

A variety of idempotency and reliability improvements.


Bugfixes
--------

- 281 - mongodb_linux Fixes disable-transparent-huge-pages.service idempotency.
- 282 - Add restart handler, and bool variable to control to mongofb_config/mongod/mongos roles.
- 285 - Output users and roles dict by database to avoid overwriting entries.
- 287 - Fixes return value on older versions of MongoDB.
- 290 - Adds pseudo-idempotency feature to module.

v1.1.2
======

Bugfixes
--------

- 252 - Fix config template override in various roles.
- 255 - Add replica_set param to mongodb_index module.
- 264 - Only add force parameter to shutdown command when set to true.
- 275 - Use OrderedDict class in the following modules, mongodb_balancer, mongodb_oplog, mongodb_shutdown.

v1.1.1
======

Bugfixes
--------

- 235 - Fix namespace.

v1.1.0
======

Release Summary
---------------

This release adds the mongodb_shell module and the mongodb_auth role.


New Modules
-----------

- community.mongodb.mongodb_shell - Run commands via the MongoDB shell.

New Roles
---------

- community.mongodb.mongodb_auth - Configure auth on MongoDB servers.

v1.0.0
======

Release Summary
---------------

The first stable release of the commmunity.mongodb collection.
Many of the plugins and modules were previously released in ansible itself.


New Plugins
-----------

Cache
~~~~~

- community.mongodb.mongodb - This cache uses per host records saved in MongoDB.

Lookup
~~~~~~

- community.mongodb.mongodb - The ``MongoDB`` lookup runs the *find()* command on a given *collection* on a given *MongoDB* server.

New Modules
-----------

- community.mongodb.mongodb_balancer - Manages the MongoDB Sharded Cluster Balancer.
- community.mongodb.mongodb_index - Creates or drops indexes on MongoDB collections.
- community.mongodb.mongodb_info - Gather information about MongoDB instance.
- community.mongodb.mongodb_maintenance - Enables or disables maintenance mode for a secondary member.
- community.mongodb.mongodb_oplog - Resizes the MongoDB oplog.
- community.mongodb.mongodb_parameter - Change an administrative parameter on a MongoDB server
- community.mongodb.mongodb_replicaset - Initialises a MongoDB replicaset.
- community.mongodb.mongodb_shard - Add or remove shards from a MongoDB Cluster
- community.mongodb.mongodb_shutdown - Cleans up all database resources and then terminates the mongod/mongos process.
- community.mongodb.mongodb_status - Validates the status of the cluster.
- community.mongodb.mongodb_stepdown - Step down the MongoDB node from a PRIMARY state.
- community.mongodb.mongodb_user - Adds or removes a user from a MongoDB database

New Roles
---------

- community.mongodb.mongodb_config - Configure the CSRS Config Server Replicaset for a MongoDB sharded cluster. (Use mongodb_mongod for Standalone installations - this does not create mongo.conf)
- community.mongodb.mongodb_install - Install MongoDB packages on Debian and RedHat based platforms.
- community.mongodb.mongodb_linux - A simple role to configure Linux Operating System settings, as advised in the MongoDB Production Notes.
- community.mongodb.mongodb_mongod - Configure the mongod service (includes populating mongod.conf) which is a MongoDB replicaset or standalone server.
- community.mongodb.mongodb_mongos - Configure the mongos service (includes populating mongos.conf) which only runs in a sharded MongoDB cluster.
- community.mongodb.mongodb_repository - Configures a package repository for MongoDB on Debian and RedHat based platforms.
- community.mongodb.mongodb_selinux - Configure SELinux for MongoDB.
