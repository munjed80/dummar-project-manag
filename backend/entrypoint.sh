#!/bin/sh
set -e

echo "=== Dummar Backend Entrypoint ==="
echo "Waiting for database to be ready..."

# Wait for PostgreSQL (max 30s)
MAX_RETRIES=30
RETRY=0
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-dummar}" -q 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        echo "ERROR: Database not ready after ${MAX_RETRIES}s. Proceeding anyway..."
        break
    fi
    echo "Waiting for database... ($RETRY/$MAX_RETRIES)"
    sleep 1
done

echo "Running database migrations..."
alembic upgrade head || {
    echo "WARNING: Migrations failed. The application may not work correctly."
    echo "Check DATABASE_URL and migration files."
}

echo "Starting Dummar API server..."
exec gunicorn app.main:app \
    --workers "${GUNICORN_WORKERS:-4}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --graceful-timeout 30 \
    --keep-alive 5
