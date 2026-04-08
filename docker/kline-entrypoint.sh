#!/bin/bash

exec python3 -u src/kline.py --swap-chain-id "$SWAP_CHAIN_ID" --swap-application-id "$SWAP_APPLICATION_ID" --database-host "$DATABASE_HOST" --database-port "$DATABASE_PORT" --database-user "$DATABASE_USER" --database-password "$DATABASE_PASSWORD" --database-name "$DATABASE_NAME" --swap-host "$SWAP_HOST"
