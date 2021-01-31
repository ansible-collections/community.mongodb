mongodb_mongod
==============

A simple role to aid in the setup of a MongoDB replicaset.

Role Variables
--------------

* `mongod_port`: The port used by the mongod process. Default 27017.
* `mongod_service`: The name of the mongod service. Default mongod.
* `mongodb_user`: The Linux OS user for MongoDB. Default mongod.
* `mongodb_group`: The Linux OS user group for MongoDB. Default mongod.
* `bind_ip`: The IP address mongos will bind to. Default 0.0.0.0.
* `repl_set_name`: The name of the replicaset the member will participate in. Default rs0.
* `authorization`: Enable authorization. Default enabled.
* `openssl_keyfile_content`: The keyfile content that MongoDB uses to authenticate within a replicaset. Generate with cmd: openssl rand -base64 756.
* `mongodb_admin_user`: MongoDB admin username. Default admin.
* `mongodb_admin_pwd`: MongoDB admin password. Default admin.
* `mongod_package`: The mongod package to install. Default mongodb-org-server.
* `replicaset`: When enabled add a replication section to the configuration. Default true.
* `sharding`: If this replicaset member will form part of a sharded cluster. Default false.
* `mongod_config_template`: If defined allows to override path to mongod config template with custom configuration. Default "mongod.conf.j2"
* `skip_restart`: If set to `true` will skip restarting mongod service when config file or the keyfile content changes. Default `true`.

IMPORTANT NOTE: It is expected that `mongodb_admin_user` & `mongodb_admin_pwd` values be overridden in your own file protected by Ansible Vault. These values are primary included here for Molecule/Travis CI integration. Any production environments should protect these values. For more information see [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html)

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
```

License
-------

BSD

Author Information
------------------

Rhys Campbell (https://github.com/rhysmeister)
