# Mongodb Collection
|Category|Status|
|---|---|
|Github CI|![CI](https://github.com/ansible-collections/community.mongodb/workflows/CI/badge.svg)|
|Github Docs|![documentation](https://github.com/ansible-collections/community.mongodb/workflows/documentation/badge.svg)|
|Codecov|[![Codecov](https://img.shields.io/codecov/c/github/ansible-collections/community.mongodb)](https://codecov.io/gh/ansible-collections/community.mongodb)|
|CI Roles|![CI_roles](https://github.com/ansible-collections/community.mongodb/workflows/CI_roles/badge.svg)|
|AutomatingMongoDBWithAnsible|[![CI-basic](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/actions/workflows/CI-basic.yml/badge.svg)](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/actions/workflows/CI-basic.yml)|
|AutomatingMongoDBWithAnsible|[![CI-etc](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/actions/workflows/CI-etc.yml/badge.svg)](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/actions/workflows/CI-etc.yml)|
|AutomatingMongoDBWithAnsible|[![CI-resync](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/actions/workflows/CI-resync.yml/badge.svg)](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/actions/workflows/CI-resync.yml)|
|AutomatingMongoDBWithAnsible|[![CI-upgrade-downgrade](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/actions/workflows/CI-upgrade-downgrade.yml/badge.svg)](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/actions/workflows/CI-upgrade-downgrade.yml)|
|Latest Build|![Build & Publish Collection](https://github.com/ansible-collections/community.mongodb/workflows/Build%20&%20Publish%20Collection/badge.svg)|

This collection called `mongodb` aims at providing all Ansible modules allowing to interact with MongoDB.
The modules present in Ansible 2.9 are included in this collection and will benefit from the evolutions and quality requirements from this collection.

As this is an independent collection, it can be released on its own release cadence.

If you like this collection please give us a rating on [Ansible Galaxy](https://galaxy.ansible.com/community/mongodb).

## Collection contents

### Roles

These roles prepare servers with Debian-based and RHEL-based distributions to run MongoDB:

- `community.mongodb.mongodb_linux`: A simple role to configure Linux Operating System settings, as advised in the [MongoDB Production Notes](https://docs.mongodb.com/manual/administration/production-notes/).
- `community.mongodb.mongodb_selinux`: Configure SELinux for MongoDB.

- `community.mongodb.mongodb_repository`: Configures a package repository for MongoDB on Debian and RedHat based platforms.
- `community.mongodb.mongodb_install`: Install MongoDB packages on Debian and RedHat based platforms. This role, unlike all other roles, provides for installing specific versions of mongodb-org packages. Other roles merely validate that mongodb-org is installed/present; they do not install particular versions.

These roles manage configuring and starting various MongoDB services.

- `community.mongodb.mongodb_mongod`: Configure the `mongod` service (includes populating `mongod.conf`) which is a MongoDB replicaset or standalone server.
- `community.mongodb.mongodb_mongos`: Configure the `mongos` service (includes populating `mongos.conf`) which only runs in a sharded MongoDB cluster.
- `community.mongodb.mongodb_config`: Configure the CSRS Config Server Replicaset for a MongoDB sharded cluster. The CSRS is a special-purpose instance of `mongod` that hosts the `config` database for the sharded cluster. For standalone installations, please use the `mongodb_mongod` role instead.
- `community.mongodb.mongodb_auth`: Configure auth on MongoDB servers. NB: The other MongoDB server config roles (`mongodb_mongod`, `mongodb_mongos`, `mongodb_config`) do not configure auth. Use this role in conjunction with the other roles.

### Plugins

#### Lookup Plugins
- `community.mongodb.mongodb`: A lookup plugin that gets info from a collection using the MongoDB `find()` function.

#### Cache Plugins
- `community.mongodb.mongodb`: A cache plugin that stores the host fact cache records in MongoDB.

#### Modules

These modules are for any MongoDB cluster (standalone, replicaset, or sharded):

- `community.mongodb.mongodb_index`: Creates or drops indexes on MongoDB collections.
- `community.mongodb.mongodb_info`: Gather information about MongoDB instance.
- `community.mongodb.mongodb_monitoring`: Manages the [free monitoring](https://docs.mongodb.com/manual/administration/free-monitoring/) feature.
- `community.mongodb.mongodb_oplog`: [Resizes](https://docs.mongodb.com/manual/tutorial/change-oplog-size) the MongoDB oplog (MongoDB 3.6+ only).
- `community.mongodb.mongodb_parameter`: Change an administrative parameter on a MongoDB server.
- `community.mongodb.mongodb_schema`: Manages MongoDB Document Schema Validators.
- `community.mongodb.mongodb_shell`: Run commands via the MongoDB shell.
- `community.mongodb.mongodb_shutdown`: Cleans up all database resources and then terminates the mongod/mongos process.
- `community.mongodb.mongodb_user`: Adds or removes a user from a MongoDB database.

These modules are only useful for replicaset (or sharded) MongoDB clusters:

- `community.mongodb.mongodb_maintenance`: Enables or disables [maintenance](https://docs.mongodb.com/manual/reference/command/replSetMaintenance/) mode for a secondary member.
- `community.mongodb.mongodb_replicaset`: Initialises a MongoDB replicaset.
- `community.mongodb.mongodb_status`: Validates the status of the replicaset.
- `community.mongodb.mongodb_stepdown`: [Step down](https://docs.mongodb.com/manual/reference/command/replSetStepDown/) the MongoDB node from a PRIMARY state.

These modules are only useful for sharded MongoDB clusters:

- `community.mongodb.mongodb_balancer`: Manages the MongoDB Sharded Cluster Balancer.
- `community.mongodb.mongodb_shard`: Add or remove shards from a MongoDB Cluster.
- `community.mongodb.mongodb_shard_tag`: Manage Shard Tags.
- `community.mongodb.mongodb_shard_zone`: Manage Shard Zones.


## Running the integration and unit tests

* Requirements
  * [Python 3.5+](https://www.python.org/)
  * [pip](https://pypi.org/project/pip/)
  * [virtualenv](https://virtualenv.pypa.io/en/latest/) or [pipenv](https://pypi.org/project/pipenv/) if you prefer.
  * [git](https://git-scm.com/)
  * [docker](https://www.docker.com/)

* Useful Links
  * [Pip & Virtual Environments](https://docs.python-guide.org/dev/virtualenvs/)
  * [Ansible Integration Tests](https://docs.ansible.com/ansible/latest/dev_guide/testing_integration.html)

The ansible-test tool requires a specific directory hierarchy to function correctly so please follow carefully.

* Create the required directory structure. N-B. The ansible-test tool requires this format.

```bash
mkdir -p git/ansible_collections/community
cd git/ansible_collections/community
```

* Clone the required projects.

```bash
git clone  https://github.com/ansible-collections/community.mongodb.git ./mongodb
git clone  https://github.com/ansible-collections/community.general.git ./general
```

* Create and activate a virtual environment.

```bash
virtualenv venv
source venv/bin/activate
```

* Change to the project directory.

```bash
cd mongodb
```

* Install the devel branch of ansible-base.

```bash
pip install https://github.com/ansible/ansible/archive/devel.tar.gz --disable-pip-version-check
```

* Run integration tests for the mongodb_shard module.

```bash
ansible-test integration --docker default -v --color --python 3.6 mongodb_shard
```

* Run integration tests for the mongodb_status module.

```bash
ansible-test integration --docker default -v --color --python 3.6 mongodb_status
```

* Run integration tests for the mongodb_oplog module.

```bash
ansible-test integration --docker ubuntu1804 -v --color --python 3.6 mongodb_oplog
```

* Run tests for everything in the collection.

```bash
ansible-test integration --docker default -v --color --python 3.6
```

* Run the units tests

```bash
ansible-test units --docker default -v --color --python 3.6
```

## GitHub workflow

* Maintainers would be members of this GitHub Repo
* Branch protections could be used to enforce 1 (or 2) reviews from relevant maintainers [CODEOWNERS](.github/CODEOWNERS)

## Contributing

Any contribution is welcome and we only ask contributors to:
* Provide *at least* integration tests for any contribution.
* Create an issue for any significant contribution that would change a large portion of the codebase.

## License

GNU General Public License v3.0 or later

See LICENCING to see the full text.
