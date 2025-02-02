#!/usr/bin/env bash

# Check if the required string argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <observation name>"
  exit 1
fi

OBS_NAME="$1"
docker exec turmfrontend-web python manage.py create_test_observation "$OBS_NAME"
