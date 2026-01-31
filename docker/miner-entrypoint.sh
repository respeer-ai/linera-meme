#!/bin/bash

MAX_PENDING_MESSAGE_BUNDLES=${MAX_PENDING_MESSAGE_BUNDLES:-10}

/usr/bin/miner \
  --wallet /wallet/wallet.json \
  --keystore /wallet/keystore.json \
  --storage rocksdb:/wallet/client.db \
  --with-application-logs \
  --max-pending-message-bundles $MAX_PENDING_MESSAGE_BUNDLES \
  run \
  --proxy-application-id $PROXY_APPLICATION_ID
