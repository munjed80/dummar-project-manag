#!/bin/bash
# =============================================================================
# Dummar Project Management — Production Deployment Script
# =============================================================================
# Automates building and deploying the Dummar application stack on a VPS.
#
# Usage:
#   ./deploy.sh                         # Deploy or update the application
#   ./deploy.sh --seed                  # Deploy and load seed data (first-time only)
#   ./deploy.sh --rebuild               # Force rebuild of all Docker images
#   ./deploy.sh --domain=example.com    # Set CORS_ORIGINS for your domain
#
# Prerequisites:
#   - Docker and Docker Compose (v2) installed
#   - .env file configured (generated from template if missing)
#   - Node.js 20+ (for frontend build — required by Vite 8)
#   - Port 80 (and 443 if SSL) available
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colors & helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()    { echo -e "\n${CYAN}▸ $*${NC}"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
SEED_DATA=false
FORCE_REBUILD=false
DOMAIN=""

for arg in "$@"; do
    case "$arg" in
        --seed)    SEED_DATA=true ;;
        --rebuild) FORCE_REBUILD=true ;;
        --domain=*)
            DOMAIN="${arg#--domain=}"
            ;;
        --help|-h)
            head -17 "$0" | tail -14
            exit 0
            ;;
        *)
            error "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Resolve project root (directory containing this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
info "Project directory: $SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
step "Running pre-flight checks"

# Docker
if ! command -v docker &>/dev/null; then
    error "Docker is not installed. Install it first: https://docs.docker.com/engine/install/"
    exit 1
fi
success "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# Docker Compose (v2 plugin or standalone)
if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    error "Docker Compose is not installed."
    exit 1
fi
success "Docker Compose available ($COMPOSE)"

# Node.js (v20+ required for Vite 8 + Tailwind CSS 4)
if ! command -v node &>/dev/null; then
    error "Node.js is not installed. Required for frontend build (v20+)."
    exit 1
fi
NODE_MAJOR=$(node --version | cut -d. -f1 | tr -d 'v')
if [ "$NODE_MAJOR" -lt 20 ]; then
    error "Node.js v20+ required (found: $(node --version)). Upgrade: https://nodejs.org/"
    exit 1
fi
success "Node.js $(node --version)"

# ---------------------------------------------------------------------------
# Detect first-time deployment
# ---------------------------------------------------------------------------
FIRST_DEPLOY=false
if ! $COMPOSE ps --quiet 2>/dev/null | grep -q .; then
    FIRST_DEPLOY=true
    info "First-time deployment detected."
else
    info "Existing deployment detected — performing update."
fi

# ---------------------------------------------------------------------------
# Environment file
# ---------------------------------------------------------------------------
step "Checking environment configuration"

if [ ! -f .env ]; then
    warn ".env file not found — generating from template."

    generate_secret() {
        openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '\n'
    }

    DB_PASS="$(generate_secret)"
    SECRET="$(generate_secret)"

    cat > .env <<EOF
# =============================================================================
# Dummar Project — Production Environment
# Generated on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# =============================================================================

# Database — REQUIRED. Stack refuses to start if unset.
DB_PASSWORD=${DB_PASS}

# Application secret — REQUIRED. Keep this safe! Stack refuses to start if unset.
SECRET_KEY=${SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=480

# CORS — set to your public domain
CORS_ORIGINS=http://localhost

# Deployment environment.
# In "production" the API documentation (/docs, /redoc, /openapi.json) is
# disabled by default. Set ENABLE_API_DOCS=true to re-enable, or set
# ENVIRONMENT=development for local work.
ENVIRONMENT=production
ENABLE_API_DOCS=false

# Backend port binding.
# Default 127.0.0.1 means the backend is reachable ONLY from the local host
# (i.e. through nginx). Set to 0.0.0.0 only if you intentionally want to
# expose port 8000 directly (e.g. behind an external load balancer).
BACKEND_BIND=127.0.0.1

# Nginx port (change if fronted by another reverse proxy)
HTTP_PORT=80

# Logging
LOG_LEVEL=info

# Gunicorn workers — adjust to your server: 2×CPU + 1 (e.g. 2-core → 5)
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120

# Email (optional)
SMTP_ENABLED=false
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@dummar.gov.sy
EOF

    success ".env generated with random secrets."
    warn "Review .env and update CORS_ORIGINS with your domain before going live."
else
    success ".env file present."

    # Validate required secrets are non-empty (not just present as keys)
    if ! grep -qE '^DB_PASSWORD=.+' .env; then
        error ".env is missing DB_PASSWORD. The stack will refuse to start."
        error "Add a strong value: DB_PASSWORD=\$(openssl rand -base64 32)"
        exit 1
    fi
    if ! grep -qE '^SECRET_KEY=.+' .env; then
        error ".env is missing SECRET_KEY. The stack will refuse to start."
        error "Add a strong value: SECRET_KEY=\$(openssl rand -base64 32)"
        exit 1
    fi

    # Refuse to launch with the well-known insecure values that older versions
    # of this script and older docs may have produced or that someone may have
    # copied from .env.example.
    if grep -qE '^DB_PASSWORD=dummar_password\s*$' .env; then
        error ".env contains the legacy default DB_PASSWORD=dummar_password — refusing to deploy."
        error "Rotate it: sed -i 's|^DB_PASSWORD=.*|DB_PASSWORD='\"\$(openssl rand -base64 32)\"'|' .env"
        exit 1
    fi
    if grep -qE '^SECRET_KEY=dummar-secret-key' .env; then
        error ".env contains the legacy default SECRET_KEY — refusing to deploy."
        error "Rotate it: sed -i 's|^SECRET_KEY=.*|SECRET_KEY='\"\$(openssl rand -base64 32)\"'|' .env"
        exit 1
    fi
    success ".env secrets look safe (no legacy defaults detected)."
fi

# If --domain was specified, update CORS_ORIGINS in .env
if [ -n "$DOMAIN" ]; then
    if [ -f .env ]; then
        # Determine scheme (https if certs exist, http otherwise)
        if [ -d certs ] || [ -d /etc/letsencrypt/live/"$DOMAIN" ]; then
            SCHEME="https"
        else
            SCHEME="http"
        fi
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=${SCHEME}://${DOMAIN}|" .env
        success "CORS_ORIGINS set to ${SCHEME}://${DOMAIN}"
    fi
fi

# Source .env for local use (read only needed vars, not sensitive ones)
HTTP_PORT=$(grep '^HTTP_PORT=' .env 2>/dev/null | cut -d= -f2 || echo "80")

# ---------------------------------------------------------------------------
# Frontend build
# ---------------------------------------------------------------------------
step "Building frontend"

info "Installing dependencies…"
npm ci --prefer-offline --no-audit --no-fund 2>&1 | tail -5

info "Running production build…"
npm run build 2>&1 | tail -3

if [ ! -d dist ] || [ ! -f dist/index.html ]; then
    error "Frontend build failed — dist/index.html not found."
    exit 1
fi
success "Frontend built → dist/ ($(du -sh dist | awk '{print $1}'))"

# ---------------------------------------------------------------------------
# Docker build & deploy
# ---------------------------------------------------------------------------
step "Building and starting Docker services"

BUILD_FLAGS=""
if [ "$FORCE_REBUILD" = true ]; then
    BUILD_FLAGS="--build --force-recreate --no-deps"
    info "Forcing full rebuild of all images."
fi

# Pull base images to get security patches
$COMPOSE pull db nginx 2>&1 | tail -2

# Build and start
# shellcheck disable=SC2086
$COMPOSE up -d --build $BUILD_FLAGS 2>&1 | tail -5

success "Docker services started."

# ---------------------------------------------------------------------------
# Wait for health checks
# ---------------------------------------------------------------------------
step "Waiting for services to become healthy"

MAX_WAIT=120
INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    DB_HEALTH=$($COMPOSE ps db --format '{{.Health}}' 2>/dev/null || echo "unknown")
    BACKEND_HEALTH=$($COMPOSE ps backend --format '{{.Health}}' 2>/dev/null || echo "unknown")

    if [ "$DB_HEALTH" = "healthy" ] && [ "$BACKEND_HEALTH" = "healthy" ]; then
        success "All services healthy (${ELAPSED}s)."
        break
    fi

    info "db=${DB_HEALTH}  backend=${BACKEND_HEALTH}  (${ELAPSED}s / ${MAX_WAIT}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    warn "Timeout waiting for services. Checking status…"
    $COMPOSE ps
    error "Some services may not be healthy. Check logs: $COMPOSE logs --tail 50"
    exit 1
fi

# ---------------------------------------------------------------------------
# Seed data (first deployment only, when requested)
# ---------------------------------------------------------------------------
if [ "$SEED_DATA" = true ]; then
    step "Loading seed data"

    if [ "$FIRST_DEPLOY" = true ] || [ "$FORCE_REBUILD" = true ]; then
        info "Running seed script inside backend container…"
        info "Mode: STRONG RANDOM PASSWORDS (production-safe). Credentials will"
        info "be written to /app/seed_credentials.txt inside the backend container."
        $COMPOSE exec -T backend python -m app.scripts.seed_data 2>&1 | tail -10
        success "Seed data loaded."
        warn "IMPORTANT: Retrieve and securely distribute the generated passwords:"
        warn "  $COMPOSE exec backend cat /app/seed_credentials.txt"
        warn "Then DELETE the file:"
        warn "  $COMPOSE exec backend rm /app/seed_credentials.txt"
        warn "Force operators to rotate their passwords on first login."
    else
        warn "Skipping seed data — not a first-time deployment. Use --rebuild to force."
    fi
fi

# ---------------------------------------------------------------------------
# Post-deployment verification
# ---------------------------------------------------------------------------
step "Post-deployment verification"

HTTP_PORT="${HTTP_PORT:-80}"
BASE_URL="http://localhost:${HTTP_PORT}"
PASS=0
FAIL=0

check_endpoint() {
    local label="$1"
    local url="$2"
    local expected_code="${3:-200}"

    status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || echo "000")
    if [ "$status" = "$expected_code" ]; then
        success "$label → HTTP $status"
        PASS=$((PASS + 1))
    else
        error "$label → HTTP $status (expected $expected_code)"
        FAIL=$((FAIL + 1))
    fi
}

check_endpoint "Frontend (SPA)"     "$BASE_URL/"
check_endpoint "API health/ready"   "$BASE_URL/api/health/ready"  200
check_endpoint "API root"            "$BASE_URL/api/"              200

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
if [ $FAIL -eq 0 ]; then
    echo -e "  ${GREEN}✓ Deployment successful${NC}  ($PASS/$((PASS + FAIL)) checks passed)"
else
    echo -e "  ${YELLOW}⚠ Deployment completed with issues${NC}  ($PASS/$((PASS + FAIL)) checks passed)"
fi
echo "=========================================="
echo ""
info "Services:  $COMPOSE ps"
info "Logs:      $COMPOSE logs -f"
info "Stop:      $COMPOSE down"
if [ -f ssl-setup.sh ] && [ ! -d certs ]; then
    echo ""
    info "SSL:       ./ssl-setup.sh <your-domain.com>  (to enable HTTPS)"
fi
echo ""

exit $FAIL
