#!/usr/bin/env bash
############################################################
# Author: Rhys Campbell                                    #
# Created: 2020.02.09                                      #
# Description: Runs molecle tests for the roles located in #
# roles/ when appropriate according to commits.            #
############################################################

set -u;
set -e;

pwd;

FILES=$(git diff --name-only HEAD~1 | wc -l | xargs);
ROLES=$(git diff --name-only HEAD~1 | grep roles/ | cut -d'/' -f -2 | sort | uniq)

echo "There are $FILES files in this commit.";
echo "This commit touches $(echo "${ROLES}" | wc -w) roles: $(echo "${ROLES//roles\/}" | tr '\n' ' ')"

test_count=0;

declare -a role_list=();

# https://docs.travis-ci.com/user/environment-variables/#default-environment-variables
# vars used below: TRAVIS, TRAVIS_BRANCH, TRAVIS_TAG

if [ -z "${TRAVIS:+x}" ]; then
  # This should only be triggered if running outside of travis (eg for local testing)
  for role in ${ROLES}; do
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
else  # MONGODB_ROLE should be defined
  set +u;
  # MONGODB_ROLE is set per travis job to one role.
  if [ -z "$MONGODB_ROLE" ]; then
    echo "MONGODB_ROLE was not set as expected.";
  elif [ -n "${TRAVIS_TAG}" ] || [[ "master" == "${TRAVIS_BRANCH}" ]] || [[ "$ROLES" == *"${MONGODB_ROLE}"* ]]; then
    # Include all roles (one per Travis job) when this is:
    #   a tag build (TRAVIS_TAG is set)
    #   a master branch build or a PR targetting the master branch (TRAVIS_BRANCH == master)
    # Include only changed roles when this is:
    #  a non-master push or PR and the current job's MONGODB_ROLE was changed.
    role_list+=( "$MONGODB_ROLE" );
  fi;
  set -u;
fi;

# prevent timeout during idempotence runs where no output for over 10min is common
progress_file=$(mktemp)
progress() {
  while [ -e "${progress_file}" ]; do
    sleep 300  # 5 min (< 10min travis timeout)
    echo -ne "\n.\n"
  done
}
progress &
if [ ${#role_list[@]} -ne 0 ]; then
  for role in "${role_list[@]}"; do
    echo "Executing tests for $role.";
    cd "$role"
    molecule --debug test;
    cd ../../ && echo "Back in $(pwd)"; # back to project root
    test_count=$(( test_count + 1 ));
  done;

  if (( test_count > 0 )); then
    echo "Executed tests for a total of $test_count roles.";
  else
    echo "No role tests executed on this run."
  fi;
else
  echo "No roles in commit. Bailing without doing anything"
fi;
rm -f "${progress_file}"
