import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def include_vars(host):
    if host.system_info.distribution == "redhat" \
            or host.system_info.distribution == "centos":
        ansible = host.ansible('include_vars',
                               'file="../../vars/RedHat.yml"',
                               False,
                               False)
    if host.system_info.distribution == "debian" \
            or host.system_info.distribution == "ubuntu":
        ansible = host.ansible('include_vars',
                               'file="../../vars/Debian.yml"',
                               False,
                               False)
    return ansible


def test_mongod_cnf_file(host):
    if host.ansible.get_variables()['inventory_hostname'] != 'config1':
        mongodb_user = include_vars(host)['ansible_facts']['mongodb_user']
        mongodb_group = include_vars(host)['ansible_facts']['mongodb_group']
        f = host.file('/etc/mongos.conf')

        assert f.exists
        assert f.user == mongodb_user
        assert f.group == mongodb_group


def test_mongod_service(host):

    if host.ansible.get_variables()['inventory_hostname'] != 'config1':
        mongos_service = include_vars(host)['ansible_facts']['mongos_service']
        s = host.service(mongos_service)

        assert s.is_running
        assert s.is_enabled


def test_mongod_port(host):
    if host.ansible.get_variables()['inventory_hostname'] != 'config1':
        port = include_vars(host)['ansible_facts']['mongos_port']
        s = host.socket("tcp://0.0.0.0:{0}".format(port))

        assert s.is_listening


def test_mongos_shell_connectivity(host):
    '''
    Tests that we can connect to mongos via the shell annd run a cmd
    '''
    if host.ansible.get_variables()['inventory_hostname'] != 'config1':
        port = include_vars(host)['ansible_facts']['mongos_port']
        cmd = host.run("mongo admin -username admin --password admin --port {0} --eval 'db.runCommand({{listDatabases: 1}})'".format(port))

        assert cmd.rc == 0
        assert "config" in cmd.stdout
        assert "admin" in cmd.stdout
