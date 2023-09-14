import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def include_vars(host):
    if host.system_info.distribution == "debian" \
            or host.system_info.distribution == "ubuntu":
        ansible = host.ansible('include_vars',
                               'file="../../vars/Debian.yml"',
                               False,
                               False)
    else:
        ansible = host.ansible('include_vars',
                               'file="../../vars/RedHat.yml"',
                               False,
                               False)
    return ansible


def test_mongod_cnf_file(host):
    mongodb_user = include_vars(host)['ansible_facts']['mongodb_user']
    mongodb_group = include_vars(host)['ansible_facts']['mongodb_group']
    f = host.file('/etc/mongod.conf')

    assert f.exists
    assert f.user == mongodb_user
    assert f.group == mongodb_group


def test_mongod_service(host):
    mongod_service = include_vars(host)['ansible_facts']['mongod_service']
    s = host.service(mongod_service)

    assert s.is_running
    assert s.is_enabled


def test_mongod_port(host):
    port = include_vars(host)['ansible_facts']['config_port']
    s = host.socket("tcp://0.0.0.0:{0}".format(port))

    assert s.is_listening


def test_mongod_replicaset(host):
    '''
    Ensure that the MongoDB config replicaset has been created successfully
    '''
    port = include_vars(host)['ansible_facts']['config_port']
    cmd = "mongosh --port {0} --eval 'rs.status()'".format(port)
    # We only want to run this once
    if host.ansible.get_variables()['inventory_hostname'] == "fedora":
        r = host.run(cmd)

        assert "cfg" in r.stdout
        assert "almalinux_8:{0}".format(port) in r.stdout
        assert "fedora:{0}".format(port) in r.stdout
        assert "ubuntu_22_04:{0}".format(port) in r.stdout
        assert "ubuntu_22:{0}".format(port) in r.stdout
        assert "debian_bullseye:{0}".format(port) in r.stdout


def test_mongod_config_default_path(host):
    '''
    Ensure that the default paths for RedHat and Debian based OSes are respected
    '''
    hostname = host.ansible.get_variables()['inventory_hostname']
    default_path = "/var/lib/mongo"
    if hostname.startswith('centos'):
        default_path = "/var/lib/mongo"
    elif hostname.startswith('ubuntu') or hostname.startswith('debian'):
        default_path = "/var/lib/mongodb"

    # assert path exists
    f = host.file(default_path)
    assert f.exists
    assert f.is_directory
    # asset mongodb.cnf contains path
    conf = host.file('/etc/mongod.conf').content_string
    assert "dbPath: {0}".format(default_path) in conf
