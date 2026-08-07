#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-api}" = "worker" ]; then
    echo "Starting image worker..."
    exec python -m app.workers.image_worker
fi

if [ "${1:-api}" = "email-worker" ]; then
    echo "Starting email worker..."
    exec python -m app.workers.email_worker
fi

echo "Running database migrations..."
sqlspec upgrade --no-prompt

echo "Starting Gunicorn..."
exec "$@"
