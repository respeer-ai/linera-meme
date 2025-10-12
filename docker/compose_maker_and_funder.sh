#!/bin/bash

####
## E.g. ./compose_maker_and_funder.sh
####

LAN_IP=$( hostname -I | awk '{print $1}' )
CLUSTER=testnet-conway

options="z:"

while getopts $options opt; do
  case ${opt} in
    z) CLUSTER=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..
DOMAIN_FILE="${ROOT_DIR}/webui/src/constant/domain.ts"

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

SUB_DOMAIN=$(echo "api.${CLUSTER}." | sed 's/\.\./\./g')

function wallet_owner() {
    wallet_name=$1
    wallet_index=$2
    set -x
    sudo $BIN_DIR/linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | grep AccountOwner | grep -v ' - ' | awk '{print $5}'
    set +x
}

function wallet_chain_id() {
    wallet_name=$1
    wallet_index=$2
    sudo $BIN_DIR/linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | grep AccountOwner | grep -v " - " | awk '{print $2}'
}

cd $OUTPUT_DIR

docker stop kline maker funder
docker rm kline maker funder
docker rmi kline funder

DATABASE_NAME=linera_swap_kline
DATABASE_USER=linera-swap
DATABASE_PASSWORD=12345679
DATABASE_PORT=3306
SWAP_HOST=${SUB_DOMAIN}lineraswap.fun
PROXY_HOST=${SUB_DOMAIN}linerameme.fun

SWAP_APPLICATION_ID=$( cat $DOMAIN_FILE | grep 'SWAP_APPLICATION_ID' | awk -F ' = ' '{print $2}' | sed "s/'//g" )
PROXY_APPLICATION_ID=$( cat $DOMAIN_FILE | grep 'PROXY_APPLICATION_ID' | awk -F ' = ' '{print $2}' | sed "s/'//g" )

# Build kline and maker
function run_kline() {
    docker stop kline maker
    docker rm kline maker

    cp -v $ROOT_DIR/docker/*-entrypoint.sh $DOCKER_DIR
    docker build -f $ROOT_DIR/docker/Dockerfile . -t kline || exit 1

    LAN_IP=$LAN_IP DATABASE_HOST=$LAN_IP DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-kline.yml up --wait
    LAN_IP=$LAN_IP SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID WALLET_HOST=$LAN_IP:40082 WALLET_OWNER=$(wallet_owner maker 0) WALLET_CHAIN=$(wallet_chain_id maker 0) \
      SWAP_HOST=$SWAP_HOST PROXY_HOST=$PROXY_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-maker.yml up --wait
}

function run_funder() {
    docker stop funder
    docker rm funder

    image_exists=`docker images | grep funder | wc -l`
    if [ "x$image_exists" != "x1" ]; then
        cp -v $ROOT_DIR/docker/*-entrypoint.sh $DOCKER_DIR
        docker build -f $ROOT_DIR/docker/Dockerfile.funder . -t funder || exit 1
    fi

    LAN_IP=$LAN_IP SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-funder.yml up --wait
}


cd $OUTPUT_DIR
cp -v $ROOT_DIR/service/kline $DOCKER_DIR -rf

run_kline
run_funder
