import os
import yaml

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


def include_vars(host):
    ansible = host.ansible("include_vars",
                           'file="../../defaults/main.yml"',
                           False,
                           False)
    return ansible


def test_mongod_cnf_file(host):
    f = host.file("/etc/mongod.conf")

    assert f.exists
    assert yaml.safe_load(f.content)["security"]["authorization"] == "enabled"


def test_mongod_service(host):
    mongod_service = include_vars(host)["ansible_facts"].get("mongod_service", "mongod")
    s = host.service(mongod_service)

    assert s.is_running
    assert s.is_enabled


def test_mongod_port(host):
    port = include_vars(host)["ansible_facts"].get("mongod_port", 27017)
    s = host.socket("tcp://0.0.0.0:{0}".format(port))
    assert s.is_listening


def test_mongo_shell_connectivity(host):
    """
    Tests that we can connect to mongos via the shell annd run a cmd
    """
    facts = include_vars(host)["ansible_facts"]
    port = facts.get("mongod_port", 27017)
    user = facts.get("mongod_admin_user", "admin")
    pwd = facts.get("mongodb_default_admin_pwd", "admin")

    cmd = host.run(
        "mongosh admin --username {user} --password {pwd} --port {port} --eval 'db.runCommand({{listDatabases: 1}})'".format(
            user=user, pwd=pwd, port=port
        )
    )

    assert cmd.rc == 0
    assert "admin" in cmd.stdout
