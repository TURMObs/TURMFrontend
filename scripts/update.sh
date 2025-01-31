#!/usr/bin/env bash

DAYS=${1:-0}

docker exec turmfrontend-web python manage.py update_observations delete_observations
docker exec turmfrontend-web python manage.py update_observations clean_up_users
docker exec turmfrontend-web python manage.py update_observations --days "$DAYS"
