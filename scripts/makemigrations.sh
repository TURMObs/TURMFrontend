#!/usr/bin/env bash

docker-compose up -d
docker exec -it turmfrontend-web python manage.py makemigrations
