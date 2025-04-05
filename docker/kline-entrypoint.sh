#!/bin/bash

python3 src/kline.py --swap-application-id "$SWAP_APPLICATION_ID" --database-host "$DATABASE_HOST" --database-user "$DATABASE_USER" --database-password "$DATABASE_PASSWORD" --database-name "$DATABASE_NAME" &
sleep 10
curl -X POST http://localhost:25080/run/ticker
