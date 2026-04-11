#!/bin/bash

####
## E.g. ./restart.sh -C 1 -z testnet-conway
####

LAN_IP=$( hostname -I | awk '{print $1}' )
CLUSTER=testnet-conway

options="C:z:"

while getopts $options opt; do
  case ${opt} in
    C) COMPILE=${OPTARG} ;;
    z) CLUSTER=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../output/compose"
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

BIN_DIR="${OUTPUT_DIR}/bin"
mkdir -p $BIN_DIR

DOCKER_DIR="${OUTPUT_DIR}/docker"
mkdir -p $DOCKER_DIR

function get_domain_value() {
    application=$1
    sed ':a;N;s/=\n/=/;ta;P;D'  ../webui-v2/src/constant/domain.ts | grep $application | awk '{ print $NF }'
}

BLOB_GATEWAY_CHAIN_ID=$(get_domain_value BLOB_GATEWAY_CHAIN_ID)
BLOB_GATEWAY_APPLICATION_ID=$(get_domain_value BLOB_GATEWAY_APPLICATION_ID)
AMS_CHAIN_ID=$(get_domain_value AMS_CHAIN_ID)
AMS_APPLICATION_ID=$(get_domain_value AMS_APPLICATION_ID)
SWAP_CHAIN_ID=$(get_domain_value SWAP_CHAIN_ID)
SWAP_APPLICATION_ID=$(get_domain_value SWAP_APPLICATION_ID)
PROXY_CHAIN_ID=$(get_domain_value PROXY_CHAIN_ID)
PROXY_APPLICATION_ID=$(get_domain_value PROXY_APPLICATION_ID)

SUB_DOMAIN=$(echo "api.${CLUSTER}." | sed 's/\.\./\./g')
DATABASE_NAME=linera_swap_kline
DATABASE_USER=linera-swap
DATABASE_PASSWORD=12345679
DATABASE_PORT=3306
SWAP_HOST=${SUB_DOMAIN}lineraswap.fun
PROXY_HOST=${SUB_DOMAIN}linerameme.fun

export PATH=$BIN_DIR:$PATH

function wallet_owner() {
    wallet_name=$1
    wallet_index=$2
    sudo $BIN_DIR/linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | awk '/^Default owner:/ { if ($3 != "No") print $3 }'
}

function wallet_chain_id() {
    wallet_name=$1
    wallet_index=$2
    sudo $BIN_DIR/linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | awk '/^Chain ID:/ {chain=$3} /^Default owner:/ {if ($3 != "No") print chain}'
}

function stop_chains() {
    LINERA_IMAGE=linera-respeer docker compose -f config/docker-compose.yml down
}

function start_chains() {
    LINERA_IMAGE=linera-respeer docker compose -f config/docker-compose.yml up --wait
}

function build_linera_respeer() {
    rm linera-protocol-respeer -rf
    git clone https://github.com/respeer-ai/linera-protocol.git linera-protocol-respeer
    cd linera-protocol-respeer
    git checkout respeer-maas-testnet_conway-c75455ed-2025-09-26
    git pull origin respeer-maas-testnet_conway-c75455ed-2025-09-26
    GIT_COMMIT=$(git rev-parse --short HEAD)
    docker build --build-arg git_commit="$GIT_COMMIT" --build-arg features="scylladb,metrics,disable-native-rpc,enable-wallet-rpc" -f docker/Dockerfile . -t linera-respeer || exit 1
}

function build_kline() {
    docker build -f $ROOT_DIR/docker/Dockerfile . -t kline || exit 1
}

function build_funder() {
    docker build -f $ROOT_DIR/docker/Dockerfile.funder . -t funder || exit 1
}

if [ "x$COMPILE" = "x1" ]; then
    cd $SOURCE_DIR
    build_linera_respeer

    cp -v $ROOT_DIR/docker/docker-compose-wallet.yml $DOCKER_DIR
    cp -v $ROOT_DIR/service/kline $DOCKER_DIR -rf
    cp -v $ROOT_DIR/docker/*-entrypoint.sh $DOCKER_DIR

    cd $OUTPUT_DIR
    build_kline
    build_funder
fi

function restart_kline() {
    LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-wallet.yml down
    MAKER_OWNER=$(wallet_owner maker 0)
    MAKER_CHAIN_ID=$(wallet_chain_id maker 0)
    BLOB_GATEWAY_OWNER=$(wallet_owner blob-gateway 0)
    AMS_OWNER=$(wallet_owner ams 0)
    PROXY_OWNER=$(wallet_owner proxy 0)
    SWAP_OWNER=$(wallet_owner swap 0)

    cp -v $ROOT_DIR/docker/docker-compose-query.yml $DOCKER_DIR
    LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-query.yml down
    LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-query.yml up --wait

    function import_query_chain() {
        owner=$1
        chain_id=$2
        label=$3

        payload=$(jq -cn \
            --arg owner "$owner" \
            --arg chainId "$chain_id" \
            '{query:"mutation ImportChain($owner: AccountOwner!, $chainId: ChainId!) { importChain(owner: $owner, chainId: $chainId) }", variables:{owner:$owner, chainId:$chainId}}')
        verify_payload='{"query":"query Chains { chains { list } }"}'

        for _ in $(seq 1 20); do
            resp=$(curl -sS http://localhost:24080 -H 'Content-Type: application/json' --data "$payload" 2>&1 || true)
            verify=$(curl -sS http://localhost:24080 -H 'Content-Type: application/json' --data "$verify_payload" 2>&1 || true)
            if echo "$verify" | grep -q "$chain_id"; then
                echo "Imported $label chain $chain_id to query-service"
                return 0
            fi
            sleep 2
        done

        echo "Failed import $label chain $chain_id to query-service"
        echo "$resp"
        echo "$verify"
        exit 1
    }

    import_query_chain "$BLOB_GATEWAY_OWNER" "$BLOB_GATEWAY_CHAIN_ID" blob-gateway
    import_query_chain "$AMS_OWNER" "$AMS_CHAIN_ID" ams
    import_query_chain "$PROXY_OWNER" "$PROXY_CHAIN_ID" proxy
    import_query_chain "$SWAP_OWNER" "$SWAP_CHAIN_ID" swap

    start_chains
    LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-wallet.yml up --wait

    LAN_IP=$LAN_IP DATABASE_HOST=$LAN_IP DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-kline.yml down
    LAN_IP=$LAN_IP DATABASE_HOST=$LAN_IP DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-kline.yml up --wait

    LAN_IP=$LAN_IP SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID WALLET_HOST=$LAN_IP:40082 WALLET_OWNER=$MAKER_OWNER WALLET_CHAIN=$MAKER_CHAIN_ID \
      SWAP_HOST=$SWAP_HOST PROXY_HOST=$PROXY_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-maker.yml down
    LAN_IP=$LAN_IP SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID WALLET_HOST=$LAN_IP:40082 WALLET_OWNER=$MAKER_OWNER WALLET_CHAIN=$MAKER_CHAIN_ID \
      SWAP_HOST=$SWAP_HOST PROXY_HOST=$PROXY_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-maker.yml up --wait
}

function restart_funder() {
    LAN_IP=$LAN_IP SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
    PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
    docker compose -f $ROOT_DIR/docker/docker-compose-funder.yml down
    LAN_IP=$LAN_IP SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
    PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
    MAKER_WALLET_CHAIN_ID=$MAKER_CHAIN_ID \
    docker compose -f $ROOT_DIR/docker/docker-compose-funder.yml up --wait
}

cd $OUTPUT_DIR
stop_chains
restart_kline
restart_funder
