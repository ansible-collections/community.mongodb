mongodb_install
===============

Install MongoDB packages on Debian and RedHat based platforms. Installs the mongodb-org meta-package which then installs the following packages: mongodb-org-server, mongodb-org-shell, mongodb-org-mongos, mongodb-org-tools.

Role Variables
--------------

None

Dependencies
------------
 meta package which
mongodb_repository

Example Playbook
----------------

    - hosts: servers
      roles:
         - mongodb_repository
         - mongodb_install

License
-------

BSD

Author Information
------------------

Rhys Campbell (https://github.com/rhysmeister)
