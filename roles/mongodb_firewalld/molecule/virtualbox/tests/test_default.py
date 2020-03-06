import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def test_firewalld_service(host):
    s = host.service('firewalld')

    assert s.is_running
    assert s.is_enabled
