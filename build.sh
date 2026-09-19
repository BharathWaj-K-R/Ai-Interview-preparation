#!/usr/bin/env bash
# Render build script — only install dependencies here.
# DB migrations run at start time via startCommand.
set -o errexit

pip install -r requirements.txt
