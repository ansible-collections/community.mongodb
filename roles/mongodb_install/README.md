mongodb_install
===============

Install MongoDB packages on Debian and RedHat based platforms. Installs the mongodb-org meta-package which then installs the following packages: mongodb-org-server, mongodb-org-shell, mongodb-org-mongos, mongodb-org-tools.

Role Variables
--------------

specific_mongodb_version - Install a specific version of mongodb i.e. 4.4.1. The specified version must be available in the system repositories. By default this variable is undefined.

Dependencies
------------
mongodb_repository

Example Playbook
----------------

```yaml
    - hosts: servers
      roles:
         - mongodb_repository
         - mongodb_install
```

License
-------

BSD

Author Information
------------------

Rhys Campbell (https://github.com/rhysmeister)
