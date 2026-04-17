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
#   - Copy nginx-ssl.conf → nginx.conf with domain replaced
#   - Uncomment /etc/letsencrypt volume in docker-compose.yml
#   - Update CORS_ORIGINS in .env to https://
#   - Restart the nginx container
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

    # 1. Copy SSL config and replace domain placeholder
    cp nginx-ssl.conf nginx.conf
    sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx.conf
    success "nginx.conf updated with SSL config for $DOMAIN."

    # 2. Uncomment letsencrypt volumes in docker-compose.yml
    if grep -q '# - /etc/letsencrypt:/etc/letsencrypt:ro' docker-compose.yml; then
        sed -i 's|# - /etc/letsencrypt:/etc/letsencrypt:ro|- /etc/letsencrypt:/etc/letsencrypt:ro|' docker-compose.yml
        sed -i 's|# - /var/www/certbot:/var/www/certbot:ro|- /var/www/certbot:/var/www/certbot:ro|' docker-compose.yml
        success "docker-compose.yml: letsencrypt volumes enabled."
    else
        info "docker-compose.yml: letsencrypt volumes already configured."
    fi

    # 3. Update CORS_ORIGINS in .env to use HTTPS
    if [ -f .env ]; then
        if grep -q "^CORS_ORIGINS=http://" .env; then
            sed -i "s|^CORS_ORIGINS=http://.*|CORS_ORIGINS=https://$DOMAIN|" .env
            success ".env: CORS_ORIGINS updated to https://$DOMAIN."
        elif grep -q "^CORS_ORIGINS=https://" .env; then
            info ".env: CORS_ORIGINS already uses HTTPS."
        else
            echo "CORS_ORIGINS=https://$DOMAIN" >> .env
            success ".env: CORS_ORIGINS added as https://$DOMAIN."
        fi
    fi

    # 4. Restart nginx container
    step "Restarting nginx with SSL"
    if [ -f docker-compose.yml ]; then
        docker compose up -d --build nginx 2>/dev/null && success "nginx restarted with SSL." || warn "Failed to restart nginx. Run: docker compose up -d --build nginx"
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
    echo "  Next steps (or re-run with --auto to do these automatically):"
    echo ""
    echo "  1. Copy the SSL nginx config into place:"
    echo "     cp nginx-ssl.conf nginx.conf"
    echo ""
    echo "  2. Replace DOMAIN_PLACEHOLDER with your domain:"
    echo "     sed -i 's/DOMAIN_PLACEHOLDER/$DOMAIN/g' nginx.conf"
    echo ""
    echo "  3. Update docker-compose.yml nginx volumes — uncomment letsencrypt lines:"
    echo "     volumes:"
    echo "       - /etc/letsencrypt:/etc/letsencrypt:ro"
    echo "       - /var/www/certbot:/var/www/certbot:ro"
    echo ""
    echo "  4. Update CORS_ORIGINS in .env to use HTTPS:"
    echo "     CORS_ORIGINS=https://$DOMAIN"
    echo ""
    echo "  5. Restart the stack:"
    echo "     docker compose up -d --build nginx"
    echo ""
else
    echo ""
    echo "=========================================="
    echo -e "  ${GREEN}✓ SSL fully configured${NC}"
    echo "=========================================="
    echo ""
    info "HTTPS is now active at https://$DOMAIN"
    info "Certificates auto-renew daily at 03:00."
    info "Verify: curl -sI https://$DOMAIN | head -5"
    echo ""
fi
