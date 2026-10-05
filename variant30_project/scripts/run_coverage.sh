#!/usr/bin/env bash
set -e
coverage run --branch -m pytest -q
coverage report -m
