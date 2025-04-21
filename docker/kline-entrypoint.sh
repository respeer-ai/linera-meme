#!/bin/bash

python3 src/kline.py --swap-application-id "$SWAP_APPLICATION_ID" --database-host "$DATABASE_HOST" --database-port "$DATABASE_PORT" --database-user "$DATABASE_USER" --database-password "$DATABASE_PASSWORD" --database-name "$DATABASE_NAME" --swap-host "$SWAP_HOST" &
sleep 10
curl -X POST http://localhost:25080/run/ticker
