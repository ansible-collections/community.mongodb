mongodb_mongos
==============

A role to setup a mongos server for a MongoDB sharded cluster.

Requirements
------------

Any pre-requisites that may not be covered by Ansible itself or the role should
be mentioned here. For instance, if the role uses the EC2 module, it may be a
good idea to mention in this section that the boto package is required.

Role Variables
--------------

* `mongos_port`: The port used by the mongos process. Default 27017.
* `mongos_service`: The name of the mongos service. Default mongos.
* `mongodb_user`: The Linux OS user for MongoDB. Default mongod.
* `mongodb_group`: The Linux OS user group for MongoDB. Default mongod.
* `pid_file`: The pid file for mongos. Default /run/mongodb/mongos.pid.
* `bind_ip`: The IP address mongos will bind to. Default 0.0.0.0.
* `mypy`: Python interpretor. Default python
* `mongos_package`: The name of the mongos installation package. Default mongodb-org-mongos.
* `config_repl_set_name`: The name of the config server replicaset. Default cfg.
* `config_servers`: "config1:27019, config2:27019, config3:27019"
* `openssl_keyfile_content`: The kexfile content that MongoDB uses to authenticate within a replicaset. Generate with cmd: openssl rand -base64 756.
* `mongos_config_template`: If defined allows to override path to mongod config template with custom configuration. Default "mongos.conf.j2"
* `skip_restart`: If set to `true` will skip restarting mongos service when config file or the keyfile content changes. Default `true`.

Dependencies
------------

mongodb_repository

Example Playbook
----------------

```yaml
    - hosts: servers
      roles:
         - mongodb_repository
         - mongodb_mongos
```

License
-------

BSD

Author Information
------------------

Rhys Campbell (https://github.com/rhysmeister)
