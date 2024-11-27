#!/usr/bin/env bash

ruff format
ruff check --fix

djlint . --reformat
