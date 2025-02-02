#!/usr/bin/env bash

set -e

echo "Fetching newest changes..."
git fetch origin deployment || exit 1
git checkout -B deployment origin/deployment || exit 1
git pull || exit 1

echo "Stopping server..."

docker compose down -v || exit 1
echo "Starting server..."
docker compose up -d --build || exit 1

echo "Deployment complete, newest version is up and running."
