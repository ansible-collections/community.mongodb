# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
from collections import defaultdict

from ansible.module_utils.urls import fetch_url

try:
    from urllib import quote
except ImportError:
    # noinspection PyCompatibility, PyUnresolvedReferences
    from urllib.parse import (
        quote,
    )  # pylint: disable=locally-disabled, import-error, no-name-in-module

ATLAS_API_V2_VERSION = "2025-02-19"


def get_bearer_token(module, service_account_id, service_account_secret):
    """Obtain OAuth2 Bearer token using client_credentials grant."""
    import base64
    credentials = base64.b64encode(
        "{0}:{1}".format(service_account_id, service_account_secret).encode("utf-8")
    ).decode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": "Basic {0}".format(credentials),
    }
    rsp, info = fetch_url(
        module=module,
        url="https://cloud.mongodb.com/api/oauth/token",
        data="grant_type=client_credentials",
        headers=headers,
        method="POST",
    )
    if info["status"] != 200:
        module.fail_json(msg="Failed to obtain Atlas Bearer token. HTTP %d" % info["status"])
    return json.loads(rsp.read())["access_token"]


class AtlasAPIObject:
    module = None

    def __init__(
        self, module, object_name, group_id, path, data, data_is_array=False
    ):
        self.module = module
        self.path = path
        self.data = data
        self.group_id = group_id
        self.object_name = object_name
        self.data_is_array = data_is_array

        self.module.params["url_username"] = self.module.params["api_username"]
        self.module.params["url_password"] = self.module.params["api_password"]

    def call_url(self, path, data="", method="GET"):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self.data_is_array and data != "":
            data = "[" + data + "]"

        url = (
            "https://cloud.mongodb.com/api/atlas/v1.0/groups/"
            + self.group_id
            + path
        )
        rsp, info = fetch_url(
            module=self.module,
            url=url,
            data=data,
            headers=headers,
            method=method,
        )

        content = ""
        error = ""
        if rsp and info["status"] not in (204, 404):
            content = json.loads(rsp.read())
        if info["status"] >= 400:
            try:
                content = json.loads(info["body"])
                error = content["reason"]
                if "detail" in content:
                    error += ". Detail: " + content["detail"]
            except ValueError:
                error = info["msg"]
        if info["status"] < 0:
            error = info["msg"]
        return {"code": info["status"], "data": content, "error": error}

    def exists(self):
        additional_path = ""
        if self.path == "/databaseUsers":
            additional_path = "/" + self.module.params["database_name"]
        ret = self.call_url(
            path=self.path
            + additional_path
            + "/"
            + quote(self.data[self.object_name], "")
        )
        if ret["code"] == 200:
            return True
        return False

    def create(self):
        ret = self.call_url(
            path=self.path,
            data=self.module.jsonify(self.data),
            method="POST",
        )
        return ret

    def delete(self):
        additional_path = ""
        if self.path == "/databaseUsers":
            additional_path = "/" + self.module.params["database_name"]
        ret = self.call_url(
            path=self.path
            + additional_path
            + "/"
            + quote(self.data[self.object_name], ""),
            method="DELETE",
        )
        return ret

    def modify(self):
        additional_path = ""
        if self.path == "/databaseUsers":
            additional_path = "/" + self.module.params["database_name"]
        ret = self.call_url(
            path=self.path
            + additional_path
            + "/"
            + quote(self.data[self.object_name], ""),
            data=self.module.jsonify(self.data),
            method="PATCH",
        )
        return ret

    def diff(self):
        additional_path = ""
        if self.path == "/databaseUsers":
            additional_path = "/" + self.module.params["database_name"]
        ret = self.call_url(
            path=self.path
            + additional_path
            + "/"
            + quote(self.data[self.object_name], ""),
            method="GET",
        )

        data_from_atlas = json.loads(self.module.jsonify(ret["data"]))
        data_from_task = json.loads(self.module.jsonify(self.data))

        diff = defaultdict(dict)
        for key, value in data_from_atlas.items():
            if key in data_from_task.keys() and value != data_from_task[key]:
                diff["before"][key] = "{val}".format(val=value)
                diff["after"][key] = "{val}".format(val=data_from_task[key])
        return diff

    def update(self, state):
        changed = False
        diff_result = {"before": "", "after": ""}
        if self.exists():
            diff_result.update({"before": "state: present\n"})
            if state == "absent":
                if self.module.check_mode:
                    diff_result.update({"after": "state: absent\n"})
                    self.module.exit_json(
                        changed=True,
                        object_name=self.data[self.object_name],
                        diff=diff_result,
                    )
                else:
                    try:
                        ret = self.delete()
                        if ret["code"] == 204 or ret["code"] == 202:
                            changed = True
                            diff_result.update({"after": "state: absent\n"})
                        else:
                            self.module.fail_json(
                                msg="bad return code while deleting: %d. Error message: %s"
                                % (ret["code"], ret["error"])
                            )
                    except Exception as e:
                        self.module.fail_json(
                            msg="exception when deleting: " + str(e)
                        )

            else:
                diff_result.update(self.diff())
                if self.module.check_mode:
                    if diff_result["after"] != "":
                        changed = True
                    self.module.exit_json(
                        changed=changed,
                        object_name=self.data[self.object_name],
                        data=self.data,
                        diff=diff_result,
                    )
                if diff_result["after"] != "":
                    if self.path == "/whitelist":
                        ret = self.create()
                    else:
                        ret = self.modify()
                    if ret["code"] == 200 or ret["code"] == 201:
                        changed = True
                    else:
                        self.module.fail_json(
                            msg="bad return code while modifying: %d. Error message: %s"
                            % (ret["code"], ret["error"])
                        )

        else:
            diff_result.update({"before": "state: absent\n"})
            if state == "present":
                if self.module.check_mode:
                    changed = True
                    diff_result.update({"after": "state: created\n"})
                else:
                    try:
                        ret = self.create()
                        if ret["code"] == 201:
                            changed = True
                            diff_result.update({"after": "state: created\n"})
                        else:
                            self.module.fail_json(
                                msg="bad return code while creating: %d. Error message: %s"
                                % (ret["code"], ret["error"])
                            )
                    except Exception as e:
                        self.module.fail_json(
                            msg="exception while creating: " + str(e)
                        )
        return changed, diff_result


class AtlasAPIObjectV2(AtlasAPIObject):
    """Atlas API v2 variant supporting both OAuth2 Bearer (Service Account)
    and Digest authentication (API public/private key).

    Authentication priority:
      - If service_account_id and service_account_secret are provided: OAuth2 Bearer
      - If api_username and api_password are provided: Digest (same as AtlasAPIObject)

    Additional arguments vs AtlasAPIObject:
      - base_url             : full URL prefix replacing /api/atlas/v1.0/groups/{group_id}
      - service_account_id   : OAuth2 client ID (optional)
      - service_account_secret: OAuth2 client secret (optional)
    """

    def __init__(
        self,
        module,
        object_name,
        path,
        data,
        base_url,
        group_id="",
        data_is_array=False,
        service_account_id=None,
        service_account_secret=None,
        api_username=None,
        api_password=None,
    ):
        self.module = module
        self.path = path
        self.data = data
        self.group_id = group_id
        self.object_name = object_name
        self.data_is_array = data_is_array
        self._base_url = base_url

        if service_account_id and service_account_secret:
            self._auth_type = "bearer"
            self._bearer_token = get_bearer_token(module, service_account_id, service_account_secret)
        elif api_username and api_password:
            self._auth_type = "digest"
            self.module.params["url_username"] = api_username
            self.module.params["url_password"] = api_password
        else:
            module.fail_json(
                msg="Either service_account_id/service_account_secret or api_username/api_password must be provided."
            )

    def call_url(self, path, data="", method="GET"):
        headers = {
            "Accept": "application/vnd.atlas.{0}+json".format(ATLAS_API_V2_VERSION),
            "Content-Type": "application/vnd.atlas.{0}+json".format(ATLAS_API_V2_VERSION),
        }

        if self._auth_type == "bearer":
            headers["Authorization"] = "Bearer {0}".format(self._bearer_token)

        if self.data_is_array and data != "":
            data = "[" + data + "]"

        url = self._base_url + path
        rsp, info = fetch_url(
            module=self.module,
            url=url,
            data=data,
            headers=headers,
            method=method,
        )

        content = ""
        error = ""
        if rsp and info["status"] not in (204, 404):
            content = json.loads(rsp.read())
        if info["status"] >= 400:
            try:
                content = json.loads(info["body"])
                error = content.get("reason", "Unknown error")
                if "detail" in content:
                    error += ". Detail: " + content["detail"]
            except ValueError:
                error = info["msg"]
        if info["status"] < 0:
            error = info["msg"]
        return {"code": info["status"], "data": content, "error": error}
