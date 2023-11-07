#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 T-Systems MMS
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: mongodb_atlas_cluster
short_description: Manage database clusters in Atlas
description:
  - The clusters module provides access to your cluster configurations.
  - The module lets you create, edit and delete clusters.
  - L(API Documentation,https://docs.atlas.mongodb.com/reference/api/clusters/)
author: "Martin Schurz (@schurzi)"
extends_documentation_fragment: community.mongodb.atlas_options
options:
  name:
    description:
      - Name of the cluster as it appears in Atlas. Once the cluster is created, its name cannot be changed.
    type: str
    required: True
  mongoDBMajorVersion:
    description:
      - Version of the cluster to deploy.
      - Atlas always deploys the cluster with the latest stable release of the specified version.
      - You can upgrade to a newer version of MongoDB when you modify a cluster.
    choices: [ "4.2", "4.4", "5.0", "6.0", "7.0" ]
    type: str
  clusterType:
    description:
      - Type of the cluster that you want to create.
    choices: [ "REPLICASET", "SHARDED" ]
    default: "REPLICASET"
    type: str
  replicationFactor:
    description:
      - Number of replica set members. Each member keeps a copy of your databases, providing high availability and data redundancy.
    choices: [ 3, 5, 7 ]
    default: 3
    type: int
  autoScaling:
    description:
      - Configure your cluster to automatically scale its storage and cluster tier.
    suboptions:
      diskGBEnabled:
        type: bool
        description:
          - Specifies whether disk auto-scaling is enabled. The default is true.
    required: False
    type: dict
  providerSettings:
    description:
      - Configuration for the provisioned servers on which MongoDB runs.
      - The available options are specific to the cloud service provider.
    suboptions:
      providerName:
        required: True
        type: str
        description:
          - Cloud service provider on which the servers are provisioned.
      regionName:
        required: True
        type: str
        description:
          - Physical location of your MongoDB cluster.
      instanceSizeName:
        required: True
        type: str
        description:
          - Atlas provides different cluster tiers, each with a default storage capacity and RAM size.
          - The cluster you select is used for all the data-bearing servers in your cluster tier.
    required: True
    type: dict
  diskSizeGB:
    description:
      - Capacity, in gigabytes, of the host's root volume. Increase this number to add capacity,
        up to a maximum possible value of 4096 (i.e., 4 TB). This value must be a positive integer.
    type: int
  providerBackupEnabled:
    description:
      - Flag that indicates if the cluster uses Cloud Backups for backups.
    type: bool
  pitEnabled:
    description:
      - Flag that indicates the cluster uses continuous cloud backups.
    type: bool
'''

EXAMPLES = '''
    - name: test cluster
      community.mongodb.mongodb_atlas_cluster:
        apiUsername: "API_user"
        apiPassword: "API_passwort_or_token"
        groupId: "GROUP_ID"
        name: "testcluster"
        mongoDBMajorVersion: "4.0"
        clusterType: "REPLICASET"
        providerSettings:
          providerName: "GCP"
          regionName: "EUROPE_WEST_3"
          instanceSizeName: "M10"
...
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_atlas import (
    AtlasAPIObject,
)


# ===========================================
# Module execution.
#
def main():
    # add our own arguments
    argument_spec = dict(
        state=dict(default="present", choices=["absent", "present"]),
        apiUsername=dict(required=True),
        apiPassword=dict(required=True, no_log=True),
        groupId=dict(required=True),
        name=dict(required=True),
        mongoDBMajorVersion=dict(
            choices=["4.2", "4.4", "5.0", "6.0", "7.0"]
        ),
        clusterType=dict(
            default="REPLICASET", choices=["REPLICASET", "SHARDED"]
        ),
        replicationFactor=dict(default=3, type="int", choices=[3, 5, 7]),
        autoScaling=dict(
            type="dict",
            options=dict(
                diskGBEnabled=dict(type="bool"),
            ),
        ),
        providerSettings=dict(
            type="dict",
            required=True,
            options=dict(
                providerName=dict(required=True),
                regionName=dict(required=True),
                instanceSizeName=dict(required=True),
            ),
        ),
        diskSizeGB=dict(type="int"),
        providerBackupEnabled=dict(type="bool"),
        pitEnabled=dict(type="bool"),
    )

    # Define the main module
    module = AnsibleModule(
        argument_spec=argument_spec, supports_check_mode=True
    )

    data = {
        "name": module.params["name"],
        "clusterType": module.params["clusterType"],
        "replicationFactor": module.params["replicationFactor"],
        "providerSettings": module.params["providerSettings"],
    }

    # handle optional options
    optional_vars = [
        "mongoDBMajorVersion",
        "autoScaling",
        "diskSizeGB",
        "providerBackupEnabled",
        "pitEnabled",
    ]

    for var in optional_vars:
        if var in module.params:
            data.update({var: module.params[var]})

    try:
        atlas = AtlasAPIObject(
            module=module,
            path="/clusters",
            object_name="name",
            groupId=module.params["groupId"],
            data=data,
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


# import module snippets
if __name__ == "__main__":
    main()
