#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: mongodb_atlas_org_invite
short_description: Manage Atlas organization user invitations
description:
  - Invite users to a MongoDB Atlas organization with specified org and project roles.
  - If the user already exists in the org, the module reports no change (idempotent).
  - If a pending invite for the user already exists, the module reports no change.
  - Uses OAuth2 client_credentials (Service Account) for authentication.
  - L(API Documentation,https://www.mongodb.com/docs/atlas/reference/api-resources-spec/v2/#tag/Organizations)
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
    type: str
    aliases: [ "apiPassword" ]
  org_id:
    description:
      - Unique identifier of the Atlas organization.
    required: true
    type: str
    aliases: [ "orgId" ]
  state:
    description:
      - C(present) ensures the user is invited or already a member.
      - C(absent) removes a pending invitation (does not remove existing org members).
    choices: [ "present", "absent" ]
    default: present
    type: str
  username:
    description:
      - Email address of the user to invite.
    required: true
    type: str
  roles:
    description:
      - List of org-level roles to assign (e.g. ORG_OWNER, ORG_MEMBER, ORG_READ_ONLY).
    required: true
    type: list
    elements: str
  group_role_assignments:
    description:
      - Optional list of project-level role assignments.
    type: list
    elements: dict
    default: []
    suboptions:
      group_id:
        description:
          - Atlas project ID.
        required: true
        type: str
        aliases: [ "groupId" ]
      roles:
        description:
          - List of project-level roles (e.g. GROUP_READ_ONLY, GROUP_DATA_ACCESS_READ_ONLY).
        required: true
        type: list
        elements: str
'''

EXAMPLES = '''
- name: Invite user as org owner
  community.mongodb.mongodb_atlas_org_invite:
    service_account_id: "mdb_sa_id_xxxx"
    service_account_secret: "mdb_sa_sk_xxxx"
    org_id: "694ec9ddbaecce170ffe8b62"
    username: "newuser@d360.com"
    roles:
      - ORG_OWNER

- name: Invite user with org and project roles
  community.mongodb.mongodb_atlas_org_invite:
    service_account_id: "mdb_sa_id_xxxx"
    service_account_secret: "mdb_sa_sk_xxxx"
    org_id: "694ec9ddbaecce170ffe8b62"
    username: "analyst@d360.com"
    roles:
      - ORG_MEMBER
    group_role_assignments:
      - group_id: "6991db0a32bf1b56dbb63d62"
        roles:
          - GROUP_READ_ONLY

- name: Revoke pending invitation
  community.mongodb.mongodb_atlas_org_invite:
    service_account_id: "mdb_sa_id_xxxx"
    service_account_secret: "mdb_sa_sk_xxxx"
    org_id: "694ec9ddbaecce170ffe8b62"
    username: "newuser@d360.com"
    roles: []
    state: absent
'''

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_atlas import (
    get_bearer_token,
    ATLAS_API_V2_VERSION,
)

ATLAS_BASE = "https://cloud.mongodb.com/api/atlas/v2"


def call_url(module, url, method="GET", data=None, token=None):
    headers = {
        "Accept": "application/vnd.atlas.{0}+json".format(ATLAS_API_V2_VERSION),
        "Content-Type": "application/vnd.atlas.{0}+json".format(ATLAS_API_V2_VERSION),
    }
    if token:
        headers["Authorization"] = "Bearer {0}".format(token)
    rsp, info = fetch_url(
        module=module,
        url=url,
        data=module.jsonify(data) if data is not None else None,
        headers=headers,
        method=method,
    )
    content = {}
    if rsp and info["status"] not in (204, 404):
        try:
            content = json.loads(rsp.read())
        except ValueError:
            pass
    return info["status"], content


def get_existing_member(module, token, org_id, username):
    """Return user dict if already an org member, else None."""
    page = 1
    while True:
        url = "{0}/orgs/{1}/users?pageNum={2}&itemsPerPage=100".format(ATLAS_BASE, org_id, page)
        status, data = call_url(module, url, token=token)
        if status != 200:
            return None
        for user in data.get("results", []):
            if user.get("username", "").lower() == username.lower():
                return user
        if len(data.get("results", [])) < 100:
            break
        page += 1
    return None


def get_pending_invite(module, token, org_id, username):
    """Return invite dict if a pending invite exists for username, else None."""
    url = "{0}/orgs/{1}/invites".format(ATLAS_BASE, org_id)
    status, data = call_url(module, url, token=token)
    if status != 200:
        return None
    if isinstance(data, list):
        results = data
    else:
        results = data.get("results", [])
    for invite in results:
        if invite.get("username", "").lower() == username.lower():
            return invite
    return None


def main():
    argument_spec = dict(
        state=dict(default="present", choices=["absent", "present"]),
        service_account_id=dict(aliases=["serviceAccountId"]),
        service_account_secret=dict(no_log=True, aliases=["serviceAccountSecret"]),
        api_username=dict(aliases=["apiUsername"]),
        api_password=dict(no_log=True, aliases=["apiPassword"]),
        org_id=dict(required=True, aliases=["orgId"]),
        username=dict(required=True),
        roles=dict(required=True, type="list", elements="str"),
        group_role_assignments=dict(
            type="list",
            elements="dict",
            default=[],
            options=dict(
                group_id=dict(required=True, aliases=["groupId"]),
                roles=dict(required=True, type="list", elements="str"),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec, supports_check_mode=True
    )

    if module.params.get("service_account_id") and module.params.get("service_account_secret"):
        token = get_bearer_token(
            module,
            module.params["service_account_id"],
            module.params["service_account_secret"],
        )
        # Digest auth not used — clear any url_username to avoid conflicts
    elif module.params.get("api_username") and module.params.get("api_password"):
        token = None
        module.params["url_username"] = module.params["api_username"]
        module.params["url_password"] = module.params["api_password"]
    else:
        module.fail_json(
            msg="Either service_account_id/service_account_secret or api_username/api_password must be provided."
        )

    org_id = module.params["org_id"]
    username = module.params["username"]
    state = module.params["state"]

    group_role_assignments = [
        {
            "groupId": gra["group_id"],
            "groupRoles": gra["roles"],
        }
        for gra in module.params.get("group_role_assignments") or []
    ]

    existing_member = get_existing_member(module, token, org_id, username)
    pending_invite = get_pending_invite(module, token, org_id, username)

    changed = False
    diff_result = {"before": "", "after": ""}

    if state == "present":
        if existing_member:
            # User already in org - nothing to do
            diff_result["before"] = "state: member\n"
            diff_result["after"] = "state: member\n"
        elif pending_invite:
            # Invite already pending - nothing to do
            diff_result["before"] = "state: invited\n"
            diff_result["after"] = "state: invited\n"
        else:
            diff_result["before"] = "state: absent\n"
            if module.check_mode:
                diff_result["after"] = "state: invited\n"
                module.exit_json(changed=True, diff=diff_result)

            invite_data = {
                "username": username,
                "roles": module.params["roles"],
                "groupRoleAssignments": group_role_assignments,
            }
            url = "{0}/orgs/{1}/invites".format(ATLAS_BASE, org_id)
            status, data = call_url(module, url, method="POST", data=invite_data, token=token)
            if status in (200, 201):
                changed = True
                diff_result["after"] = "state: invited\n"
            else:
                error = data.get("reason", "unknown")
                if "detail" in data:
                    error += ". Detail: " + data["detail"]
                module.fail_json(
                    msg="bad return code while inviting: %d. Error message: %s" % (status, error)
                )

    elif state == "absent":
        if pending_invite:
            diff_result["before"] = "state: invited\n"
            if module.check_mode:
                diff_result["after"] = "state: absent\n"
                module.exit_json(changed=True, diff=diff_result)

            url = "{0}/orgs/{1}/invites/{2}".format(ATLAS_BASE, org_id, pending_invite["id"])
            status, _ignored = call_url(module, url, method="DELETE", token=token)
            if status == 204:
                changed = True
                diff_result["after"] = "state: absent\n"
            else:
                module.fail_json(
                    msg="bad return code while deleting invite: %d" % status
                )
        else:
            diff_result["before"] = "state: absent\n"
            diff_result["after"] = "state: absent\n"

    module.exit_json(changed=changed, diff=diff_result)


if __name__ == "__main__":
    main()
