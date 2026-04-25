FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (including fonts for Arabic PDF export)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Create non-root user and set up directories.
# --create-home ensures /home/appuser exists and is owned by appuser so that
# gunicorn's arbiter control socket (and any other tool that writes to $HOME)
# can initialise correctly. Without it gunicorn logs
# "[ERROR] Control server error: [Errno 13] Permission denied: '/home/appuser'"
# which degrades worker lifecycle management and can cause intermittent 502s.
RUN mkdir -p /app/uploads && \
    useradd --system --create-home appuser && \
    chown -R appuser:appuser /app/uploads && \
    chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

# Use entrypoint for auto-migration + gunicorn startup
ENTRYPOINT ["/app/entrypoint.sh"]
