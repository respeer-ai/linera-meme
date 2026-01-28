#!/bin/bash

/usr/bin/miner \
  --wallet /wallet/wallet.json \
  --keystore /wallet/keystore.json \
  --storage rocksdb:/wallet/client.db \
  --with-application-logs \
  run \
  --proxy-application-id $PROXY_APPLICATION_ID
