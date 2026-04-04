#!/bin/bash

[ ! -z "$MAKER_WALLET_HOST" ] && MAKER_WALLET_HOST="--maker-wallet-host $MAKER_WALLET_HOST"
[ ! -z "$MAKER_WALLET_CHAIN_ID" ] && MAKER_WALLET_CHAIN_ID="--maker-wallet-chain-id $MAKER_WALLET_CHAIN_ID"
[ ! -z "$MAKER_WALLETS" ] && MAKER_WALLETS="--maker-wallets $MAKER_WALLETS"
[ ! -z "$MINER_WALLETS" ] && MINER_WALLETS="--miner-wallets $MINER_WALLETS"

PATH=/:$PATH python3.10 -u src/funder.py --swap-chain-id "$SWAP_CHAIN_ID" --swap-application-id "$SWAP_APPLICATION_ID" --wallet-host "$WALLET_HOST" --wallet-owner "$WALLET_OWNER" --wallet-chain "$WALLET_CHAIN" --swap-host "$SWAP_HOST" --proxy-host "$PROXY_HOST" --proxy-chain-id "$PROXY_CHAIN_ID" --proxy-application-id "$PROXY_APPLICATION_ID" $MAKER_WALLET_HOST $MAKER_WALLET_CHAIN_ID $MAKER_WALLETS $MINER_WALLETS
