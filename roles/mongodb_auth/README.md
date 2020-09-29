mongodb_auth
============

This role to enables auth on MongoDB servers, adds the first admin user, and adds a list of other users.
If your mongo instance requires ssl or an alternative auth_mechanism, please use
[`module_defaults`](https://docs.ansible.com/ansible/latest/user_guide/playbooks_module_defaults.html)
to provide the default auth details for `community.mongodb.mongodb_user` (these defaults are ignored
when adding the initial admin user with the localhost exception).

If running this on a MongoDB server that already has an admin user (ie when using this role to audit
an alternate install method), you must touch `/root/mongodb_admin.success` or you will get an error
when this role tries to add the admin user again.

Role Variables
--------------

mongod_host: The domain or ip to use to communicate with mongod. Default localhost.
mongod_port: The port used by the mongod process. Default 27017.
mongod_package: The mongod package to install. Default mongodb-org-server.
authorization: Enable authorization. Default enabled.
mongodb_admin_db: MongoDB admin database (for adding users). Default admin.
mongodb_admin_user: MongoDB admin username. Default admin.
mongodb_admin_pwd: MongoDB admin password. Defaults to value of mongodb_admin_default_pwd.
mongodb_admin_default_pwd: MongoDB admin password (for parent roles to override without overriding user's password). Default admin.
mongodb_users: List of additional users to add. Each user dict should include fields: db, user, pwd, roles
mongodb_force_update_password: Whether or not to force a password update for any users in mongodb_users. Setting this to yes will result in 'changed' on every run, even if the password is the same. Setting this to no only adds a password when creating the user.

IMPORTANT NOTE: It is expected that mongodb_admin_user & mongodb_admin_pwd values be overridden in your own file protected by Ansible Vault. Any production environments should protect these values. For more information see [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html)

Dependencies
------------

mongodb_repository

Example Playbook
----------------

Install MongoDB preparing hosts for a Sharded Cluster.

```yaml
    - hosts: servers
      roles:
         - { role: mongodb_repository }
         - { role: mongodb_mongod, mongod_port: 27018, sharding: true }
         - { role: mongodb_auth, mongod_port: 27018, mongod_host: 127.0.0.1, mongodb_admin_pwd: f00b@r }
```

License
-------

BSD

Author Information
------------------

Jacob Floyd (https://github.com/cognifloyd)
