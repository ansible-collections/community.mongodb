#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: mongodb_atlas_federation_role_mapping
short_description: Manage Atlas Federation role mappings for SAML/OIDC groups
description:
  - Manage role mappings between external IdP groups and MongoDB Atlas org/project roles.
  - Used to grant Atlas Console access to SAML/SSO groups (e.g. ORG_OWNER, GROUP_READ_ONLY).
  - Uses OAuth2 client_credentials (Service Account) for authentication.
  - L(API Documentation,https://www.mongodb.com/docs/atlas/reference/api-resources-spec/v2/#tag/Federated-Authentication)
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
  federation_settings_id:
    description:
      - Unique identifier of the federation settings.
    required: true
    type: str
    aliases: [ "federationSettingsId" ]
  org_id:
    description:
      - Unique identifier of the Atlas organization.
    required: true
    type: str
    aliases: [ "orgId" ]
  state:
    description:
      - Desired state of the role mapping.
    choices: [ "present", "absent" ]
    default: present
    type: str
  external_group_name:
    description:
      - Name of the external IdP group (e.g. AD/SAML group name).
    required: true
    type: str
    aliases: [ "externalGroupName" ]
  role_assignments:
    description:
      - List of Atlas role assignments for this group.
    required: true
    type: list
    elements: dict
    suboptions:
      org_id:
        description:
          - Atlas org ID for org-level role assignment. Mutually exclusive with group_id.
        type: str
        aliases: [ "orgId" ]
      group_id:
        description:
          - Atlas project ID for project-level role assignment. Mutually exclusive with org_id.
        type: str
        aliases: [ "groupId" ]
      role:
        description:
          - Atlas role name (e.g. ORG_OWNER, ORG_MEMBER, GROUP_READ_ONLY).
        required: true
        type: str
'''

EXAMPLES = '''
- name: Map AD group to ORG_OWNER in Atlas
  community.mongodb.mongodb_atlas_federation_role_mapping:
    service_account_id: "mdb_sa_id_xxxx"
    service_account_secret: "mdb_sa_sk_xxxx"
    federation_settings_id: "69d3f63fd91aa77b74a930a0"
    org_id: "694ec9ddbaecce170ffe8b62"
    external_group_name: "SG-OCI-INFRA-ADMINS"
    role_assignments:
      - org_id: "694ec9ddbaecce170ffe8b62"
        role: "ORG_OWNER"

- name: Map AD group to project read-only
  community.mongodb.mongodb_atlas_federation_role_mapping:
    service_account_id: "mdb_sa_id_xxxx"
    service_account_secret: "mdb_sa_sk_xxxx"
    federation_settings_id: "69d3f63fd91aa77b74a930a0"
    org_id: "694ec9ddbaecce170ffe8b62"
    external_group_name: "SG-OCI-DB-Family"
    role_assignments:
      - org_id: "694ec9ddbaecce170ffe8b62"
        role: "ORG_MEMBER"
      - group_id: "6991db0a32bf1b56dbb63d62"
        role: "GROUP_READ_ONLY"
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
        federation_settings_id=dict(required=True, aliases=["federationSettingsId"]),
        org_id=dict(required=True, aliases=["orgId"]),
        external_group_name=dict(required=True, aliases=["externalGroupName"]),
        role_assignments=dict(
            required=True,
            type="list",
            elements="dict",
            options=dict(
                org_id=dict(type="str", default=None, aliases=["orgId"]),
                group_id=dict(type="str", default=None, aliases=["groupId"]),
                role=dict(required=True, type="str"),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec, supports_check_mode=True
    )

    role_assignments = []
    for ra in module.params.get("role_assignments"):
        role_assignments.append({
            "orgId": ra.get("org_id"),
            "groupId": ra.get("group_id"),
            "role": ra.get("role"),
        })

    data = {
        "externalGroupName": module.params["external_group_name"],
        "roleAssignments": role_assignments,
    }

    base_url = (
        "https://cloud.mongodb.com/api/atlas/v2/federationSettings/"
        + module.params["federation_settings_id"]
        + "/connectedOrgConfigs/"
        + module.params["org_id"]
    )

    # Build AtlasAPIObjectV2 only to get a working call_url() with correct auth/headers.
    # We cannot use atlas.update() here because the /roleMappings endpoint:
    #   - has no GET-by-name (requires listing and matching by externalGroupName)
    #   - returns HTTP 200 (not 201) on POST
    #   - requires PUT /{id} (not PATCH /{name}) for updates
    try:
        atlas = AtlasAPIObjectV2(
            module=module,
            path="/roleMappings",
            object_name="externalGroupName",
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

    # Find existing mapping by externalGroupName
    existing_id = None
    existing_data = None
    ret = atlas.call_url(path="/roleMappings")
    if ret["code"] == 200:
        for item in ret["data"].get("results", []):
            if item.get("externalGroupName") == data["externalGroupName"]:
                existing_id = item["id"]
                existing_data = item
                break
    elif ret["code"] not in (404,):
        module.fail_json(
            msg="failed to list role mappings: %d. Error: %s" % (ret["code"], ret["error"])
        )

    state = module.params["state"]
    changed = False
    diff_result = {"before": "", "after": ""}

    if state == "present":
        if existing_id:
            diff_result["before"] = "state: present\n"
            # Compare roleAssignments to detect if update is needed
            if existing_data.get("roleAssignments") != data["roleAssignments"]:
                if module.check_mode:
                    diff_result["after"] = "state: updated\n"
                    module.exit_json(changed=True, diff=diff_result)
                ret = atlas.call_url(
                    path="/roleMappings/{0}".format(existing_id),
                    data=module.jsonify(data),
                    method="PUT",
                )
                if ret["code"] == 200:
                    changed = True
                    diff_result["after"] = "state: updated\n"
                else:
                    module.fail_json(
                        msg="bad return code while updating: %d. Error message: %s"
                        % (ret["code"], ret["error"])
                    )
            else:
                diff_result["after"] = "state: present\n"
        else:
            diff_result["before"] = "state: absent\n"
            if module.check_mode:
                diff_result["after"] = "state: created\n"
                module.exit_json(changed=True, diff=diff_result)
            ret = atlas.call_url(
                path="/roleMappings",
                data=module.jsonify(data),
                method="POST",
            )
            if ret["code"] in (200, 201):
                changed = True
                diff_result["after"] = "state: created\n"
            else:
                module.fail_json(
                    msg="bad return code while creating: %d. Error message: %s"
                    % (ret["code"], ret["error"])
                )

    elif state == "absent":
        if existing_id:
            diff_result["before"] = "state: present\n"
            if module.check_mode:
                diff_result["after"] = "state: absent\n"
                module.exit_json(changed=True, diff=diff_result)
            ret = atlas.call_url(
                path="/roleMappings/{0}".format(existing_id),
                method="DELETE",
            )
            if ret["code"] in (200, 202, 204):
                changed = True
                diff_result["after"] = "state: absent\n"
            else:
                module.fail_json(
                    msg="bad return code while deleting: %d. Error message: %s"
                    % (ret["code"], ret["error"])
                )
        else:
            diff_result["before"] = "state: absent\n"
            diff_result["after"] = "state: absent\n"

    module.exit_json(changed=changed, data=data, diff=diff_result)


if __name__ == "__main__":
    main()
