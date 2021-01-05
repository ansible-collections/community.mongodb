# Mongodb Collection
|Category|Status|
|---|---|
|Github CI|![CI](https://github.com/ansible-collections/community.mongodb/workflows/CI/badge.svg)|
|Github Docs|![documentation](https://github.com/ansible-collections/community.mongodb/workflows/documentation/badge.svg)|
|Codecov|[![Codecov](https://img.shields.io/codecov/c/github/ansible-collections/community.mongodb)](https://codecov.io/gh/ansible-collections/community.mongodb)|
|CI Roles|![CI_roles](https://github.com/ansible-collections/community.mongodb/workflows/CI_roles/badge.svg)|
|MongoDB Clusters|![CI](https://github.com/rhysmeister/AutomatingMongoDBWithAnsible/workflows/CI/badge.svg)|
|Latest Build|![Build & Publish Collection](https://github.com/ansible-collections/community.mongodb/workflows/Build%20&%20Publish%20Collection/badge.svg)|

This collection called `mongodb` aims at providing all Ansible modules allowing to interact with MongoDB.
The modules present in Ansible 2.9 are included in this collection and will benefit from the evolutions and quality requirements from this collection.

As this is an independent collection, it can be released on its own release cadence.

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
