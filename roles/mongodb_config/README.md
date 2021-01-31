mongodb_config
==============

A simple role to aid in setting up a CSRS Config Server Replicaset for a MongoDB sharded cluster.

Role Variables
--------------

* `config_port`: The port used by the mongos process. Default 27019.
* `mongod_service`: The name of the mongod service. Default mongod.
* `mongodb_user`: The Linux OS user for MongoDB. Default mongod.
* `mongodb_group`: The Linux OS user group for MongoDB. Default mongod.
* `pid_file`: The pid file for mongos. Default /run/mongodb/mongos.pid.
* `bind_ip`: The IP address mongos will bind to. Default 0.0.0.0.
* `config_repl_set_name`: The replicaset name for the config servers. Default cfg.
* `authorization`: Enable authorization. Default enabled.
* `openssl_keyfile_content`: The kexfile content that MongoDB uses to authenticate within a replicaset. Generate with cmd: openssl rand -base64 756.
* `mongod_package`: The name of the mongod installation package. Default mongodb-org-server.
replicaset: When enabled add a replication section to the configuration. Default true.
* `mongod_config_template`: If defined allows to override path to mongod config template with custom configuration. Default "mongod.conf.j2"
* `skip_restart`: If set to `true` will skip restarting mongod service when config file or the keyfile content changes. Default `true`.

Dependencies
------------

mongodb_repository

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables
passed in as parameters) is always nice for users too:


```yaml
    - hosts: servers
      roles:
         - { role: mongodb_repository }
         - { role: mongodb_config, config_repl_set_name: "mycustomrs" }
```

License
-------

BSD

Author Information
------------------

Rhys Campbell (https://github.com/rhysmeister)
