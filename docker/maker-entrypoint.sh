#!/bin/bash

set -euo pipefail

python3 -u src/maker.py \
  --swap-chain-id "$SWAP_CHAIN_ID" \
  --swap-application-id "$SWAP_APPLICATION_ID" \
  --wallet-host "$WALLET_HOST" \
  --swap-host "$SWAP_HOST" \
  --proxy-host "$PROXY_HOST" \
  --proxy-chain-id "$PROXY_CHAIN_ID" \
  --proxy-application-id "$PROXY_APPLICATION_ID" \
  --database-host "$DATABASE_HOST" \
  --database-port "$DATABASE_PORT" \
  --database-user "$DATABASE_USER" \
  --database-password "$DATABASE_PASSWORD" \
  --database-name "$DATABASE_NAME" &
MAKER_PID=$!

python3 -u src/maker_api.py \
  --database-host "$DATABASE_HOST" \
  --database-port "$DATABASE_PORT" \
  --database-user "$DATABASE_USER" \
  --database-password "$DATABASE_PASSWORD" \
  --database-name "$DATABASE_NAME" \
  --wallet-url "http://${WALLET_HOST}" \
  --wallet-metrics-url "${WALLET_METRICS_URL}" \
  --wallet-memory-limit-bytes "${WALLET_MEMORY_LIMIT_BYTES:-0}" &
API_PID=$!

wait -n "$MAKER_PID" "$API_PID"
EXIT_CODE=$?
kill "$MAKER_PID" "$API_PID" 2>/dev/null || true
wait "$MAKER_PID" "$API_PID" 2>/dev/null || true
exit "$EXIT_CODE"
