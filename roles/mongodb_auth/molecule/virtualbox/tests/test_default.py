import os
import yaml

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def include_vars(host):
    ansible = host.ansible('include_vars',
                           'file="../../defaults/main.yml"',
                           False,
                           False)
    return ansible


def test_mongod_cnf_file(host):
    f = host.file('/etc/mongod.conf')

    assert f.exists
    assert yaml.safe_load(f.content)["security"]["authorization"] == "enabled"


def test_mongod_service(host):
    mongod_service = include_vars(host)['ansible_facts']['mongod_service']
    s = host.service(mongod_service)

    assert s.is_running
    assert s.is_enabled


def test_mongod_port(host):
    port = include_vars(host)['ansible_facts']['mongod_port']
    s = host.socket("tcp://0.0.0.0:{0}".format(port))

    assert s.is_listening


def test_mongod_replicaset(host):
    '''
    Ensure that the MongoDB replicaset has been created successfully
    '''
    port = include_vars(host)['ansible_facts']['mongod_port']
    cmd = "mongo --port {0} --eval 'rs.status()'".format(port)
    # We only want to run this once
    if host.ansible.get_variables()['inventory_hostname'] == "ubuntu_16":
        r = host.run(cmd)

        assert "rs0" in r.stdout
        assert "ubuntu-16:27017" in r.stdout
        assert "ubuntu-18:27017" in r.stdout
        assert "debian-stretch:27017" in r.stdout
        assert "debian-buster:27017" in r.stdout
        assert "centos-7:27017" in r.stdout
