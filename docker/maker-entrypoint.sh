#!/bin/bash

python3 -u src/maker.py \
  --swap-chain-id "$SWAP_CHAIN_ID" \
  --swap-application-id "$SWAP_APPLICATION_ID" \
  --wallet-host "$WALLET_HOST" \
  --wallet-owner "$WALLET_OWNER" \
  --wallet-chain "$WALLET_CHAIN" \
  --swap-host "$SWAP_HOST" \
  --proxy-host "$PROXY_HOST" \
  --proxy-chain-id "$PROXY_CHAIN_ID" \
  --proxy-application-id "$PROXY_APPLICATION_ID" \
  --database-host "$DATABASE_HOST" \
  --database-port "$DATABASE_PORT" \
  --database-user "$DATABASE_USER" \
  --database-password "$DATABASE_PASSWORD" \
  --database-name "$DATABASE_NAME" &

exec python3 -u src/maker_api.py \
  --database-host "$DATABASE_HOST" \
  --database-port "$DATABASE_PORT" \
  --database-user "$DATABASE_USER" \
  --database-password "$DATABASE_PASSWORD" \
  --database-name "$DATABASE_NAME" \
  --maker-replicas "${MAKER_REPLICAS:-1}" \
  --shared-app-data-dir "${SHARED_APP_DATA_DIR:-/shared-app-data}" \
  --wallet-host-template "${MAKER_WALLET_HOST_TEMPLATE:-maker-wallet-service-{index}.maker-wallet-service}" \
  --wallet-rpc-port "${MAKER_WALLET_RPC_PORT:-8080}" \
  --wallet-metrics-port "${MAKER_WALLET_METRICS_PORT:-8082}" \
  --wallet-memory-limit-bytes "${WALLET_MEMORY_LIMIT_BYTES:-0}"
