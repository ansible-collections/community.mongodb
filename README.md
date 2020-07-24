# Mongodb Collection
![CI](https://github.com/ansible-collections/community.mongodb/workflows/CI/badge.svg)
[![Codecov](https://img.shields.io/codecov/c/github/ansible-collections/mongodb)](https://codecov.io/gh/ansible-collections/mongodb)
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-1-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

This collection called `mongodb` aims at providing all Ansible modules allowing to interact with MongoDB.
The modules present in Ansible 2.9 are included in this collection and will benefit from the evolutions and quality requirements from this collection.

As this is an independent Collection, it can be release on it's own release cadance.

## Running the integration tests

Clone the collection git project. The ansible-test tool requires a specific directory setup to function correctly so please follow carefully.

```
cd && mkdir -p git/ansible_collections/community
git clone https://github.com/ansible-collections/community.mongodb.git ./ansible_collections/community/mongodb
cd ./git/ansible_collections/community/mongodb
```

Create a Python virtual environment.

```
virtualenv venv
source venv/bin/activate
pip install -r requirements-3.6.txt
```

Run integration tests for the mongodb_shard module.

```
ansible-test integration --docker default -v --color --python 3.6 mongodb_shard
```

Run integration tests for the mongodb_status module.

```
ansible-test integration --docker default -v --color --python 3.6 mongodb_status
```

Run integration tests for the mongodb_oplog module.

```
ansible-test integration --docker default -v --color --python 3.6 mongodb_status
```

Run tests for everything in collection.

```
ansible-test integration --docker default -v --color --python 3.6
```

## GitHub workflow

* Maintainers would be members of this GitHub Repo
* Branch protections could be used to enforce 1 (or 2) reviews from relevant maintainers [CODEOWNERS](.github/CODEOWNERS)

## Contributing

Any contribution is welcome and we only ask contributors to:
* Provide *at least* integration tests for any contribution.
* Create an issues for any significant contribution that would change a large portion of the code base.

## License

GNU General Public License v3.0 or later

See LICENCING to see the full text.
