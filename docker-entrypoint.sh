#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-api}" = "worker" ]; then
    echo "Starting image worker..."
    exec python -m app.workers.image_worker
fi

echo "Running database migrations..."
sqlspec --config app.core.database.db upgrade --no-prompt

echo "Starting Gunicorn..."
exec gunicorn -c gunicorn.conf.py main:api
