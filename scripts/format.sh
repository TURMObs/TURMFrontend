#!/usr/bin/env bash

ruff format
ruff check --fix

djlint . --reformat

prettier --ignore-path ./.gitignore --write "./**/*.{js,css}"
