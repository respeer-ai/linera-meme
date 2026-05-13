#!/bin/bash

args=(
  --swap-chain-id "$SWAP_CHAIN_ID"
  --swap-application-id "$SWAP_APPLICATION_ID"
  --database-host "$DATABASE_HOST"
  --database-port "$DATABASE_PORT"
  --database-user "$DATABASE_USER"
  --database-password "$DATABASE_PASSWORD"
  --database-name "$DATABASE_NAME"
  --swap-host "$SWAP_HOST"
)

if [ -n "${PROXY_HOST:-}" ]; then
  args+=(--proxy-host "$PROXY_HOST")
fi
if [ -n "${PROXY_CHAIN_ID:-}" ]; then
  args+=(--proxy-chain-id "$PROXY_CHAIN_ID")
fi
if [ -n "${PROXY_APPLICATION_ID:-}" ]; then
  args+=(--proxy-application-id "$PROXY_APPLICATION_ID")
fi
if [ -n "${CHAIN_GRAPHQL_URL:-}" ]; then
  args+=(--chain-graphql-url "$CHAIN_GRAPHQL_URL")
fi
if [ -n "${CHAIN_GRAPHQL_WS_URL:-}" ]; then
  args+=(--chain-graphql-ws-url "$CHAIN_GRAPHQL_WS_URL")
fi
if [ -n "${CATCH_UP_CHAIN_IDS:-}" ]; then
  args+=(--catch-up-chain-ids "$CATCH_UP_CHAIN_IDS")
fi
if [ -n "${CATCH_UP_MAX_BLOCKS_PER_CHAIN:-}" ]; then
  args+=(--catch-up-max-blocks-per-chain "$CATCH_UP_MAX_BLOCKS_PER_CHAIN")
fi
if [ "${DISABLE_CATCH_UP_ON_STARTUP:-false}" = "true" ]; then
  args+=(--disable-catch-up-on-startup)
fi

exec python3 -u src/kline.py "${args[@]}"
