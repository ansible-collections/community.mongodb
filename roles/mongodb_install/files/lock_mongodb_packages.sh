#!/usr/bin/env bash
# Hold mongodb-org packages on RHEL and Debian based systems

set -e;
set -u;

HOLD="$1";
PACKAGE_NAME="mongodb-org*"

if [[ "$HOLD" == "HOLD" ]], then
  if command -v yum &> /dev/null; then
    yum versionlock "$PACKAGE_NAME" && touch /root/mongo_version_lock.success;
  elif command -v dpkg  &> /dev/null; then
    echo "$PACKAGE_NAME hold" | sudo dpkg --set-selections && touch /root/mongo_version_lock.success;
  fi;
elif [[ "$HOLD" == "NOHOLD" ]], then
  if command -v yum &> /dev/null; then
    yum versionlock delete "$PACKAGE_NAME" && rm -rf /root/mongo_version_lock.success;
  elif command -v dpkg  &> /dev/null; then
    echo "$PACKAGE_NAME install" | sudo dpkg --set-selections && rm -rf /root/mongo_version_lock.success;
  fi;
else
  echo "No action taken";
fi;
