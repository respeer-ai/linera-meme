#!/bin/bash

python3 src/kline.py --swap-application-id "$SWAP_APPLICATION_ID" &
sleep 10
curl -X POST http://localhost:25080/run/ticker
