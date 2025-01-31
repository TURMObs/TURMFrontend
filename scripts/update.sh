#!/usr/bin/env bash

DAYS=${1:-0}

docker exec turmfrontend-web python manage.py update_observations process_pending_deletion
docker exec turmfrontend-web python manage.py update_observations --days "$DAYS"
