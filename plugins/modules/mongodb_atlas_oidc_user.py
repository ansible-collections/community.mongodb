#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: mongodb_atlas_oidc_user
short_description: Manage OIDC database users in Atlas
description:
  - Manage OIDC-authenticated database users (human users and IdP groups) in MongoDB Atlas.
  - Uses OAuth2 client_credentials (Service Account) for authentication.
  - For oidc_auth_type USER the database_name must be C($external).
  - For oidc_auth_type IDP_GROUP the database_name must be C(admin).
  - L(API Documentation,https://www.mongodb.com/docs/atlas/reference/api-resources-spec/v2/#tag/Database-Users)
author: "Karol Murawski (@kazz3m)"
options:
  service_account_id:
    description:
      - MongoDB Atlas Service Account client ID (OAuth2).
      - Mutually exclusive with C(api_username).
    type: str
    aliases: [ "serviceAccountId" ]
  service_account_secret:
    description:
      - MongoDB Atlas Service Account client secret (OAuth2).
      - Mutually exclusive with C(api_password).
    no_log: true
    type: str
    aliases: [ "serviceAccountSecret" ]
  api_username:
    description:
      - Atlas API public key. Alternative to C(service_account_id).
    type: str
    aliases: [ "apiUsername" ]
  api_password:
    description:
      - Atlas API private key. Alternative to C(service_account_secret).
    no_log: true
    type: str
    aliases: [ "apiPassword" ]
  group_id:
    description:
      - Unique identifier of the Atlas project (group).
    required: true
    type: str
    aliases: [ "groupId" ]
  state:
    description:
      - Desired state of the user.
    choices: [ "present", "absent" ]
    default: present
    type: str
  oidc_auth_type:
    description:
      - OIDC authentication type.
      - C(USER) for individual human users authenticated via OIDC.
      - C(IDP_GROUP) for IdP groups mapped to MongoDB roles.
    choices: [ "USER", "IDP_GROUP" ]
    default: IDP_GROUP
    type: str
    aliases: [ "oidcAuthType" ]
  database_name:
    description:
      - Database against which Atlas authenticates the user.
      - Must be C($external) for C(USER) and C(admin) for C(IDP_GROUP).
    choices: [ "admin", "$external" ]
    default: "$external"
    type: str
    aliases: [ "databaseName" ]
  username:
    description:
      - Username for OIDC USER or IdP group identifier for IDP_GROUP.
      - For IDP_GROUP format is C(<idp_id>/<group_name>).
    required: true
    type: str
  roles:
    description:
      - Array of roles and the databases on which the roles apply.
    required: true
    type: list
    elements: dict
    suboptions:
      database_name:
        description:
          - Database on which the user has the specified role.
        required: true
        type: str
        aliases: [ "databaseName" ]
      role_name:
        description:
          - Name of the role. Can be a built-in or custom role.
        required: true
        type: str
        aliases: [ "roleName" ]
'''

EXAMPLES = '''
- name: Create OIDC IDP_GROUP database user
  community.mongodb.mongodb_atlas_oidc_user:
    service_account_id: "mdb_sa_id_xxxx"
    service_account_secret: "mdb_sa_sk_xxxx"
    group_id: "6991db0a32bf1b56dbb63d62"
    oidc_auth_type: "IDP_GROUP"
    database_name: "admin"
    username: "69d4192c57e96607c7180011/SG-DB-ROLE-APPOPS"
    roles:
      - database_name: admin
        role_name: readViewOnboardingCustomerList

- name: Create OIDC USER database user
  community.mongodb.mongodb_atlas_oidc_user:
    service_account_id: "mdb_sa_id_xxxx"
    service_account_secret: "mdb_sa_sk_xxxx"
    group_id: "6991db0a32bf1b56dbb63d62"
    oidc_auth_type: "USER"
    database_name: "$external"
    username: "69d4192c57e96607c7180011/karol.murawski@d360.com"
    roles:
      - database_name: admin
        role_name: dbAdminAnyDatabase
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_atlas import (
    AtlasAPIObjectV2,
)


def main():
    argument_spec = dict(
        state=dict(default="present", choices=["absent", "present"]),
        service_account_id=dict(aliases=["serviceAccountId"]),
        service_account_secret=dict(no_log=True, aliases=["serviceAccountSecret"]),
        api_username=dict(aliases=["apiUsername"]),
        api_password=dict(no_log=True, aliases=["apiPassword"]),
        group_id=dict(required=True, aliases=["groupId"]),
        oidc_auth_type=dict(default="IDP_GROUP", choices=["USER", "IDP_GROUP"], aliases=["oidcAuthType"]),
        database_name=dict(default="$external", choices=["admin", "$external"], aliases=["databaseName"]),
        username=dict(required=True),
        roles=dict(
            required=True,
            type="list",
            elements="dict",
            options=dict(
                database_name=dict(required=True, aliases=["databaseName"]),
                role_name=dict(required=True, aliases=["roleName"]),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec, supports_check_mode=True
    )

    data = {
        "databaseName": module.params["database_name"],
        "oidcAuthType": module.params["oidc_auth_type"],
        "username": module.params["username"],
        "roles": [],
    }

    for role in module.params.get("roles"):
        data["roles"].append({
            "databaseName": role.get("database_name"),
            "roleName": role.get("role_name"),
        })

    base_url = (
        "https://cloud.mongodb.com/api/atlas/v2/groups/"
        + module.params["group_id"]
    )

    try:
        atlas = AtlasAPIObjectV2(
            module=module,
            path="/databaseUsers",
            object_name="username",
            group_id=module.params["group_id"],
            data=data,
            base_url=base_url,
            service_account_id=module.params.get("service_account_id"),
            service_account_secret=module.params.get("service_account_secret"),
            api_username=module.params.get("api_username"),
            api_password=module.params.get("api_password"),
        )
    except Exception as e:
        module.fail_json(
            msg="unable to connect to Atlas API. Exception message: %s" % e
        )

    changed, diff = atlas.update(module.params["state"])
    module.exit_json(
        changed=changed,
        data=atlas.data,
        diff=diff,
    )


if __name__ == "__main__":
    main()
