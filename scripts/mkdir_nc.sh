#!/usr/bin/env bash

# Check if the required string argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <path>"
  exit 1
fi

TARGET_PATH="$1"
docker exec turmfrontend-web python manage.py mkdir_nc "$TARGET_PATH"
