mongodb_repository
==================

Configures a repository for MongoDB on Debian and RedHat based platforms.

Role Variables
--------------

mongodb_version: Version of MongoDB. Default "4.2".
debian_packages: Packages needs on Debian systems for this role.

Example Playbook
----------------

Set mongodb_version to 4.0.

```yaml
    - hosts: servers
      roles:
         - { role: mongodb_repository, mongodb_version: "4.0" }
```

License
-------

BSD

Author Information
------------------

Rhys Campbell (https://github.com/rhysmeister)
