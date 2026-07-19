#!/usr/bin/env bash
set -euo pipefail

echo "Running database migrations..."
sqlspec --config app.core.database.db upgrade --no-prompt

echo "Starting Gunicorn..."
exec gunicorn -c gunicorn.conf.py main:api
