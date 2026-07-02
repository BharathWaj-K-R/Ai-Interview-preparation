#!/usr/bin/env bash
# Render build script
set -o errexit

pip install -r requirements.txt
flask db upgrade
