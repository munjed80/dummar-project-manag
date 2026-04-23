#!/bin/bash
# =============================================================================
# Dummar Project Management — Let's Encrypt SSL Setup
# =============================================================================
# Obtains a free TLS certificate from Let's Encrypt and configures auto-renewal.
#
# Usage:
#   ./ssl-setup.sh example.com
#   ./ssl-setup.sh example.com --auto      # Auto-configure nginx + .env after cert
#   ./ssl-setup.sh example.com --webroot   # Use webroot mode (nginx stays up)
#
# Prerequisites:
#   1. A registered domain name pointing to this server's public IP.
#   2. Port 80 open and reachable from the internet.
#   3. certbot installed  (apt install certbot)
#   4. Run as root or with sudo.
#
# When --auto is used, the script will:
#   - Render nginx-ssl.conf into a gitignored nginx-active.conf with the
#     real domain substituted (the tracked nginx.conf is NEVER overwritten,
#     so `git reset --hard origin/main` no longer breaks HTTPS).
#   - Persist NGINX_CONF_FILE=./nginx-active.conf and DOMAIN=<domain> in .env
#     so docker-compose (and the next ./deploy.sh --rebuild) automatically
#     keep using the SSL config without any further manual edits.
#   - Update CORS_ORIGINS in .env to https://<domain>.
#   - Restart the nginx container.
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
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()    { echo -e "\n${CYAN}▸ $*${NC}"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
if [ $# -lt 1 ]; then
    echo "Usage: $0 <domain> [--auto] [--webroot]"
    echo "  domain    Your fully-qualified domain name (e.g. dummar.example.com)"
    echo "  --auto    Auto-configure nginx, docker-compose.yml, and .env for SSL"
    echo "  --webroot Use webroot plugin instead of standalone (keeps nginx running)"
    exit 1
fi

DOMAIN="$1"
MODE="standalone"
WEBROOT_PATH="/var/www/certbot"
AUTO_CONFIGURE=false

for arg in "${@:2}"; do
    case "$arg" in
        --webroot) MODE="webroot" ;;
        --auto)    AUTO_CONFIGURE=true ;;
        *)
            error "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

info "Domain:  $DOMAIN"
info "Mode:    $MODE"
info "Auto:    $AUTO_CONFIGURE"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
step "Checking prerequisites"

# Must be root
if [ "$(id -u)" -ne 0 ]; then
    error "This script must be run as root (or with sudo)."
    exit 1
fi
success "Running as root."

# certbot
if ! command -v certbot &>/dev/null; then
    error "certbot is not installed."
    echo ""
    echo "  Install it with:"
    echo "    Ubuntu/Debian:  apt update && apt install -y certbot"
    echo "    CentOS/RHEL:    yum install -y certbot"
    echo "    Snap:           snap install --classic certbot"
    echo ""
    exit 1
fi
success "certbot $(certbot --version 2>&1 | awk '{print $NF}')"

# ---------------------------------------------------------------------------
# DNS validation
# ---------------------------------------------------------------------------
step "Validating DNS for $DOMAIN"

SERVER_IP=$(curl -4 -s --max-time 5 https://ifconfig.me 2>/dev/null || echo "unknown")
DNS_IP=$(dig +short "$DOMAIN" A 2>/dev/null | head -1 || echo "")

if [ -z "$DNS_IP" ]; then
    warn "Could not resolve $DOMAIN via DNS."
    echo ""
    echo "  Make sure you have an A record pointing to this server:"
    echo "    Type:  A"
    echo "    Name:  $DOMAIN"
    echo "    Value: $SERVER_IP"
    echo ""
    echo "  DNS changes can take up to 48 hours to propagate."
    echo ""
    read -rp "Continue anyway? (y/N) " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        info "Aborting. Set up DNS first, then re-run this script."
        exit 0
    fi
elif [ "$DNS_IP" != "$SERVER_IP" ]; then
    warn "DNS mismatch: $DOMAIN resolves to $DNS_IP, but this server is $SERVER_IP."
    echo "  Let's Encrypt validation may fail if traffic doesn't reach this server."
    read -rp "Continue anyway? (y/N) " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    success "$DOMAIN → $DNS_IP (matches this server)."
fi

# ---------------------------------------------------------------------------
# Stop nginx if using standalone mode
# ---------------------------------------------------------------------------
if [ "$MODE" = "standalone" ]; then
    step "Freeing port 80 for standalone verification"

    if docker compose ps nginx --format '{{.State}}' 2>/dev/null | grep -qi running; then
        info "Stopping nginx container…"
        docker compose stop nginx
        success "nginx stopped."
    elif systemctl is-active --quiet nginx 2>/dev/null; then
        info "Stopping system nginx…"
        systemctl stop nginx
        success "nginx stopped."
    else
        success "Port 80 appears free."
    fi
fi

# ---------------------------------------------------------------------------
# Obtain certificate
# ---------------------------------------------------------------------------
step "Requesting certificate from Let's Encrypt"

# Note: --register-unsafely-without-email skips expiration/security emails.
# For production, consider using: --email admin@yourdomain.com instead.
CERTBOT_FLAGS=(
    --non-interactive
    --agree-tos
    --register-unsafely-without-email
    -d "$DOMAIN"
)

if [ "$MODE" = "webroot" ]; then
    mkdir -p "$WEBROOT_PATH"
    certbot certonly --webroot -w "$WEBROOT_PATH" "${CERTBOT_FLAGS[@]}"
else
    certbot certonly --standalone "${CERTBOT_FLAGS[@]}"
fi

CERT_DIR="/etc/letsencrypt/live/$DOMAIN"

if [ ! -f "$CERT_DIR/fullchain.pem" ]; then
    error "Certificate files not found in $CERT_DIR."
    exit 1
fi
success "Certificate obtained:"
info "  fullchain → $CERT_DIR/fullchain.pem"
info "  privkey   → $CERT_DIR/privkey.pem"

# ---------------------------------------------------------------------------
# Prepare certs for Docker volume mount
# ---------------------------------------------------------------------------
step "Preparing certificates for Docker"

DOCKER_CERT_DIR="./certs"
mkdir -p "$DOCKER_CERT_DIR"

# Create symlinks so Docker volumes can reference a stable path
ln -sf "$CERT_DIR/fullchain.pem" "$DOCKER_CERT_DIR/fullchain.pem"
ln -sf "$CERT_DIR/privkey.pem"   "$DOCKER_CERT_DIR/privkey.pem"

success "Symlinks created in $DOCKER_CERT_DIR/"

# ---------------------------------------------------------------------------
# Set up auto-renewal
# ---------------------------------------------------------------------------
step "Configuring automatic renewal"

PROJECT_DIR="$(pwd)"
CRON_JOB="0 3 * * * certbot renew --quiet --deploy-hook 'docker compose -f ${PROJECT_DIR}/docker-compose.yml exec -T nginx nginx -s reload' >> /var/log/letsencrypt-renew.log 2>&1"

# Add cron job if it doesn't already exist
if crontab -l 2>/dev/null | grep -qF "certbot renew"; then
    warn "Certbot renewal cron job already exists — skipping."
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    success "Cron job added: daily renewal check at 03:00."
fi

# Also enable the certbot systemd timer if available
if systemctl list-unit-files 2>/dev/null | grep -q certbot.timer; then
    systemctl enable --now certbot.timer 2>/dev/null || true
    success "certbot.timer systemd timer enabled."
fi

# ---------------------------------------------------------------------------
# Restart nginx
# ---------------------------------------------------------------------------
if [ "$MODE" = "standalone" ]; then
    step "Restarting nginx"

    if [ -f docker-compose.yml ]; then
        docker compose start nginx 2>/dev/null && success "nginx container restarted." || true
    fi
    if systemctl is-enabled --quiet nginx 2>/dev/null; then
        systemctl start nginx && success "System nginx restarted." || true
    fi
fi

# ---------------------------------------------------------------------------
# Test certificate
# ---------------------------------------------------------------------------
step "Testing certificate"

CERT_EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_DIR/fullchain.pem" 2>/dev/null | cut -d= -f2)
CERT_ISSUER=$(openssl x509 -issuer -noout -in "$CERT_DIR/fullchain.pem" 2>/dev/null | sed 's/issuer=//')

success "Certificate details:"
info "  Domain:  $DOMAIN"
info "  Issuer:  $CERT_ISSUER"
info "  Expires: $CERT_EXPIRY"

# Try a TLS connection if port 443 is reachable
if curl -sI --max-time 5 "https://$DOMAIN/" &>/dev/null; then
    success "HTTPS connection to https://$DOMAIN/ succeeded."
else
    warn "Could not reach https://$DOMAIN/ — ensure nginx-ssl.conf is active."
fi

# ---------------------------------------------------------------------------
# Auto-configure nginx + .env (when --auto is used)
# ---------------------------------------------------------------------------
if [ "$AUTO_CONFIGURE" = true ]; then
    step "Auto-configuring nginx for SSL"

    # 1. Render the SSL nginx config into a gitignored runtime file. The
    #    tracked nginx.conf is left ALONE so a future `git reset --hard
    #    origin/main` cannot revert nginx to HTTP-only behind the operator's
    #    back. nginx-active.conf is listed in .gitignore.
    if [ ! -f nginx-ssl.conf ]; then
        error "nginx-ssl.conf template is missing — cannot render nginx-active.conf."
        exit 1
    fi
    sed "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx-ssl.conf > nginx-active.conf
    success "nginx-active.conf rendered for $DOMAIN (gitignored runtime file)."

    # 2. Persist the SSL state in .env so docker-compose and deploy.sh keep
    #    selecting the SSL config across rebuilds. .env is gitignored and
    #    therefore survives `git reset --hard origin/main`.
    upsert_env() {
        # upsert_env <KEY> <VALUE> — replaces existing KEY=… line in .env or
        # appends it. Idempotent. No-op if .env is missing (deploy.sh creates
        # it on first run).
        local key="$1"
        local value="$2"
        [ -f .env ] || return 0
        if grep -qE "^${key}=" .env; then
            # Use a sed delimiter unlikely to appear in the value
            sed -i "s|^${key}=.*|${key}=${value}|" .env
        else
            printf '%s=%s\n' "$key" "$value" >> .env
        fi
    }

    if [ ! -f .env ]; then
        warn ".env not found — SSL state cannot be persisted yet."
        warn "Run ./deploy.sh first to generate .env, then re-run ssl-setup.sh."
    else
        upsert_env NGINX_CONF_FILE "./nginx-active.conf"
        upsert_env DOMAIN "$DOMAIN"
        upsert_env CORS_ORIGINS "https://$DOMAIN"
        success ".env updated: NGINX_CONF_FILE, DOMAIN, CORS_ORIGINS pinned for HTTPS."
    fi

    # 3. Backward-compatibility: older clones of docker-compose.yml had the
    #    /etc/letsencrypt mount commented out and relied on a sed patch here.
    #    Current compose mounts them unconditionally via LETSENCRYPT_DIR /
    #    CERTBOT_WEBROOT — nothing to patch on fresh checkouts. We still
    #    handle the legacy form for operators upgrading from older versions.
    if grep -q '# - /etc/letsencrypt:/etc/letsencrypt:ro' docker-compose.yml 2>/dev/null; then
        sed -i 's|# - /etc/letsencrypt:/etc/letsencrypt:ro|- /etc/letsencrypt:/etc/letsencrypt:ro|' docker-compose.yml
        sed -i 's|# - /var/www/certbot:/var/www/certbot:ro|- /var/www/certbot:/var/www/certbot:ro|' docker-compose.yml
        success "docker-compose.yml: legacy commented letsencrypt volumes activated."
    else
        info "docker-compose.yml: letsencrypt volumes already active (mounted unconditionally)."
    fi

    # 4. Defensive guard: if a previous run of an older ssl-setup.sh had
    #    overwritten the tracked nginx.conf with SSL content, warn the
    #    operator. We do NOT auto-revert it — that's a destructive action
    #    and the operator may be mid-merge. nginx-active.conf is what the
    #    container will actually use after this run; nginx.conf is now only
    #    the HTTP-only fallback when NGINX_CONF_FILE is unset.
    if grep -q 'listen 443 ssl' nginx.conf 2>/dev/null; then
        warn "nginx.conf in the working tree contains 'listen 443 ssl' — likely"
        warn "a leftover from an older ssl-setup.sh that overwrote the tracked"
        warn "file. The container will now use nginx-active.conf instead, so"
        warn "this is harmless. To restore the canonical HTTP-only nginx.conf:"
        warn "  git checkout -- nginx.conf"
    fi

    # 5. Restart nginx container to pick up the new config mount.
    step "Restarting nginx with SSL"
    if [ -f docker-compose.yml ]; then
        # Re-create the container so the new NGINX_CONF_FILE env var takes
        # effect (a plain restart would keep the old volume binding).
        docker compose up -d --force-recreate nginx 2>/dev/null && success "nginx restarted with SSL." || warn "Failed to restart nginx. Run: docker compose up -d --force-recreate nginx"
    fi
fi

# ---------------------------------------------------------------------------
# Next steps (when --auto was NOT used)
# ---------------------------------------------------------------------------
if [ "$AUTO_CONFIGURE" = false ]; then
    echo ""
    echo "=========================================="
    echo -e "  ${GREEN}✓ SSL setup complete${NC}"
    echo "=========================================="
    echo ""
    echo "  Next steps (or re-run with --auto to do all of these automatically):"
    echo ""
    echo "  1. Render the SSL nginx config into a gitignored runtime file"
    echo "     (do NOT overwrite the tracked nginx.conf — it would be reverted"
    echo "     on the next 'git reset --hard origin/main'):"
    echo "     sed 's/DOMAIN_PLACEHOLDER/$DOMAIN/g' nginx-ssl.conf > nginx-active.conf"
    echo ""
    echo "  2. Pin the SSL config and domain in .env so docker-compose keeps"
    echo "     using it across rebuilds:"
    echo "     echo 'NGINX_CONF_FILE=./nginx-active.conf' >> .env"
    echo "     echo 'DOMAIN=$DOMAIN' >> .env"
    echo "     sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=https://$DOMAIN|' .env"
    echo ""
    echo "  3. Re-create the nginx container so the new mount takes effect"
    echo "     (the SSL volumes are already mounted unconditionally — no"
    echo "     docker-compose.yml editing required):"
    echo "     docker compose up -d --force-recreate nginx"
    echo ""
else
    echo ""
    echo "=========================================="
    echo -e "  ${GREEN}✓ SSL fully configured${NC}"
    echo "=========================================="
    echo ""
    info "HTTPS is now active at https://$DOMAIN"
    info "Active nginx config: ./nginx-active.conf (gitignored, survives git reset)"
    info "Certificates auto-renew daily at 03:00."
    info "Verify: curl -sI https://$DOMAIN | head -5"
    echo ""
fi
