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

# Detect whether a Let's Encrypt cert file exists. We CANNOT rely on a plain
# `[ -f "$cert" ]` because /etc/letsencrypt/{live,archive} are mode 0700
# root:root on a standard install. When this script is run by the typical
# non-root deploy user (who only needs docker-socket access, not full root),
# that test silently returns false even when the cert is present. The
# resulting failure mode was: SSL self-heal skipped → nginx.conf stays
# HTTP-only after `git pull` → no `listen 443 ssl` → docker-proxy resets
# every connection on 443 → curl reports SSL_SYSCALL and Cloudflare
# returns 521.
#
# Fall back to the docker daemon (which always has root via the socket) by
# running a tiny throw-away container against the same nginx:alpine image
# the stack already uses. The cert path is passed via env (CERT_PATH) so
# it is not subject to shell interpolation/quoting inside the container.
cert_present() {
    local cert="$1"
    [ -r "$cert" ] && return 0
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        docker run --rm \
            -e CERT_PATH="$cert" \
            -v /etc/letsencrypt:/etc/letsencrypt:ro \
            --entrypoint sh nginx:alpine \
            -c '[ -f "$CERT_PATH" ]' >/dev/null 2>&1 && return 0
    fi
    return 1
}

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
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=120
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
    LE_CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"

    if [ -f .env ]; then
        # Determine scheme (https if certs exist, http otherwise).
        # cert_present() (defined near the top) handles the non-root /
        # 0700-permissions case via a docker fallback.
        if [ -d certs ] || cert_present "$LE_CERT"; then
            SCHEME="https"
        else
            SCHEME="http"
        fi
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=${SCHEME}://${DOMAIN}|" .env
        success "CORS_ORIGINS set to ${SCHEME}://${DOMAIN}"
    fi

    # ---------------------------------------------------------------------
    # SSL self-heal: if a Let's Encrypt cert already exists for this domain
    # but nginx.conf is the HTTP-only template (which happens after every
    # `git pull` — git restores the repo's nginx.conf and silently overwrites
    # the on-VPS SSL version), automatically re-apply nginx-ssl.conf so the
    # next nginx restart serves HTTPS instead of falling back to HTTP.
    #
    # This makes  `git pull && ./deploy.sh --rebuild --domain=X`  idempotent
    # for HTTPS — no hidden manual edits required on the VPS.
    # ---------------------------------------------------------------------
    if cert_present "$LE_CERT" && [ -f nginx-ssl.conf ]; then
        # Detect whether the live nginx.conf is already SSL-enabled. We look
        # for the `listen 443 ssl` directive AND the substituted server_name
        # (i.e. DOMAIN_PLACEHOLDER has been replaced with the real domain).
        NEEDS_SSL_APPLY=true
        if [ -f nginx.conf ] \
           && grep -q 'listen 443 ssl' nginx.conf \
           && grep -q "server_name ${DOMAIN}" nginx.conf \
           && ! grep -q 'DOMAIN_PLACEHOLDER' nginx.conf; then
            NEEDS_SSL_APPLY=false
        fi

        if [ "$NEEDS_SSL_APPLY" = true ]; then
            warn "SSL cert exists for ${DOMAIN} but nginx.conf is not the SSL"
            warn "version (likely overwritten by git pull). Re-applying SSL config…"
            cp nginx-ssl.conf nginx.conf
            sed -i "s/DOMAIN_PLACEHOLDER/${DOMAIN}/g" nginx.conf
            success "nginx.conf re-generated from nginx-ssl.conf for ${DOMAIN}."
        else
            info "nginx.conf already configured for HTTPS on ${DOMAIN} — no change."
        fi
    elif [ -n "$DOMAIN" ] && ! cert_present "$LE_CERT"; then
        info "No Let's Encrypt cert at ${LE_CERT} yet — staying on HTTP nginx.conf."
        info "Run  sudo ./ssl-setup.sh ${DOMAIN} --auto  once to enable HTTPS."
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

# Pin production-safe frontend env values for the build. Vite bakes VITE_*
# into the bundle at build time, so any stray .env / .env.local on the VPS
# with a localhost fallback would otherwise silently poison the production
# bundle on every rebuild. We therefore EXPORT the safe defaults in-process
# and let them take precedence over any file-based value.
#
# Override ONLY if the operator explicitly set them in the current shell
# (e.g. for a non-standard reverse-proxy mount point).
: "${VITE_API_BASE_URL:=/api}"
: "${VITE_FILES_BASE_URL:=}"
export VITE_API_BASE_URL VITE_FILES_BASE_URL
info "Frontend build env: VITE_API_BASE_URL='${VITE_API_BASE_URL}' VITE_FILES_BASE_URL='${VITE_FILES_BASE_URL}'"

info "Running production build…"
npm run build 2>&1 | tail -3

if [ ! -d dist ] || [ ! -f dist/index.html ]; then
    error "Frontend build failed — dist/index.html not found."
    exit 1
fi

# Fail loud if the legacy localhost fallback somehow leaked into the bundle.
# This protects against operator mistakes (e.g. a leftover VITE_API_BASE_URL=
# http://localhost:8000 in .env.production on the VPS).
if grep -rq 'http://localhost:8000' dist/assets 2>/dev/null; then
    error "dist/ bundle contains 'http://localhost:8000' — refusing to deploy."
    error "This would break login/auth in production. Remove the localhost"
    error "value from .env / .env.production / .env.local and re-run deploy.sh."
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
        info "be written to /tmp/seed_credentials.txt inside the backend container."
        $COMPOSE exec -T backend python -m app.scripts.seed_data 2>&1 | tail -10
        success "Seed data loaded."
        warn "IMPORTANT: Retrieve and securely distribute the generated passwords:"
        warn "  $COMPOSE exec backend cat /tmp/seed_credentials.txt"
        warn "Then DELETE the file:"
        warn "  $COMPOSE exec backend rm /tmp/seed_credentials.txt"
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

# ---------------------------------------------------------------------------
# Detect whether nginx is running in SSL mode before running local probes.
# When SSL is active, every http://localhost request gets a 301 redirect to
# HTTPS — making the three checks below always fail with "expected 200, got
# 301" even though the stack is working correctly. In that case we skip the
# plain-HTTP local probes (the HTTPS local check below exercises the same
# paths) to avoid false [ERROR] lines that mislead the operator.
# ---------------------------------------------------------------------------
SSL_ENABLED=false
if [ -f nginx.conf ] && grep -q 'listen 443 ssl' nginx.conf; then
    SSL_ENABLED=true
fi

if [ "$SSL_ENABLED" = false ]; then
    check_endpoint "Frontend (SPA)"     "$BASE_URL/"
    check_endpoint "API health/ready"   "$BASE_URL/api/health/ready"  200
    check_endpoint "API root"            "$BASE_URL/api/"              200
else
    info "SSL mode active — skipping plain-HTTP local probes (all HTTP requests redirect 301→HTTPS)."
    info "HTTPS local probes and public endpoint checks below cover the same paths."
fi

# ---------------------------------------------------------------------------
# Local HTTPS acceptance probe — the test that previously caught no one out.
#
# We trigger this whenever the loaded nginx.conf is actually SSL-enabled
# (i.e. has a `listen 443 ssl` block). Checking the on-disk nginx.conf is
# the most reliable signal — it works for non-root operators and makes no
# assumptions about /etc/letsencrypt permissions, which were the original
# trip-wire that masked this regression.
#
# This check runs ON the VPS against `https://localhost`, so it bypasses
# Cloudflare entirely and exercises the origin TLS stack directly. Without
# it, an HTTP-only nginx.conf would happily pass the public HTTPS probe via
# a cached/stale Cloudflare response or be silently absent (the previous
# behavior), letting CF return 521 in production.
# ---------------------------------------------------------------------------

if [ "$SSL_ENABLED" = true ]; then
    HTTPS_PORT_LOCAL=$(grep '^HTTPS_PORT=' .env 2>/dev/null | cut -d= -f2 || echo "443")
    HTTPS_PORT_LOCAL="${HTTPS_PORT_LOCAL:-443}"

    info "SSL is enabled in nginx.conf — verifying origin TLS on localhost…"

    # Probe https://localhost directly. -k because the cert is for $DOMAIN,
    # not "localhost". A working TLS stack returns 200/301/etc.; a broken
    # one (no listen 443, missing cert, bad config) yields curl exit code
    # ≠0 and HTTP 000 — which we treat as a hard deploy failure so the
    # SSL_SYSCALL / Cloudflare-521 regression cannot pass silently again.
    https_status=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 \
        "https://localhost:${HTTPS_PORT_LOCAL}/" 2>/dev/null || echo "000")
    if [ "$https_status" != "000" ] && [ "$https_status" != "521" ]; then
        success "HTTPS origin (https://localhost) → HTTP $https_status"
        PASS=$((PASS + 1))
    else
        error "HTTPS origin (https://localhost) → curl failed (status=$https_status)"
        error "  nginx.conf has 'listen 443 ssl' but the TLS handshake on the"
        error "  origin failed. Check 'docker compose logs nginx' and verify"
        error "  /etc/letsencrypt/live/${DOMAIN:-your-domain}/ contains fullchain.pem"
        error "  and privkey.pem and is mounted into the nginx container."
        FAIL=$((FAIL + 1))
    fi

    # HTTP → HTTPS redirect on the origin (catches accidental HTTP-only
    # regressions where /nginx-health works but the catch-all is missing).
    redirect_status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
        -H "Host: ${DOMAIN:-localhost}" "$BASE_URL/" 2>/dev/null || echo "000")
    if [ "$redirect_status" = "301" ] || [ "$redirect_status" = "302" ]; then
        success "HTTP → HTTPS redirect on origin → HTTP $redirect_status"
        PASS=$((PASS + 1))
    else
        warn "HTTP → HTTPS redirect on origin → HTTP $redirect_status (expected 301/302)"
    fi
fi

# When --domain was passed AND a Let's Encrypt cert exists, also probe the
# real public HTTPS endpoint. This catches "nginx is healthy locally but TLS
# is broken" regressions (e.g. cert mount path wrong, HSTS issue).
if [ -n "$DOMAIN" ] && cert_present "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"; then
    check_endpoint "HTTPS frontend"      "https://${DOMAIN}/"                200
    check_endpoint "HTTPS health/ready"  "https://${DOMAIN}/api/health/ready" 200
fi

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

# ---------------------------------------------------------------------------
# Seed credentials surfacing
# ---------------------------------------------------------------------------
# If a seed_credentials.txt file is present inside the backend container,
# always remind the operator how to retrieve and delete it — even when
# --seed was NOT passed this run. This protects against the case where the
# operator forgets they ran a seed earlier and leaves cleartext credentials
# sitting on disk inside the container.
SEED_CRED_PATH="${SEED_CREDENTIALS_FILE:-/tmp/seed_credentials.txt}"
if $COMPOSE exec -T backend test -f "$SEED_CRED_PATH" 2>/dev/null; then
    echo ""
    warn "Seed credentials file detected inside backend container: $SEED_CRED_PATH"
    warn "  Read:    $COMPOSE exec backend cat $SEED_CRED_PATH"
    warn "  Delete:  $COMPOSE exec backend rm $SEED_CRED_PATH"
    warn "Distribute via a secure channel and DELETE the file once recorded."
fi
echo ""

exit $FAIL
