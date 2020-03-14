#!/usr/bin/env bash
############################################################
# Author: Rhys Campbell                                    #
# Created: 2020.02.09                                      #
# Description: Runs molecle tests for the roles located in #
# roles/ when appropriate according to commits.            #
############################################################

cd ./plugins/modules;
export ANSIBLE_LIBRARY="$(pwd)";
cd ../../;

set -u;
set -e;

FILES=$(git diff --name-only HEAD~1 | wc -l | xargs);

echo "There are $FILES files in this commit.";

test_count=0;

declare -a role_list=();

for role in $(git diff --name-only HEAD~1 | grep roles/ | cut -d'/' -f -2 | sort | uniq); do
    if [[ -d "$role/molecule" ]]; then
      if [[ ! -f "$role/molecule/.travisignore" ]]; then
        echo "Adding $role to test queue"
        role_list+=( $role );
      else
        echo "The role $role has been specifically excluded from travis with a .travisignore file";
      fi;
    else
        echo "The role $role does not have a molecule sub-directoy so skipping tests."
    fi;
done

for role in "${role_list[@]}"; do
  echo "Executing tests for $role.";
  cd "$role"
  molecule test;
  cd ../../ && echo "Back in $(pwd)"; # back to project root
  test_count=$(( test_count + 1 ));
done;

if (( test_count > 0 )); then
  echo "Executed tests for a total of $test_count roles.";
else
  echo "No role tests executed on this run."
fi;
