#!/bin/bash

####
## E.g. ./compose_maker_and_funder.sh
####

function resolve_lan_ip() {
    local route_ip
    route_ip=$(ip route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "src") {print $(i + 1); exit}}')
    if [ -n "$route_ip" ] && [[ ! "$route_ip" =~ ^127\. ]] && [[ ! "$route_ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]]; then
        echo "$route_ip"
        return
    fi
    hostname -I | tr ' ' '\n' | awk '/^[0-9]+\./ && !/^127\./ && !/^172\.(1[6-9]|2[0-9]|3[0-1])\./ {print; exit}'
}

LAN_IP=$(resolve_lan_ip)
if [ -z "$LAN_IP" ]; then
    echo "Failed to resolve LAN_IP" >&2
    exit 1
fi
CLUSTER=testnet-conway

options="z:"

while getopts $options opt; do
  case ${opt} in
    z) CLUSTER=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..
DOMAIN_FILE="${ROOT_DIR}/webui-v2/src/constant/domain.ts"
SUDO_PASSWORD=${SUDO_PASSWORD:-}

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../output/compose"
mkdir -p $OUTPUT_DIR

# Wallet directory
WALLET_DIR="${OUTPUT_DIR}/wallet"
mkdir -p $WALLET_DIR

BIN_DIR="${OUTPUT_DIR}/bin"
mkdir -p $BIN_DIR

DOCKER_DIR="${OUTPUT_DIR}/docker"
mkdir -p $DOCKER_DIR

export PATH=$BIN_DIR:$PATH

# Applications are deployed outside of container, container only run service with wallets

cd $SCRIPT_DIR/..

function sudo_run() {
    if [ -n "$SUDO_PASSWORD" ]; then
        printf '%s\n' "$SUDO_PASSWORD" | sudo -S "$@"
    else
        sudo "$@"
    fi
}

SUB_DOMAIN=$(echo "api.${CLUSTER}." | sed 's/\.\./\./g')

function wallet_owner() {
    wallet_name=$1
    wallet_index=$2
    sudo_run $BIN_DIR/linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
             --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
             --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
             wallet show \
           | awk '/^Default owner:/ { if ($3 != "No") print $3 }'
}

function wallet_chain_id() {
    wallet_name=$1
    wallet_index=$2
    sudo_run $BIN_DIR/linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
             --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
             --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
             wallet show \
           | awk '/^Chain ID:/ {chain=$3} /^Default owner:/ {if ($3 != "No") print chain}'
}

function require_non_empty() {
    local name=$1
    local value=$2
    if [ -z "$value" ]; then
        echo "Missing required value: $name" >&2
        exit 1
    fi
}

cd $OUTPUT_DIR

docker stop kline maker funder
docker rm kline maker funder
docker rmi kline funder npool/kline npool/funder

DATABASE_NAME=linera_swap_kline
DATABASE_USER=linera-swap
DATABASE_PASSWORD=12345679
DATABASE_PORT=3306
SWAP_HOST=${SUB_DOMAIN}lineraswap.fun
PROXY_HOST=${SUB_DOMAIN}linerameme.fun
LOCAL_NO_PROXY=localhost,127.0.0.1,::1,query-service,rpc,maker-wallet,maker,funder,kline,docker-mysql-1,api.lineraswap.fun,api.linerameme.fun,api.testnet-conway.lineraswap.fun,api.testnet-conway.linerameme.fun
NO_PROXY_VALUE=${no_proxy:-${NO_PROXY:-}}
if [ -n "$NO_PROXY_VALUE" ]; then
    NO_PROXY_VALUE="$NO_PROXY_VALUE,$LOCAL_NO_PROXY"
else
    NO_PROXY_VALUE="$LOCAL_NO_PROXY"
fi

SWAP_CHAIN_ID=$( cat $DOMAIN_FILE | grep 'SWAP_CHAIN_ID' | awk -F ' = ' '{print $2}' | sed "s/'//g" )
SWAP_APPLICATION_ID=$( cat $DOMAIN_FILE | grep 'SWAP_APPLICATION_ID' | awk -F ' = ' '{print $2}' | sed "s/'//g" )
PROXY_CHAIN_ID=$( cat $DOMAIN_FILE | grep 'PROXY_CHAIN_ID' | awk -F ' = ' '{print $2}' | sed "s/'//g" )
PROXY_APPLICATION_ID=$( cat $DOMAIN_FILE | grep 'PROXY_APPLICATION_ID' | awk -F ' = ' '{print $2}' | sed "s/'//g" )

# Build kline and maker
function run_kline() {
    docker stop kline maker
    docker rm kline maker

    cp -v $ROOT_DIR/docker/docker-compose-wallet.yml $DOCKER_DIR
    cp -v $ROOT_DIR/docker/*-entrypoint.sh $DOCKER_DIR
    docker build --build-arg all_proxy="${all_proxy:-${ALL_PROXY:-}}" -f $ROOT_DIR/docker/Dockerfile $ROOT_DIR -t kline || exit 1

    NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
      LAN_IP=$LAN_IP LINERA_IMAGE=linera-respeer \
      docker compose -f docker/docker-compose-wallet.yml up --wait

    NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
      LAN_IP=$LAN_IP DATABASE_HOST=$LAN_IP DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      PROXY_HOST=$PROXY_HOST PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID \
      CHAIN_GRAPHQL_URL=http://query-service:30080 \
      CATCH_UP_CHAIN_IDS=$SWAP_CHAIN_ID,$PROXY_CHAIN_ID \
      CATCH_UP_MAX_BLOCKS_PER_CHAIN=100 \
      SUB_DOMAIN=$CLUSTER. \
      docker compose -f $ROOT_DIR/docker/docker-compose-kline.yml up --wait
    local maker_owner
    local maker_chain_id
    maker_owner=$(wallet_owner maker 0)
    maker_chain_id=$(wallet_chain_id maker 0)
    require_non_empty WALLET_OWNER "$maker_owner"
    require_non_empty WALLET_CHAIN "$maker_chain_id"
    NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
      LAN_IP=$LAN_IP SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID WALLET_HOST=$LAN_IP:40082 WALLET_METRICS_URL=http://$LAN_IP:40084/metrics WALLET_OWNER=$maker_owner WALLET_CHAIN=$maker_chain_id \
      SWAP_HOST=$SWAP_HOST PROXY_HOST=$PROXY_HOST DATABASE_HOST=$LAN_IP DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SUB_DOMAIN=$CLUSTER. \
      docker compose -f $ROOT_DIR/docker/docker-compose-maker.yml up --wait
}

function run_funder() {
    docker stop funder
    docker rm funder

    image_exists=`docker images | grep "^funder " | wc -l`
    if [ "x$image_exists" != "x1" ]; then
        cp -v $ROOT_DIR/docker/*-entrypoint.sh $DOCKER_DIR
        docker build --build-arg all_proxy="${all_proxy:-${ALL_PROXY:-}}" -f $ROOT_DIR/docker/Dockerfile.funder $ROOT_DIR -t funder || exit 1
    fi

    local maker_owner
    local maker_chain_id
    maker_owner=$(wallet_owner maker 0)
    maker_chain_id=$(wallet_chain_id maker 0)
    require_non_empty WALLET_OWNER "$maker_owner"
    require_non_empty WALLET_CHAIN "$maker_chain_id"

    NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
      LAN_IP=$LAN_IP SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
      WALLET_HOST=$LAN_IP:40082 WALLET_OWNER=$maker_owner WALLET_CHAIN=$maker_chain_id \
      MAKER_WALLET_HOST=$LAN_IP:40082 MAKER_WALLET_CHAIN_ID=$maker_chain_id \
      SUB_DOMAIN=$CLUSTER. \
      docker compose -f $ROOT_DIR/docker/docker-compose-funder.yml up --wait
}

cd $OUTPUT_DIR
rm -rf "$DOCKER_DIR/kline"
mkdir -p "$DOCKER_DIR/kline"
rsync -a \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '*.log' \
  --exclude 'src/linera_swap_kline.egg-info/' \
  --exclude 'tests/__pycache__/' \
  "$ROOT_DIR/service/kline/" "$DOCKER_DIR/kline/"

run_kline
run_funder

docker tag kline:latest docker.io/npool/kline:latest
docker tag funder:latest docker.io/npool/funder:latest
docker push docker.io/npool/kline:latest
docker push docker.io/npool/funder:latest
