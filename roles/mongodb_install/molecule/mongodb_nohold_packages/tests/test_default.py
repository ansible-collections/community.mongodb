import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def test_mongodb_lock_file(host):
    f = host.file("/root/mongo_version_lock.success")
    assert not f.exists


def test_mongodb_packages_installed(host):
    p = host.package("mongodb-org")
    assert p.is_installed
    p = host.package("mongodb-org-server")
    assert p.is_installed
    p = host.package("mongodb-org-shell")
    assert p.is_installed
    p = host.package("mongodb-org-mongos")
    assert p.is_installed
    p = host.package("mongodb-org-tools")
    assert p.is_installed


def test_mongodb_packages_held(host):
    if host.ansible.get_variables()['inventory_hostname'] in ['debian_buster', 'debian_stretch', 'ubuntu_16', 'ubuntu_18']:
        c = "apt-mark showhold"
    elif host.ansible.get_variables()['inventory_hostname'].startswith('centos'):
        c = "yum versionlock list"
    cmd = host.run(c)
    assert cmd.rc == 0
    assert 'mongodb-org' not in cmd.stdout
