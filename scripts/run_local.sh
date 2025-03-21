#!/bin/bash

####
## E.g. ./run_local.sh -f http://172.16.31.73:8080 -C 0
####

LAN_IP=$( hostname -I | awk '{print $1}' )
FAUCET_URL=https://faucet.testnet-archimedes.linera.io
COMPILE=1
GIT_COMMIT=main
CREATE_WALLET=1
CHAIN_OWNER_COUNT=4

options="f:c:C:W:"

while getopts $options opt; do
  case ${opt} in
    f) FAUCET_URL=${OPTARG} ;;
    c) GIT_COMMIT=${OPTARG} ;;
    C) COMPILE=${OPTARG} ;;
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

# Compile applications
cargo build --release --target wasm32-unknown-unknown

# Make sure to clean up child processes on exit.
trap 'kill $(jobs -p)' EXIT

BLOB_GATEWAY_WALLET=$WALLET_DIR/blob-gateway
AMS_WALLET=$WALLET_DIR/ams
SWAP_WALLET=$WALLET_DIR/swap
PROXY_WALLET=$$WALLET_DIR/proxy

if [ ! -d ${BLOB_GATEWAY_WALLET}-0 ]; then
    CREATE_WALLET=1
fi

function create_wallet() {
    wallet_name=$1
    wallet_index=$2
    rm -rf $WALLET_DIR/$wallet_name/$wallet_index
    mkdir -p $WALLET_DIR/$wallet_name/$wallet_index
    linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db wallet init --faucet $FAUCET_URL --with-new-chain
}

# Create creator chain
if [ "x$CREATE_WALLET" = "x1" ]; then
    # Create wallet for blob gateway
    create_wallet blob-gateway creator

    # Create wallet for ams
    create_wallet ams creator

    # Create wallet for swap
    create_wallet swap creator

    # Create wallet for proxy
    create_wallet proxy creator
fi

function publish_bytecode() {
    application_name=$1
    wasm_name=$(echo $application_name | sed 's/-/_/g')
    linera --wallet $WALLET_DIR/$application_name/creator/wallet.json --storage rocksdb://$WALLET_DIR/$application_name/creator/client.db publish-module $SCRIPT_DIR/../target/wasm32-unknown-unknown/release/${wasm_name}_{contract,service}.wasm
}

# Publish bytecode then create applications
# Create blob gateway
BLOB_GATEWAY_MODULE_ID=$(publish_bytecode blob-gateway)
echo $BLOB_GATEWAY_MODULE_ID

exit 0

# Create mining chain to listen creator chain
if [ "x$CREATE_WALLET" = "x1" ]; then
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        # Create wallet for blob gateway
        create_wallet blob-gateway $i

        # Create wallet for ams
        create_wallet ams $i

        # Create wallet for swap
        create_wallet swap $i

        # Create wallet for proxy
        create_wallet proxy $i
    done
fi

# Create application with multi owners

read
