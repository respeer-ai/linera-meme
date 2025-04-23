#!/bin/bash

####
## E.g. ./run_local.sh -f https://faucet.testnet-babbage.linera.net -C 0
####

LAN_IP=$( hostname -I | awk '{print $1}' )
FAUCET_URL=https://faucet.testnet-babbage.linera.net
CHAIN_OWNER_COUNT=4
CLUSTER=

options="f:c:C:W:z:"

while getopts $options opt; do
  case ${opt} in
    f) FAUCET_URL=${OPTARG} ;;
    z) CLUSTER=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..
DOMAIN_FILE="${ROOT_DIR}/webui/src/constant/domain.ts"

NGINX_TEMPLATE_FILE=${SCRIPT_DIR}/../configuration/template/nginx.conf.j2
COMPOSE_TEMPLATE_FILE=${SCRIPT_DIR}/../configuration/template/docker-compose.yml.j2

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

cd $SOURCE_DIR
rm linera-protocol-respeer -rf
git clone https://github.com/respeer-ai/linera-protocol.git linera-protocol-respeer
cd linera-protocol-respeer
git checkout respeer-maas-testnet_babbage-3dc32c18-2025-04-15
git pull origin respeer-maas-testnet_babbage-3dc32c18-2025-04-15

GIT_COMMIT=$(git rev-parse --short HEAD)
image_exists=`docker images | grep linera-respeer | wc -l`
if [ "x$image_exists" != "x1" ]; then
    docker build --build-arg git_commit="$GIT_COMMIT" --build-arg features="scylladb,metrics,disable-native-rpc,enable-wallet-rpc" -f docker/Dockerfile . -t linera-respeer || exit 1
fi

export PATH=$BIN_DIR:$PATH

LATEST_COMMIT=`git rev-parse HEAD`
LATEST_COMMIT=${LATEST_COMMIT:0:10}
INSTALLED_COMMIT=`linera --version | grep tree | awk -F '/' '{print $7}'`

if [ "x$LATEST_COMMIT" != "x$INSTALLED_COMMIT" ]; then
    cargo build --release --features disable-native-rpc,enable-wallet-rpc,storage-service
    mv $PWD/target/release/linera $BIN_DIR
fi

# Build linera docker image. If we have, just use it
# Official linera listen on localhost, so we use respeer here

# Applications are deployed outside of container, container only run service with wallets

cd $SCRIPT_DIR/..

# Compile applications
RUSTFLAGS= cargo build --release --target wasm32-unknown-unknown

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

# Create wallet for blob gateway
create_wallets blob-gateway

# Create wallet for ams
create_wallets ams

# Create wallet for swap
create_wallets swap

# Create wallet for proxy
create_wallets proxy

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
           --initial-balance "20."))

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

    jinja -d ${CONFIG_DIR}/$endpoint.nginx.json $NGINX_TEMPLATE_FILE > ${CONFIG_DIR}/$endpoint.nginx.conf
    cp -v ${CONFIG_DIR}/$endpoint.nginx.conf /etc/nginx/sites-enabled/
}

SUB_DOMAIN=$(echo "api.${CLUSTER}." | sed 's/\.\./\./g')

# Generate service nginx conf
generate_nginx_conf 20080 blobs blobgateway.com $CHAIN_OWNER_COUNT
generate_nginx_conf 21080 ams ams.respeer.ai $CHAIN_OWNER_COUNT
generate_nginx_conf 22080 swap lineraswap.fun $CHAIN_OWNER_COUNT
generate_nginx_conf 23080 proxy linerameme.fun $CHAIN_OWNER_COUNT
generate_nginx_conf 25080 kline kline.lineraswap.fun 1

sudo nginx -s reload

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
echo -e "   'http://${SUB_DOMAIN}blobgateway.com/api/blobs/chains/$BLOB_GATEWAY_CHAIN_ID/applications/$BLOB_GATEWAY_APPLICATION_ID',"
echo -e "   'http://${SUB_DOMAIN}ams.respeer.ai/api/ams/chains/$AMS_CHAIN_ID/applications/$AMS_APPLICATION_ID',"
echo -e "   'http://${SUB_DOMAIN}linerameme.fun/api/proxy/chains/$PROXY_CHAIN_ID/applications/$PROXY_APPLICATION_ID',"
echo -e "   'http://${SUB_DOMAIN}lineraswap.fun/api/swap/chains/$SWAP_CHAIN_ID/applications/$SWAP_APPLICATION_ID'\n\n"

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
    comma=$4
    image=$5

    echo "$comma{
      \"image\": \"${image}\",
      \"name\": \"${wallet_name}\",
      \"index\": \"${wallet_index}\",
      \"port\": $port
    }" >> $CONFIG_DIR/docker-compose.json
}

function run_services() {
    wallet_name=$1
    port_base=$2
    need_comma=$3
    image=$4

    [ "$need_comma" == "1" ] && comma=', '

    run_service $wallet_name creator $port_base "$comma" $image

    comma=', '

    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        port=$((port_base + (i + 1) * 2))
        run_service $wallet_name $i $port "$comma" $image
    done
}

echo '{' > $CONFIG_DIR/docker-compose.json
echo '  "services": [' >> $CONFIG_DIR/docker-compose.json

# Run services
run_services blob-gateway 20080 0 linera-respeer
run_services ams 21080 1 linera-respeer
run_services swap 22080 1 linera-respeer
run_services proxy 23080 1 linera-respeer

echo '  ]' >> $CONFIG_DIR/docker-compose.json
echo '}' >> $CONFIG_DIR/docker-compose.json

jinja -d ${CONFIG_DIR}/docker-compose.json $COMPOSE_TEMPLATE_FILE > ${CONFIG_DIR}/docker-compose.yml

cd $OUTPUT_DIR

docker stop `docker ps -a | grep "ams-\|blob-gateway-\| proxy-\|swap-" | awk '{print $1}'` > /dev/null 2>&1
docker rm `docker ps -a | grep "ams-\|blob-gateway-\| proxy-\|swap-" | awk '{print $1}'` > /dev/null 2>&1
docker stop maker-wallet kline maker
docker rm maker-wallet kline maker
docker rmi kline

LINERA_IMAGE=linera-respeer docker compose -f config/docker-compose.yml up --wait

rm $WALLET_DIR/maker/0 -rf
mkdir $WALLET_DIR/maker/0 -p
linera --wallet $WALLET_DIR/maker/0/wallet.json --storage rocksdb:$WALLET_DIR/maker/0/client.db wallet init --faucet $FAUCET_URL --with-new-chain

cp $ROOT_DIR/docker/docker-compose-wallet.yml $DOCKER_DIR
LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-wallet.yml up --wait

DATABASE_NAME=linera_swap_kline
DATABASE_USER=linera-swap
DATABASE_PASSWORD=12345679
DATABASE_PORT=3306
SWAP_HOST=${SUB_DOMAIN}lineraswap.fun
MEME_HOST=${SUB_DOMAIN}linerameme.fun

function run_mysql() {
    docker stop docker-mysql-1
    docker rm docker-mysql-1

    MYSQL_ROOT_PASSWORD=12345679 MYSQL_DATABASE=$DATABASE_NAME MYSQL_USER=$DATABASE_USER MYSQL_PASSWORD=$DATABASE_PASSWORD \
      docker compose -f $ROOT_DIR/docker/docker-compose-mysql.yml up --wait
}

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
      SWAP_HOST=$SWAP_HOST MEME_HOST=$MEME_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-maker.yml up --wait
}

cd $OUTPUT_DIR
cp $ROOT_DIR/service/kline $DOCKER_DIR -rf

run_mysql
run_kline

