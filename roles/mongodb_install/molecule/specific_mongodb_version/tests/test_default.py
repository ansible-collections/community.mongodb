import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def test_mongod_available(host):
    cmd = host.run("mongod --version")
    assert cmd.rc == 0
    assert "db version" in cmd.stdout


def test_mongo_available(host):
    cmd = host.run("mongo --version")
    assert cmd.rc == 0
    assert "MongoDB shell version" in cmd.stdout


def test_mongos_available(host):
    cmd = host.run("mongos --version")
    assert cmd.rc == 0
    assert "mongos version" in cmd.stdout


def test_mongodump_available(host):
    cmd = host.run("mongodump --version")
    assert cmd.rc == 0
    assert "mongodump version" in cmd.stdout


def test_specific_mongodb_version(host):
    cmd = host.run("mongod --version")
    assert cmd.rc == 0
    assert "4.2.2" in cmd.stdout
