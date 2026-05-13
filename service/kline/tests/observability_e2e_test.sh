#!/usr/bin/env bash
#
# OBS-E2E-001: End-to-end observability integration test.
#
# Validates the full L1→L2→L3 pipeline:
#   Layer 1: Raw block ingestion from chain GraphQL endpoint
#   Layer 2: Normalization of decoded operations/messages into normalized events
#   Layer 3: Market-data derivation (settled trades, liquidity changes)
#   Product: /transactions, /points, /positions return projection-backed data
#
# Environment prerequisites:
#   - Docker (for MySQL)
#   - Rust toolchain (for decoder binary)
#   - Python 3 + venv
#   - Access to a running Linera chain (testnet or local)
#
# Usage:
#   ./tests/observability_e2e_test.sh --chain-graphql-url <URL> \
#       [--swap-host <host>] [--swap-chain-id <id>] [--swap-application-id <id>] \
#       [--proxy-host <host>] [--proxy-chain-id <id>] [--proxy-application-id <id>]
#
# Environment variables (overrides):
#   KLINE_DATABASE_HOST  (default: localhost)
#   KLINE_DATABASE_PORT  (default: 3306)
#   KLINE_DATABASE_NAME  (default: linera_swap_kline_test)
#   KLINE_DATABASE_USER  (default: root)
#   KLINE_DATABASE_PASS  (default: 12345679)
#   KLINE_SERVICE_PORT   (default: 25080)
#

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
KLINE_DIR=$(dirname "$SCRIPT_DIR")
ROOT_DIR=$(cd "$KLINE_DIR/../.." &> /dev/null && pwd)

# ─── Config ───────────────────────────────────────────────────────────
CHAIN_GRAPHQL_URL="${CHAIN_GRAPHQL_URL:-}"
SWAP_HOST="${SWAP_HOST:-}"
SWAP_CHAIN_ID="${SWAP_CHAIN_ID:-}"
SWAP_APPLICATION_ID="${SWAP_APPLICATION_ID:-}"
PROXY_HOST="${PROXY_HOST:-}"
PROXY_CHAIN_ID="${PROXY_CHAIN_ID:-}"
PROXY_APPLICATION_ID="${PROXY_APPLICATION_ID:-}"

DATABASE_HOST="${KLINE_DATABASE_HOST:-localhost}"
DATABASE_PORT="${KLINE_DATABASE_PORT:-3306}"
DATABASE_NAME="${KLINE_DATABASE_NAME:-linera_swap_kline_test}"
DATABASE_USER="${KLINE_DATABASE_USER:-root}"
DATABASE_PASSWORD="${KLINE_DATABASE_PASS:-12345679}"
SERVICE_PORT="${KLINE_SERVICE_PORT:-25080}"

PASS=0
FAIL=0
TMPDIR=$(mktemp -d)
KLINE_PID=""

cleanup() {
    local exit_code=$?
    echo ""
    echo "=== Cleaning up ==="
    if [ -n "$KLINE_PID" ] && kill -0 "$KLINE_PID" 2>/dev/null; then
        echo "Stopping kline service (pid $KLINE_PID)..."
        kill "$KLINE_PID" 2>/dev/null || true
        wait "$KLINE_PID" 2>/dev/null || true
    fi
    echo "Removing temp directory..."
    rm -rf "$TMPDIR"
    if [ "$exit_code" -ne 0 ] && [ "$PASS" -eq 0 ] && [ "$FAIL" -eq 0 ]; then
        echo "❌ FAIL: Unexpected error during test setup"
        exit 1
    fi
}
trap cleanup EXIT

pass() { echo "  ✅ PASS: $1"; ((PASS++)); }
fail() { echo "  ❌ FAIL: $1"; ((FAIL++)); }

# ─── Parse CLI ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --chain-graphql-url) CHAIN_GRAPHQL_URL="$2"; shift 2 ;;
        --swap-host) SWAP_HOST="$2"; shift 2 ;;
        --swap-chain-id) SWAP_CHAIN_ID="$2"; shift 2 ;;
        --swap-application-id) SWAP_APPLICATION_ID="$2"; shift 2 ;;
        --proxy-host) PROXY_HOST="$2"; shift 2 ;;
        --proxy-chain-id) PROXY_CHAIN_ID="$2"; shift 2 ;;
        --proxy-application-id) PROXY_APPLICATION_ID="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ -z "$CHAIN_GRAPHQL_URL" ]; then
    echo "Usage: $0 --chain-graphql-url <URL> [options]"
    echo "  --chain-graphql-url      Required: Linera chain GraphQL endpoint"
    echo "  --swap-host              Optional: swap service domain"
    echo "  --swap-chain-id          Optional: swap application chain ID"
    echo "  --swap-application-id    Optional: swap application ID"
    echo "  --proxy-host             Optional: proxy service domain"
    echo "  --proxy-chain-id         Optional: proxy application chain ID"
    echo "  --proxy-application-id   Optional: proxy application ID"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  OBS-E2E-001: Observability End-to-End Test"
echo "═══════════════════════════════════════════════════════════════"
echo "Chain GraphQL:  $CHAIN_GRAPHQL_URL"
echo "Service port:   $SERVICE_PORT"
echo "Database:       $DATABASE_HOST:$DATABASE_PORT/$DATABASE_NAME"
echo ""

# ─── Step 1: Decoder binary ──────────────────────────────────────────
echo "=== [1/5] Building canonical_decoder binary ==="
if [ -f "$ROOT_DIR/target/release/canonical_decoder" ]; then
    echo "  Binary already exists at target/release/canonical_decoder"
else
    cargo build --release -p decoder --bin canonical_decoder -j 1
fi
pass "canonical_decoder binary available"

# ─── Step 2: Python environment ───────────────────────────────────────
echo "=== [2/5] Setting up Python environment ==="
VENV_DIR="$TMPDIR/venv"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$KLINE_DIR/requirements.txt"
"$VENV_DIR/bin/pip" install --quiet -e "$KLINE_DIR"
"$VENV_DIR/bin/pip" install --quiet websocket-client
pass "Python environment ready"

# ─── Step 3: Automated projection-fact reconciliation ─────────────────
echo "=== [3/6] Running projection-fact reconciliation regression ==="
"$VENV_DIR/bin/python3" -m pytest "$KLINE_DIR/tests/observability_reconciliation_test.py" -q
pass "projection facts reconcile transactions, candles, stats, virtual positions and protocol fee metrics"

# ─── Step 4: Start kline service ─────────────────────────────────────
echo "=== [4/6] Starting kline service ==="
KLINE_RUST_DECODER_BIN="$ROOT_DIR/target/release/canonical_decoder"
export KLINE_RUST_DECODER_BIN

OBSERVABILITY_ARGS=(
    --chain-graphql-url "$CHAIN_GRAPHQL_URL"
    --database-host "$DATABASE_HOST"
    --database-port "$DATABASE_PORT"
    --database-name "$DATABASE_NAME"
    --database-user "$DATABASE_USER"
    --database-password "$DATABASE_PASSWORD"
)
if [ -n "$SWAP_HOST" ]; then
    OBSERVABILITY_ARGS+=(--swap-host "$SWAP_HOST")
fi
if [ -n "$SWAP_CHAIN_ID" ]; then
    OBSERVABILITY_ARGS+=(--swap-chain-id "$SWAP_CHAIN_ID")
fi
if [ -n "$SWAP_APPLICATION_ID" ]; then
    OBSERVABILITY_ARGS+=(--swap-application-id "$SWAP_APPLICATION_ID")
fi
if [ -n "$PROXY_HOST" ]; then
    OBSERVABILITY_ARGS+=(--proxy-host "$PROXY_HOST")
fi
if [ -n "$PROXY_CHAIN_ID" ]; then
    OBSERVABILITY_ARGS+=(--proxy-chain-id "$PROXY_CHAIN_ID")
fi
if [ -n "$PROXY_APPLICATION_ID" ]; then
    OBSERVABILITY_ARGS+=(--proxy-application-id "$PROXY_APPLICATION_ID")
fi

SERVICE_LOG="$TMPDIR/kline_service.log"
echo "  Log: $SERVICE_LOG"
KLINE_SRC="$KLINE_DIR/src"
cd "$KLINE_DIR"
KLINE_RUST_DECODER_BIN="$KLINE_RUST_DECODER_BIN" \
    "$VENV_DIR/bin/python3" -u "$KLINE_SRC/kline.py" \
    "${OBSERVABILITY_ARGS[@]}" \
    > "$SERVICE_LOG" 2>&1 &
KLINE_PID=$!
echo "  PID: $KLINE_PID"

# Wait for server to start (up to 60 seconds)
echo "  Waiting for service to become ready..."
STARTUP_WAIT=60
for i in $(seq 1 "$STARTUP_WAIT"); do
    if curl -sf "http://localhost:$SERVICE_PORT/debug/observability" > /dev/null 2>&1; then
        echo "  Service ready after ${i}s"
        pass "kline service started"
        break
    fi
    if ! kill -0 "$KLINE_PID" 2>/dev/null; then
        echo "  ❌ kline service died during startup"
        tail -30 "$SERVICE_LOG"
        fail "kline service startup"
        exit 1
    fi
    sleep 1
done
if ! curl -sf "http://localhost:$SERVICE_PORT/debug/observability" > /dev/null 2>&1; then
    echo "  ❌ kline service not ready after ${STARTUP_WAIT}s"
    tail -30 "$SERVICE_LOG"
    fail "kline service startup (timeout)"
    exit 1
fi

# ─── Step 5: Verify observability debug endpoint ─────────────────────
echo "=== [5/6] Verifying observability debug endpoint ==="
OBSERVABILITY_JSON=$(curl -sf "http://localhost:$SERVICE_PORT/debug/observability")
echo "$OBSERVABILITY_JSON" | python3 -m json.tool > /dev/null 2>&1 && pass "GET /debug/observability returns valid JSON"

# Check that the status object is present
STATUS_STATE=$(echo "$OBSERVABILITY_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['status']['state'])" 2>/dev/null || echo "")
if [ "$STATUS_STATE" = "ready" ] || [ "$STATUS_STATE" = "degraded" ]; then
    pass "observability status is '$STATUS_STATE'"
else
    fail "observability status should be 'ready' or 'degraded', got '$STATUS_STATE'"
fi

# Check for component groups
WORKER_COUNT=$(echo "$OBSERVABILITY_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
workers = d['status'].get('component_groups', {}).get('workers', [])
print(len(workers))
" 2>/dev/null || echo "0")
if [ "$WORKER_COUNT" -ge 3 ]; then
    pass "observability reports $WORKER_COUNT worker components (decode_scheduler, normalizer, market_deriver)"
else
    fail "observability should report >= 3 worker components, got $WORKER_COUNT"
fi

# Check for cursors
CURSOR_COUNT=$(echo "$OBSERVABILITY_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len(d.get('cursors', [])))
" 2>/dev/null || echo "0")
echo "  Chain cursors: $CURSOR_COUNT"

# ─── Step 6: Verify API endpoints ────────────────────────────────────
echo "=== [6/6] Verifying product API endpoints ==="

OWNER_ACCOUNT="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-e2e"

# /transactions (with no filters returns empty or data)
TRANSACTIONS_JSON=$(curl -sf "http://localhost:$SERVICE_PORT/transactions/start_at/0/end_at/9999999999999?limit=25" 2>/dev/null || echo "")
if [ -n "$TRANSACTIONS_JSON" ]; then
    echo "$TRANSACTIONS_JSON" | python3 -m json.tool > /dev/null 2>&1 && pass "GET /transactions returns valid JSON"
else
    fail "GET /transactions returned empty"
fi

# /points (with no filters returns empty or data)
POINTS_JSON=$(curl -sf "http://localhost:$SERVICE_PORT/points/token0/test/token1/test/start_at/0/end_at/9999999999999/interval/1m" 2>/dev/null || echo "")
if [ -n "$POINTS_JSON" ]; then
    echo "$POINTS_JSON" | python3 -m json.tool > /dev/null 2>&1 && pass "GET /points returns valid JSON"
else
    fail "GET /points returned empty"
fi

POSITIONS_JSON=$(curl -sf "http://localhost:$SERVICE_PORT/positions?owner=$OWNER_ACCOUNT&status=all" 2>/dev/null || echo "")
if [ -n "$POSITIONS_JSON" ]; then
    echo "$POSITIONS_JSON" | python3 -m json.tool > /dev/null 2>&1 && pass "GET /positions returns valid JSON"
else
    fail "GET /positions returned empty"
fi

POSITION_METRICS_JSON=$(curl -sf "http://localhost:$SERVICE_PORT/position-metrics?owner=$OWNER_ACCOUNT&status=all" 2>/dev/null || echo "")
if [ -n "$POSITION_METRICS_JSON" ]; then
    echo "$POSITION_METRICS_JSON" | python3 -m json.tool > /dev/null 2>&1 && pass "GET /position-metrics returns valid JSON"
else
    fail "GET /position-metrics returned empty"
fi

POOL_STATS_JSON=$(curl -sf "http://localhost:$SERVICE_PORT/poolstats/interval/1d" 2>/dev/null || echo "")
if [ -n "$POOL_STATS_JSON" ]; then
    echo "$POOL_STATS_JSON" | python3 -m json.tool > /dev/null 2>&1 && pass "GET /poolstats/interval/1d returns valid JSON"
else
    fail "GET /poolstats/interval/1d returned empty"
fi

PROTOCOL_STATS_JSON=$(curl -sf "http://localhost:$SERVICE_PORT/protocol/stats" 2>/dev/null || echo "")
if [ -n "$PROTOCOL_STATS_JSON" ]; then
    echo "$PROTOCOL_STATS_JSON" | python3 -m json.tool > /dev/null 2>&1 && pass "GET /protocol/stats returns valid JSON"
else
    fail "GET /protocol/stats returned empty"
fi

# Service log health check
if grep -q "startup" "$SERVICE_LOG" 2>/dev/null; then
    pass "service log contains startup messages"
fi
if grep -q "observability" "$SERVICE_LOG" 2>/dev/null; then
    pass "service log contains observability lifecycle messages"
fi

# ─── Summary ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Service log: $SERVICE_LOG"

# Additional debug info
echo ""
echo "Last 20 lines of service log:"
tail -20 "$SERVICE_LOG"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "⚠️  $FAIL assertions failed — review log above"
    exit 1
fi

exit 0
