#!/bin/sh
set -e

# Activate the virtual environment
export PATH="/app/.venv/bin:$PATH"

# Wait for postgres
if [ -n "$POSTGRES_DB" ]; then
  echo "Waiting for PostgreSQL..."
  while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
s.connect(('${POSTGRES_HOST:-postgres}', ${POSTGRES_PORT:-5432}))
s.close()
" 2>/dev/null; do
    sleep 1
  done
  echo "PostgreSQL is ready."
fi

# Only run migrations and collect static files for the API server, not celery workers
if [ "$1" != "celery" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
fi

exec "$@"
