#!/bin/bash

####
## E.g. ./run_local.sh -f http://api.faucet.respeer.ai/api/faucet -C 0 -z testnet-babbage
## This script must be run without proxy
####

LAN_IP=$( hostname -I | awk '{print $1}' )
FAUCET_URL=http://api.faucet.respeer.ai/api/faucet
COMPILE=1
GIT_BRANCH=respeer-maas-testnet_babbage-3dc32c18-2025-04-15
CREATE_WALLET=1
CHAIN_OWNER_COUNT=4
CLUSTER=

options="f:c:C:W:z:"

while getopts $options opt; do
  case ${opt} in
    f) FAUCET_URL=${OPTARG} ;;
    b) GIT_BRANCH=${OPTARG} ;;
    C) COMPILE=${OPTARG} ;;
    W) CREATE_WALLET=${OPTARG} ;;
    z) CLUSTER=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
TEMPLATE_FILE=${SCRIPT_DIR}/../configuration/template/nginx.conf.j2
DOMAIN_FILE="${SCRIPT_DIR}/../webui/src/constant/domain.ts"

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../output/local"
mkdir -p $OUTPUT_DIR

# Generate config
CONFIG_DIR="${OUTPUT_DIR}/config"
mkdir -p $CONFIG_DIR

# Wallet directory
WALLET_DIR="${OUTPUT_DIR}/wallet"
mkdir -p $WALLET_DIR

# Source code directory
SOURCE_DIR="${OUTPUT_DIR}/source"
mkdir -p $SOURCE_DIR

# Run blob query without native RPC
COMMON_BIN_DIR="${OUTPUT_DIR}/bin/common"
mkdir -p $COMMON_BIN_DIR

# Run maker wallet with native RPC
MAKER_BIN_DIR="${OUTPUT_DIR}/bin/maker"
mkdir -p $MAKER_BIN_DIR

export PATH=$COMMON_BIN_DIR:$PATH

if [ "x$COMPILE" = "x1" ]; then
    # Install official linera for genesis cluster
    cd $SOURCE_DIR
    rm linera-protocol -rf
    # We should run with respeer fork for blob query
    git clone https://github.com/respeer-ai/linera-protocol.git
    cd linera-protocol

    git checkout $GIT_BRANCH
    git pull origin $GIT_BRANCH

    # Get latest commit to avoid compilation for the same version
    LATEST_COMMIT=`git rev-parse HEAD`
    LATEST_COMMIT=${LATEST_COMMIT:0:10}
    INSTALLED_COMMIT=`linera --version | grep tree | awk -F '/' '{print $7}'`

    if [ "x$LATEST_COMMIT" != "x$INSTALLED_COMMIT" ]; then
        cargo build --release --features storage-service,disable-native-rpc
        mv target/release/linera $COMMON_BIN_DIR

        cargo build --release --features storage-service,enable-wallet-rpc
        mv target/release/linera $MAKER_BIN_DIR
    fi
fi

cd $SCRIPT_DIR/..

# Compile applications
cargo build --release --target wasm32-unknown-unknown

# Make sure to clean up child processes on exit.
trap 'kill $(jobs -p)' EXIT

BLOB_GATEWAY_WALLET=$WALLET_DIR/blob-gateway
if [ ! -d ${BLOB_GATEWAY_WALLET}/creator ]; then
    CREATE_WALLET=1
fi

function create_wallet() {
    wallet_name=$1
    wallet_index=$2
    new_chain=$3

    rm -rf $WALLET_DIR/$wallet_name/$wallet_index
    mkdir -p $WALLET_DIR/$wallet_name/$wallet_index

    # Init wallet from faucet
    if [ "x$new_chain" = "x1" ]; then
        linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
               wallet init \
               --faucet $FAUCET_URL \
               --with-new-chain
    else
        linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
               wallet init \
               --faucet $FAUCET_URL
    fi

    # Create unassigned owner for later multi-owner chain creation
    linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           keygen
}

function create_wallets() {
    wallet_name=$1

    # Create creator chain which will be used to create multi-owner chain
    create_wallet $wallet_name creator 1

    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        # Creator new wallet which only have owner
        create_wallet $wallet_name $i 0
    done
}

# Create creator chain
if [ "x$CREATE_WALLET" = "x1" ]; then
    # Create wallet for blob gateway
    create_wallets blob-gateway

    # Create wallet for ams
    create_wallets ams

    # Create wallet for swap
    create_wallets swap

    # Create wallet for proxy
    create_wallets proxy
fi

function publish_bytecode_on_chain() {
    application_name=$1
    wasm_name=$(echo $2 | sed 's/-/_/g')
    linera --wallet $WALLET_DIR/$application_name/creator/wallet.json \
           --storage rocksdb://$WALLET_DIR/$application_name/creator/client.db \
           publish-module $SCRIPT_DIR/../target/wasm32-unknown-unknown/release/${wasm_name}_{contract,service}.wasm
}

function publish_bytecode() {
    publish_bytecode_on_chain $1 $1
}

# Publish bytecode then create applications
# Create blob gateway
BLOB_GATEWAY_MODULE_ID=$(publish_bytecode blob-gateway)
AMS_MODULE_ID=$(publish_bytecode ams)
SWAP_MODULE_ID=$(publish_bytecode swap)
POOL_MODULE_ID=$(publish_bytecode_on_chain swap pool)
PROXY_MODULE_ID=$(publish_bytecode proxy)
MEME_MODULE_ID=$(publish_bytecode_on_chain proxy meme)

function wallet_owner() {
    wallet_name=$1
    wallet_index=$2
    linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | grep AccountOwner | awk '{print $4}' | grep '0x'
}

function wallet_chain_owner() {
    wallet_name=$1
    wallet_index=$2
    chain_id=$3

    linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
        --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
        wallet show \
        | grep $chain_id -A 2 | grep AccountOwner | awk '{print $4}' | grep '0x'
}

function wallet_unassigned_owner() {
    wallet_name=$1
    wallet_index=$2
    cat $WALLET_DIR/$wallet_name/$wallet_index/wallet.json | jq -r '.unassigned_key_pairs | keys[]'
}

function wallet_unassigned_owners() {
    wallet_name=$1

    owners=($(wallet_unassigned_owner $wallet_name creator))
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        owners+=($(wallet_unassigned_owner $wallet_name $i))
    done

    echo ${owners[@]}
}

function wallet_chain_owners() {
    wallet_name=$1
    chain_id=$2

    owners=($(wallet_chain_owner $wallet_name creator $chain_id))
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        owners+=($(wallet_chain_owner $wallet_name $i $chain_id))
    done

    echo ${owners[@]}
}

function wallet_chain_id() {
    wallet_name=$1
    wallet_index=$2
    linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | grep "Public Key" | grep -v " - " | awk '{print $2}'
}

function assign_chain_to_owner() {
    wallet_name=$1
    wallet_index=$2
    message_id=$3

    owner=$(wallet_unassigned_owner $wallet_name $wallet_index)
    linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           assign --owner $owner --message-id $message_id
}

function open_multi_owner_chain() {
    wallet_name=$1

    owners=$(wallet_unassigned_owners $wallet_name)
    chain_id=$(wallet_chain_id $wallet_name creator)

    chain_message=($(linera --wallet $WALLET_DIR/$wallet_name/creator/wallet.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/creator/client.db \
           open-multi-owner-chain \
           --from $chain_id \
           --owners ${owners[@]} \
           --multi-leader-rounds 100 \
           --initial-balance "5."))

    message_id=${chain_message[0]}
    chain_id=${chain_message[1]}

    # Assign newly created chain to unassigned key.
    assign_chain_to_owner $wallet_name creator $message_id > /dev/null 2>&1
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        assign_chain_to_owner $wallet_name $i $message_id > /dev/null 2>&1
    done

    linera --wallet $WALLET_DIR/$wallet_name/creator/wallet.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/creator/client.db \
	   wallet set-default \
	   $chain_id > /dev/null 2>&1

    echo $chain_id
}

# Create multi owner chains
# Create blob gateway multi owner chains
BLOB_GATEWAY_CHAIN_ID=$(open_multi_owner_chain blob-gateway)
# Create ams multi owner chains
AMS_CHAIN_ID=$(open_multi_owner_chain ams)
# Create proxy multi owner chains
PROXY_CHAIN_ID=$(open_multi_owner_chain proxy)
# Create swap multi owner chains
SWAP_CHAIN_ID=$(open_multi_owner_chain swap)

function process_inbox() {
    wallet_name=$1
    wallet_index=$2

    linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           process-inbox
}

function process_inboxes() {
    wallet_name=$1

    process_inbox $wallet_name creator
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        process_inbox $wallet_name $i
    done
}

# Exhaust chain messages
process_inboxes blob-gateway
process_inboxes ams
process_inboxes proxy
process_inboxes swap

function create_application() {
    wallet_name=$1
    module_id=$2
    argument=$3
    parameters=$4
    chain_id=$5

    if [ "x$argument" != "x" -a "x$parameters" != "x" ]; then
        linera --wallet $WALLET_DIR/$wallet_name/1/wallet.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/1/client.db \
               create-application $module_id $chain_id \
               --json-argument "$argument" \
               --json-parameters "$parameters"
    elif [ "x$argument" != "x" ]; then
        linera --wallet $WALLET_DIR/$wallet_name/1/wallet.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/1/client.db \
               create-application $module_id $chain_id \
               --json-argument "$argument"
    elif [ "x$parameters" != "x" ]; then
        linera --wallet $WALLET_DIR/$wallet_name/1/wallet.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/1/client.db \
               create-application $module_id $chain_id \
               --json-parameters "$parameters"
    else
        linera --wallet $WALLET_DIR/$wallet_name/1/wallet.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/1/client.db \
               create-application $module_id $chain_id
    fi
}

# Create applications
BLOB_GATEWAY_APPLICATION_ID=$(create_application blob-gateway $BLOB_GATEWAY_MODULE_ID '' '' $BLOB_GATEWAY_CHAIN_ID)
AMS_APPLICATION_ID=$(create_application ams $AMS_MODULE_ID '{}' '' $AMS_CHAIN_ID)
SWAP_APPLICATION_ID=$(create_application swap $SWAP_MODULE_ID "{\"pool_bytecode_id\": \"$POOL_MODULE_ID\"}" '{}' $SWAP_CHAIN_ID)
PROXY_APPLICATION_ID=$(create_application proxy $PROXY_MODULE_ID "{\"meme_bytecode_id\": \"$MEME_MODULE_ID\", \"operators\": [], \"swap_application_id\": \"$SWAP_APPLICATION_ID\"}" '' $PROXY_CHAIN_ID)

# Exhaust chain messages
process_inboxes blob-gateway
process_inboxes ams
process_inboxes proxy
process_inboxes swap

function change_multi_owner_chain_single_leader() {
    wallet_name=$1
    chain_id=$2

    owners=$(wallet_chain_owners $wallet_name $chain_id)
    linera --wallet $WALLET_DIR/$wallet_name/1/wallet.json \
	--storage rocksdb://$WALLET_DIR/$wallet_name/1/client.db \
	change-ownership \
	--chain-id $chain_id \
	--owners ${owners[@]} \
	--multi-leader-rounds 0
}

change_multi_owner_chain_single_leader blob-gateway $BLOB_GATEWAY_CHAIN_ID
change_multi_owner_chain_single_leader ams $AMS_CHAIN_ID
change_multi_owner_chain_single_leader proxy $PROXY_CHAIN_ID
change_multi_owner_chain_single_leader swap $SWAP_CHAIN_ID

function service_servers() {
    port_base=$1
    count=$2

    servers="\"localhost:$port_base\""
    if [ "x$count" == "x1" ]; then
        echo $servers
        return
    fi
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        servers="$servers, \"localhost:$((port_base + (i + 1) * 2))\""
    done
    echo $servers
}

function generate_nginx_conf() {
    port_base=$1
    endpoint=$2
    domain=$3
    count=$4

    servers=$(service_servers $port_base $count)
    echo "{
        \"service\": {
            \"endpoint\": \"$endpoint\",
            \"servers\": [$servers],
            \"domain\": \"$domain\",
            \"sub_domain\": \"$SUB_DOMAIN\",
            \"api_endpoint\": \"$endpoint\"
        }
    }" > ${CONFIG_DIR}/$endpoint.nginx.json

    jinja -d ${CONFIG_DIR}/$endpoint.nginx.json $TEMPLATE_FILE > ${CONFIG_DIR}/$endpoint.nginx.conf
    echo cp ${CONFIG_DIR}/$endpoint.nginx.conf /etc/nginx/sites-enabled/
}

SUB_DOMAIN=$(echo "api.${CLUSTER}." | sed 's/\.\./\./g')

# Generate service nginx conf
generate_nginx_conf 20080 blobs blobgateway.com $CHAIN_OWNER_COUNT
generate_nginx_conf 21080 ams ams.respeer.ai $CHAIN_OWNER_COUNT
generate_nginx_conf 22080 swap lineraswap.fun $CHAIN_OWNER_COUNT
generate_nginx_conf 23080 proxy linerameme.fun $CHAIN_OWNER_COUNT
generate_nginx_conf 25080 kline kline.lineraswap.fun 1

echo -e "\n\nService domain"
echo -e "   $LAN_IP ${SUB_DOMAIN}blobgateway.com"
echo -e "   $LAN_IP ${SUB_DOMAIN}ams.respeer.ai"
echo -e "   $LAN_IP ${SUB_DOMAIN}linerameme.fun"
echo -e "   $LAN_IP ${SUB_DOMAIN}lineraswap.fun"
echo -e "   $LAN_IP ${SUB_DOMAIN}kline.lineraswap.fun"
echo -e "   $LAN_IP graphiql.blobgateway.com"
echo -e "   $LAN_IP graphiql.ams.respeer.ai"
echo -e "   $LAN_IP graphiql.linerameme.fun"
echo -e "   $LAN_IP graphiql.lineraswap.fun"
echo -e "   http://graphiql.blobgateway.com"
echo -e "   http://graphiql.ams.respeer.ai"
echo -e "   http://graphiql.linerameme.fun"
echo -e "   http://graphiql.lineraswap.fun"
echo -e "   http://${SUB_DOMAIN}blobgateway.com/api/blobs/chains/$BLOB_GATEWAY_CHAIN_ID/applications/$BLOB_GATEWAY_APPLICATION_ID"
echo -e "   http://${SUB_DOMAIN}ams.respeer.ai/api/ams/chains/$AMS_CHAIN_ID/applications/$AMS_APPLICATION_ID"
echo -e "   http://${SUB_DOMAIN}linerameme.fun/api/proxy/chains/$PROXY_CHAIN_ID/applications/$PROXY_APPLICATION_ID"
echo -e "   http://${SUB_DOMAIN}lineraswap.fun/api/swap/chains/$SWAP_CHAIN_ID/applications/$SWAP_APPLICATION_ID\n\n"

cat <<EOF > $DOMAIN_FILE
export const SUB_DOMAIN = '$CLUSTER.'
export const BLOB_GATEWAY_CHAIN_ID = '$BLOB_GATEWAY_CHAIN_ID'
export const BLOB_GATEWAY_APPLICATION_ID = '$BLOB_GATEWAY_APPLICATION_ID'
export const AMS_CHAIN_ID = '$AMS_CHAIN_ID'
export const AMS_APPLICATION_ID = '$AMS_APPLICATION_ID'
export const PROXY_CHAIN_ID = '$PROXY_CHAIN_ID'
export const PROXY_APPLICATION_ID = '$PROXY_APPLICATION_ID'
export const SWAP_CHAIN_ID = '$SWAP_CHAIN_ID'
export const SWAP_APPLICATION_ID = '$SWAP_APPLICATION_ID'
EOF

function run_service() {
    wallet_name=$1
    wallet_index=$2
    port=$3

    linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           service --port $port &
}

function run_services() {
    wallet_name=$1
    port_base=$2

    run_service $wallet_name creator $port_base
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        port=$((port_base + (i + 1) * 2))
        run_service $wallet_name $i $port
    done
}

# Run services
run_services blob-gateway 20080
run_services ams 21080
run_services swap 22080
run_services proxy 23080

function run_kline() {
    cd service/kline
    pip3 install --upgrade pip
    pip3 install -r requirements.txt
    pip3 install -e .

    pip3 uninstall websocket -y
    pip3 uninstall websocket-client -y
    pip3 install websocket-client

    all_proxy= python3 src/kline.py --swap-application-id $SWAP_APPLICATION_ID --clean-kline &
    sleep 10
    all_proxy= curl -X POST http://localhost:25080/run/ticker > /dev/null 2>&1 &
}

function run_maker() {
    mkdir -p $WALLET_DIR/maker/0

    create_wallet maker 0 1
    owner=$(wallet_owner maker 0)
    chain=$(wallet_chain_id maker 0)

    run_service maker 0 50080

    all_proxy= python3 src/maker.py --swap-application-id $SWAP_APPLICATION_ID --wallet-host "localhost:50080" --wallet-owner "$owner" --wallet-chain "$chain" &
}

run_kline

export PATH=$MAKER_BIN_DIR:$PATH
run_maker

read

kill -9 `ps -ef | grep $SWAP_APPLICATION_ID | awk '{print $2}'` > /dev/null 2>&1
