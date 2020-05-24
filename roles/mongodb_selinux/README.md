mongodb_linux
=============

Configures SeLinux as per the instructions located at https://docs.mongodb.com/manual/tutorial/install-mongodb-on-red-hat/


Role Variables
--------------

required_packages: Package required for this role. Currently checkpolicy & policycoreutils-python.

Example Playbook
----------------

    - hosts: servers
      roles:
         - "mongodb_selinux"

License
-------

BSD

Author Information
------------------

An optional section for the role authors to include contact information, or a
website (HTML is not allowed).
