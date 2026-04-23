#!/bin/bash
# =============================================================================
# Dummar Project — Post-Deploy Smoke Check
# =============================================================================
# Quick operator-confidence probe. Verifies that the live deployment serves:
#   - the SPA homepage
#   - the API health/ready endpoint
#   - the API root
#   - (when --domain given) the public HTTPS URL and its API health/ready
#   - the public complaint-track API (no credentials needed)
#
# This is NOT a test framework — it's a 5-second sanity check the operator
# can run after `./deploy.sh` to confirm the live site is actually serving.
#
# Usage:
#   ./smoke-check.sh                          # local probe (http://localhost)
#   ./smoke-check.sh --domain=example.com     # also probes https://example.com
#   ./smoke-check.sh --base-url=https://x.y   # custom explicit base URL
#
# Exit code: number of failed checks (0 = all good).
# =============================================================================

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[FAIL]${NC} $*"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
DOMAIN=""
BASE_URL=""

for arg in "$@"; do
    case "$arg" in
        --domain=*)   DOMAIN="${arg#--domain=}" ;;
        --base-url=*) BASE_URL="${arg#--base-url=}" ;;
        --help|-h)
            head -22 "$0" | tail -19
            exit 0
            ;;
        *)
            error "Unknown argument: $arg"
            exit 2
            ;;
    esac
done

# Default base URL
if [ -z "$BASE_URL" ]; then
    BASE_URL="http://localhost"
fi

PASS=0
FAIL=0

check() {
    local label="$1"
    local url="$2"
    local expected="${3:-200}"
    # Allow a comma-separated list of acceptable statuses (e.g. "200,301").
    local status
    status=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || echo "000")
    if [[ ",$expected," == *",${status},"* ]]; then
        success "$label → HTTP $status   ($url)"
        PASS=$((PASS + 1))
    else
        error   "$label → HTTP $status (expected one of: $expected)  ($url)"
        FAIL=$((FAIL + 1))
    fi
}

echo "════════════════════════════════════════════════════════════"
info  "Dummar smoke-check"
info  "Local base URL: $BASE_URL"
[ -n "$DOMAIN" ] && info "Public domain:  https://$DOMAIN"
echo "════════════════════════════════════════════════════════════"

# ---------------------------------------------------------------------------
# Local checks (always run — exercises the in-container nginx + backend)
# ---------------------------------------------------------------------------
check "Frontend SPA"            "$BASE_URL/"
check "Public landing renders"  "$BASE_URL/"                            "200"
check "API health/ready"        "$BASE_URL/api/health/ready"
check "API root"                "$BASE_URL/api/"
check "Login API reachable"     "$BASE_URL/api/auth/login"              "405,422"
# 405 (Method Not Allowed) or 422 (validation) confirms the route exists
# and is reachable end-to-end through nginx → backend, without us actually
# sending credentials. A 502/504 here would mean nginx can't reach backend.

check "Public submit page"      "$BASE_URL/complaints/new"              "200"
check "Public track page"       "$BASE_URL/complaints/track"            "200"

# ---------------------------------------------------------------------------
# Public HTTPS checks (only when a domain is given)
# ---------------------------------------------------------------------------
if [ -n "$DOMAIN" ]; then
    echo ""
    info "Probing public HTTPS endpoints (TLS verified):"
    check "HTTPS root"             "https://$DOMAIN/"
    check "HTTPS health/ready"     "https://$DOMAIN/api/health/ready"
    check "HTTPS login API"        "https://$DOMAIN/api/auth/login"      "405,422"
    check "HTTPS public submit"    "https://$DOMAIN/complaints/new"      "200"

    # Verify the HTTP→HTTPS redirect is in place (catches accidental HTTP-only
    # nginx.conf regressions after `git pull`).
    info "Verifying HTTP → HTTPS redirect for $DOMAIN…"
    check "HTTP redirects to HTTPS" "http://$DOMAIN/"                    "301,302"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "════════════════════════════════════════════════════════════"
if [ $FAIL -eq 0 ]; then
    success "All $PASS checks passed."
else
    warn  "$PASS passed, $FAIL failed (out of $((PASS + FAIL)))."
fi
echo "════════════════════════════════════════════════════════════"

exit $FAIL
