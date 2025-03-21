#!/bin/bash

LAN_IP=$( hostname -I | awk '{print $1}' )
FAUCET_URL=https://faucet.testnet-archimedes.linera.io
COMPILE=1
GIT_COMMIT=main
CREATE_WALLET=1
CHAIN_OWNER_COUNT=4

options="F:c:C:"

while getopts $options opt; do
  case ${opt} in
    f) FAUCET_URL=${OPTARG} ;;
    c) GIT_COMMIT=${OPTARG} ;;
    C) COMPULE=${OPTARG} ;;
    W) CREATE_WALLET=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../target/output/local"
mkdir -p $OUTPUT_DIR

# Wallet directory
WALLET_DIR="${OUTPUT_DIR}/wallet"
mkdir -p $WALLET_DIR

# Source code directory
SOURCE_DIR="${OUTPUT_DIR}/source"
mkdir -p $SOURCE_DIR

if [ "x$COMPILE" = "x1" ]; then
    # Install official linera for genesis cluster
    cd $SOURCE_DIR
    rm linera-protocol -rf
    git clone https://github.com/linera-io/linera-protocol.git
    cd linera-protocol

    git checkout $GIT_COMMIT

    # Get latest commit to avoid compilation for the same version
    LATEST_COMMIT=`git rev-parse HEAD`
    LATEST_COMMIT=${LATEST_COMMIT:0:10}
    INSTALLED_COMMIT=`linera --version | grep tree | awk -F '/' '{print $7}'`

    if [ "x$LATEST_COMMIT" != "x$INSTALLED_COMMIT" ]; then
        cargo install --path linera-service --features storage-service
        cargo install --path linera-storage-service --features storage-service
    fi
fi

cd $SCRIPT_DIR/..

# Make sure to clean up child processes on exit.
trap 'kill $(jobs -p)' EXIT

BLOB_GATEWAY_WALLET=$WALLET_DIR/blob-gateway
AMS_WALLET=$WALLET_DIR/ams
SWAP_WALLET=$WALLET_DIR/swap
PROXY_WALLET=$$WALLET_DIR/proxy

if [ ! -d ${BLOB_GATEWAY_WALLET}-0 ]; then
    CREATE_WALLET=1
fi

# Create creator chain
if [ "x$CREATE_WALLET" = "x1" ]; then
    # Create wallet for blob gateway
    linera --wallet $WALLET_DIR/blob-gateway/creator/wallet.json --storage rocksdb://$WALLET_DIR/blob-gateway/creator/client.db wallet init --faucet $FAUCET_URL --with-new-chain

    # Create wallet for ams
    linera --wallet $WALLET_DIR/ams/creator/wallet.json --storage rocksdb://$WALLET_DIR/ams/creator/client.db wallet init --faucet $FAUCET_URL --with-new-chain

    # Create wallet for swap
    linera --wallet $WALLET_DIR/swap/creator/wallet.json --storage rocksdb://$WALLET_DIR/swap/creator/client.db wallet init --faucet $FAUCET_URL --with-new-chain

    # Create wallet for proxy
    linera --wallet $WALLET_DIR/proxy/creator/wallet.json --storage rocksdb://$WALLET_DIR/proxy/creator/client.db wallet init --faucet $FAUCET_URL --with-new-chain
fi

# Publish bytecode then create applications
# Create blob gateway
linera --wallet $WALLET_DIR/blob-gateway/creator/wallet.json --storage rocksdb://$WALLET_DIR/blob-gateway/creator/client.db publish-module $SCRIPT_DIR/../target/wasm32-unknown-unknown/release/blob-gateway

# Create mining chain to listen creator chain
if [ "x$CREATE_WALLET" = "x1" ]; then
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        # Create wallet for blob gateway
        linera --wallet $WALLET_DIR/blob-gateway/$i/wallet.json --storage rocksdb://$WALLET_DIR/blob-gateway/$i/client.db wallet init --faucet $FAUCET_URL --with-new-chain

        # Create wallet for ams
        linera --wallet $WALLET_DIR/ams/$i/wallet.json --storage rocksdb://$WALLET_DIR/ams/$i/client.db wallet init --faucet $FAUCET_URL --with-new-chain

        # Create wallet for swap
        linera --wallet $WALLET_DIR/swap/$i/wallet.json --storage rocksdb://$WALLET_DIR/swap/$i/client.db wallet init --faucet $FAUCET_URL --with-new-chain

        # Create wallet for proxy
        linera --wallet $WALLET_DIR/proxy/$i/wallet.json --storage rocksdb://$WALLET_DIR/proxy/$i/client.db wallet init --faucet $FAUCET_URL --with-new-chain
    done
fi

# Create application with multi owners

read
