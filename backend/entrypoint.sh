#!/bin/sh
set -e

echo "=== Dummar Backend Entrypoint ==="
echo "Waiting for database to be ready..."

# Wait for PostgreSQL (max 30s) — required for both API and worker startup.
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

# When a custom command is supplied (e.g. the celery worker invoked via the
# docker-compose `command:` key), skip migrations + the API startup banner
# and exec the override directly. The backend container is the single source
# of truth for migrations, so secondary containers (worker, one-off jobs)
# must NOT race to run `alembic upgrade head`.
if [ "$#" -gt 0 ]; then
    echo "Custom command detected — exec: $*"
    exec "$@"
fi

echo "Running database migrations..."
if ! alembic upgrade head; then
    echo "FATAL: Database migrations failed."
    echo "FATAL: Refusing to start the API in an inconsistent schema state."
    echo "FATAL: Check DATABASE_URL connectivity and migration files in alembic/versions/."
    exit 1
fi
echo "Database migrations applied successfully."

# Verify OCR/Tesseract availability for contract intelligence
echo "=== OCR Engine Check ==="
if command -v tesseract > /dev/null 2>&1; then
    echo "Tesseract OCR: $(tesseract --version 2>&1 | head -1)"
    echo "Languages: $(tesseract --list-langs 2>&1 | tail -n +2 | tr '\n' ' ')"
else
    echo "Tesseract OCR: NOT INSTALLED (BasicTextExtractor will be used)"
fi

# Verify Arabic PDF font availability
if [ -f /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf ]; then
    echo "Arabic PDF font (DejaVu Sans): Available"
else
    echo "Arabic PDF font (DejaVu Sans): NOT FOUND — PDF export will use Helvetica fallback"
fi

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
