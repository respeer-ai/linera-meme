#!/bin/bash

python3 -u src/maker.py --swap-chain-id "$SWAP_CHAIN_ID" --swap-application-id "$SWAP_APPLICATION_ID" --wallet-host "$WALLET_HOST" --wallet-owner "$WALLET_OWNER" --wallet-chain "$WALLET_CHAIN" --swap-host "$SWAP_HOST" --proxy-host "$PROXY_HOST" --proxy-chain-id "$PROXY_CHAIN_ID" --proxy-application-id "$PROXY_APPLICATION_ID"
