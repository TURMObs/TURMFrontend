#!/usr/bin/env bash

docker-compose --profile test up -d
docker exec -it turmfrontend-web python manage.py test
