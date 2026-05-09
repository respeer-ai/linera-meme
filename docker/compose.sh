#!/bin/bash

set -euo pipefail

####
## E.g. ./compose.sh -f https://faucet.testnet-conway.linera.net -C 0
####

LAN_IP=$( hostname -I | awk '{print $1}' )
FAUCET_URL=https://faucet.testnet-conway.linera.net
CHAIN_FAUCET_URL=${CHAIN_FAUCET_URL:-https://faucet.testnet-conway.linera.net}
CHAIN_OWNER_COUNT=1
CLUSTER=testnet-conway
COMPILE=0
GIT_BRANCH=respeer-maas-testnet_conway-7e52827f-2026-03-15
COPY_TARGET=${COPY_TARGET:-0}
MULTI_OWNER_INITIAL_BALANCE=${MULTI_OWNER_INITIAL_BALANCE:-4.5}
LINERA_TIMEOUT_SECONDS=${LINERA_TIMEOUT_SECONDS:-180}
SUDO_PASSWORD=${SUDO_PASSWORD:-}
LINERA_RETRY_ATTEMPTS=${LINERA_RETRY_ATTEMPTS:-10}

options="f:z:C:"

while getopts $options opt; do
  case ${opt} in
    f) FAUCET_URL=${OPTARG} ;;
    z) CLUSTER=${OPTARG} ;;
    C) COMPILE=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..
DOMAIN_FILE="${ROOT_DIR}/webui-v2/src/constant/domain.ts"

NGINX_TEMPLATE_FILE=${SCRIPT_DIR}/../configuration/template/nginx.conf.j2
COMPOSE_TEMPLATE_FILE=${SCRIPT_DIR}/../configuration/template/docker-compose.yml.j2

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../output/compose"
mkdir -p $OUTPUT_DIR

function sudo_run() {
    if [ -n "$SUDO_PASSWORD" ]; then
        printf '%s\n' "$SUDO_PASSWORD" | sudo -S "$@"
    else
        sudo "$@"
    fi
}

sudo_run chown $USER:$(id -gn) $OUTPUT_DIR -R

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

WALLET_IMAGE_NAME=linera-respeer

IMAGE_NAME=linera-respeer
REPO_NAME=linera-protocol-respeer
REPO_BRANCH=$GIT_BRANCH
REPO_URL=https://github.com/respeer-ai/linera-protocol.git

# IMAGE_NAME=linera
# REPO_NAME=linera-protocol
# REPO_BRANCH=testnet_conway
# REPO_URL=https://github.com/linera-io/linera-protocol.git
# COPY_TARGET=1

PERSISTENT_CACHE_DIR="${OUTPUT_DIR}/cache/compose"
PERSISTENT_SOURCE_DIR="${PERSISTENT_CACHE_DIR}/${REPO_NAME}"
EXTERNAL_LINERA_DOCKER_DIR="${PERSISTENT_SOURCE_DIR}/docker"
mkdir -p "$PERSISTENT_CACHE_DIR"

mkdir -p "$SOURCE_DIR"
if [ ! -d "$PERSISTENT_SOURCE_DIR/.git" ]; then
    rm -rf "$PERSISTENT_SOURCE_DIR"
    git clone --branch "$REPO_BRANCH" --single-branch --depth 1 "$REPO_URL" "$PERSISTENT_SOURCE_DIR"
fi

cd "$PERSISTENT_SOURCE_DIR"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "x$CURRENT_BRANCH" != "x$REPO_BRANCH" ]; then
    rm -rf "$PERSISTENT_SOURCE_DIR"
    git clone --branch "$REPO_BRANCH" --single-branch --depth 1 "$REPO_URL" "$PERSISTENT_SOURCE_DIR"
    cd "$PERSISTENT_SOURCE_DIR"
fi
git fetch origin "$REPO_BRANCH" --depth 1
git checkout "$REPO_BRANCH"
git reset --hard "origin/$REPO_BRANCH"

rm -rf "$SOURCE_DIR/$REPO_NAME"
ln -s "$PERSISTENT_SOURCE_DIR" "$SOURCE_DIR/$REPO_NAME"
cd "$SOURCE_DIR/$REPO_NAME"

if [ "x$COPY_TARGET" = "x1" ]; then
    cd ..
    rm linera-protocol-respeer -rf
    git clone https://github.com/respeer-ai/linera-protocol.git linera-protocol-respeer
    cd linera-protocol-respeer
    git checkout respeer-maas-testnet_conway-7e52827f-2026-03-15
    git pull origin respeer-maas-testnet_conway-7e52827f-2026-03-15
    cp -v docker/* $SOURCE_DIR/$REPO_NAME/docker -rf
    cp -v configuration/* $SOURCE_DIR/$REPO_NAME/configuration -rf
    cd $SOURCE_DIR/$REPO_NAME
fi

docker stop `docker ps -a | grep "ams-\|blob-gateway-\| proxy-\|swap-" | awk '{print $1}'` > /dev/null 2>&1 || true
docker rm `docker ps -a | grep "ams-\|blob-gateway-\| proxy-\|swap-" | awk '{print $1}'` > /dev/null 2>&1 || true
docker stop maker-wallet query-service kline maker funder > /dev/null 2>&1 || true
docker rm maker-wallet query-service kline maker funder > /dev/null 2>&1 || true
docker rmi kline funder > /dev/null 2>&1 || true

export PATH=$BIN_DIR:$PATH

LATEST_COMMIT=`git rev-parse HEAD`
LATEST_COMMIT=${LATEST_COMMIT:0:10}
INSTALLED_COMMIT=`linera --version | grep tree | awk -F '/' '{print $7}' | awk '{print $1}'`
LINERA_SOURCE_CHANGED=1

if [ -n "$INSTALLED_COMMIT" ] && git rev-parse --verify "${INSTALLED_COMMIT}^{commit}" > /dev/null 2>&1; then
    if git diff --name-only "$INSTALLED_COMMIT" HEAD | grep -qv '^docker/'; then
        LINERA_SOURCE_CHANGED=1
    else
        LINERA_SOURCE_CHANGED=0
    fi
fi

if [ $COMPILE -eq 1 ] || [ "x${LATEST_COMMIT:0:8}" != "x${INSTALLED_COMMIT:0:8}" -a $LINERA_SOURCE_CHANGED -eq 1 ]; then
    CARGO_PROFILE_RELEASE_LTO=off \
    CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16 \
    cargo build --release --bin linera --features disable-native-rpc,enable-wallet-rpc,storage-service -j 1
    cp "$PWD/target/release/linera" "$BIN_DIR/linera"
fi

# Build linera docker image. If we have, just use it
# Official linera listen on localhost, so we use respeer here

# Applications are deployed outside of container, container only run service with wallets

cd $SCRIPT_DIR/..

# Compile chain applications only.
RUSTFLAGS= cargo build --release --target wasm32-unknown-unknown -j 1 \
    -p proxy \
    -p meme \
    -p swap \
    -p pool \
    -p blob-gateway \
    -p ams

COMPOSE_LOG_DIR="$OUTPUT_DIR/logs"
mkdir -p "$COMPOSE_LOG_DIR"
COMPOSE_DEBUG_LOG="$COMPOSE_LOG_DIR/compose_debug.log"

function log_step() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$message" >> "$COMPOSE_DEBUG_LOG"
    echo "$message" >&2
}

function linera_env_args() {
    :
}

function run_linera() {
    local step_name=$1
    shift

    log_step "START $step_name"
    if ! env $(linera_env_args) timeout --foreground "${LINERA_TIMEOUT_SECONDS}s" linera "$@" >> "$COMPOSE_DEBUG_LOG" 2>&1; then
        log_step "FAIL $step_name"
        tail -n 80 "$COMPOSE_DEBUG_LOG" >&2
        return 1
    fi
    log_step "OK $step_name"
}

function run_linera_retry() {
    local step_name=$1
    local max_attempts=$2
    shift 2

    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if run_linera "$step_name attempt=$attempt/$max_attempts" "$@"; then
            return 0
        fi
        if [ $attempt -eq $max_attempts ]; then
            log_step "ABORT $step_name exhausted retries"
            return 1
        fi
        sleep 5
        attempt=$((attempt + 1))
    done
}

function run_linera_capture() {
    local step_name=$1
    shift

    local stdout_file
    stdout_file=$(mktemp)
    log_step "START $step_name"
    if ! env $(linera_env_args) timeout --foreground "${LINERA_TIMEOUT_SECONDS}s" linera "$@" > "$stdout_file" 2>> "$COMPOSE_DEBUG_LOG"; then
        log_step "FAIL $step_name"
        rm -f "$stdout_file"
        tail -n 80 "$COMPOSE_DEBUG_LOG" >&2
        return 1
    fi
    log_step "OK $step_name"
    cat "$stdout_file"
    rm -f "$stdout_file"
}

function run_linera_capture_retry() {
    local step_name=$1
    local max_attempts=$2
    shift 2

    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if run_linera_capture "$step_name attempt=$attempt/$max_attempts" "$@"; then
            return 0
        fi
        if [ $attempt -eq $max_attempts ]; then
            log_step "ABORT $step_name exhausted retries"
            return 1
        fi
        sleep 5
        attempt=$((attempt + 1))
    done
}

function create_wallet() {
    wallet_name=$1
    wallet_index=$2
    new_chain=$3
    requested_chain_id=""

    rm -rf $WALLET_DIR/$wallet_name/$wallet_index
    mkdir -p $WALLET_DIR/$wallet_name/$wallet_index

    run_linera_retry "wallet_init ${wallet_name}/${wallet_index}" 3 \
           --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet init \
           --faucet $CHAIN_FAUCET_URL || return 1

    # Init wallet from faucet
    if [ "x$new_chain" = "x1" ]; then
        request_output=$(run_linera_capture_retry "wallet_request_chain ${wallet_name}/${wallet_index}" 3 \
               --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
               wallet request-chain \
               --faucet $CHAIN_FAUCET_URL) || return 1
        requested_chain_id=$(printf '%s\n' "$request_output" | awk 'NR == 1 { print $1; exit }')
        if [ -n "${requested_chain_id:-}" ]; then
            run_linera "wallet_set_default ${wallet_name}/${wallet_index} ${requested_chain_id}" \
                   --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
                   --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
                   --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
                   wallet set-default \
                   "$requested_chain_id" || return 1
        fi
    fi

    # Create unassigned owner for later multi-owner chain creation
    run_linera "wallet_keygen ${wallet_name}/${wallet_index}" \
           --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           keygen || return 1

    jq -r '.keys[-1][0]' \
       "$WALLET_DIR/$wallet_name/$wallet_index/keystore.json"
}

function create_wallets() {
    wallet_name=$1

    # Create creator chain which will be used to create multi-owner chain
    owners=($(create_wallet $wallet_name creator 1))

    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        # Creator new wallet which only have owner
        owners+=($(create_wallet $wallet_name $i 0))
    done

    echo ${owners[@]}
}

# Create wallet for blob gateway
BLOB_GATEWAY_OWNERS=$(create_wallets blob-gateway)
BLOB_GATEWAY_QUERY_OWNER=$(echo "$BLOB_GATEWAY_OWNERS" | awk '{print $2}')

# Create wallet for ams
AMS_OWNERS=$(create_wallets ams)
AMS_QUERY_OWNER=$(echo "$AMS_OWNERS" | awk '{print $2}')

# Create wallet for swap
SWAP_OWNERS=$(create_wallets swap)
SWAP_QUERY_OWNER=$(echo "$SWAP_OWNERS" | awk '{print $2}')

# Create wallet for proxy
PROXY_OWNERS=$(create_wallets proxy)
PROXY_QUERY_OWNER=$(echo "$PROXY_OWNERS" | awk '{print $2}')

function publish_bytecode_on_chain() {
    application_name=$1
    wasm_name=$(echo $2 | sed 's/-/_/g')

    run_linera_capture_retry "publish_module ${application_name}/${wasm_name}" "$LINERA_RETRY_ATTEMPTS" \
           --wallet $WALLET_DIR/$application_name/creator/wallet.json \
           --keystore $WALLET_DIR/$application_name/creator/keystore.json \
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
    $BIN_DIR/linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | awk '
                /^Chain ID:/ { chain=$3; next }
                /^Tags:/ { is_default = ($0 ~ /DEFAULT/ ? 1 : 0); next }
                /^Default owner:/ {
                    if (is_default && $3 != "No") {
                        print $3
                        exit
                    }
                }
           '
}

function wallet_chain_id() {
    wallet_name=$1
    wallet_index=$2
    $BIN_DIR/linera --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | awk '
                /^Chain ID:/ { chain=$3; next }
                /^Tags:/ { is_default = ($0 ~ /DEFAULT/ ? 1 : 0); next }
                /^Default owner:/ {
                    if (is_default && $3 != "No") {
                        print chain
                        exit
                    }
                }
           '
}

function assign_chain_to_owner() {
    wallet_name=$1
    wallet_index=$2
    chain_id=$3
    owner=$4

    run_linera "assign_chain ${wallet_name}/${wallet_index} ${chain_id}" \
           --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           assign --owner $owner --chain-id $chain_id
}

function to_json_list() {
    local input=()
    if [ $# -eq 1 ] && [[ "$1" == *" "* ]]; then
        read -ra input <<< "$1"
    else
        input=("$@")
    fi

    jq -n '$ARGS.positional' --args "${input[@]}"
}

to_map() {
    jq -n '
        reduce $ARGS.positional[] as $k ({}; .[$k] = 100)
    ' --args "$@"
}


function open_multi_owner_chain() {
    wallet_name=$1
    shift 1

    owners=("$@")
    chain_id=$(wallet_chain_id $wallet_name creator)

    owners_json=$(to_map "${owners[@]}")

    chain_id=($(run_linera_capture_retry "open_multi_owner_chain ${wallet_name}" "$LINERA_RETRY_ATTEMPTS" \
           --wallet $WALLET_DIR/$wallet_name/creator/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/creator/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/creator/client.db \
           open-multi-owner-chain \
           --from $chain_id \
           --owners "$owners_json" \
           --multi-leader-rounds 100 \
           --initial-balance "$MULTI_OWNER_INITIAL_BALANCE"))

    # Assign newly created chain to unassigned key.
    assign_chain_to_owner $wallet_name creator $chain_id ${owners[0]} # > /dev/null 2>&1
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        assign_chain_to_owner $wallet_name $i $chain_id ${owners[$((i+1))]} # > /dev/null 2>&1
    done

    run_linera "wallet_set_default ${wallet_name}/creator ${chain_id}" \
           --wallet $WALLET_DIR/$wallet_name/creator/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/creator/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/creator/client.db \
           wallet set-default \
           $chain_id

    echo $chain_id
}

# Create multi owner chains
# Create blob gateway multi owner chains
BLOB_GATEWAY_CHAIN_ID=$(open_multi_owner_chain blob-gateway $BLOB_GATEWAY_OWNERS)
# Create ams multi owner chains
AMS_CHAIN_ID=$(open_multi_owner_chain ams $AMS_OWNERS)
# Create proxy multi owner chains
PROXY_CHAIN_ID=$(open_multi_owner_chain proxy $PROXY_OWNERS)
# Create swap multi owner chains
SWAP_CHAIN_ID=$(open_multi_owner_chain swap $SWAP_OWNERS)

function process_inbox() {
    wallet_name=$1
    wallet_index=$2

    run_linera "process_inbox ${wallet_name}/${wallet_index}" \
           --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
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
        run_linera_capture_retry "create_application ${wallet_name}" "$LINERA_RETRY_ATTEMPTS" \
               --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
               create-application $module_id $chain_id \
               --json-argument "$argument" \
               --json-parameters "$parameters"
    elif [ "x$argument" != "x" ]; then
        run_linera_capture_retry "create_application ${wallet_name}" "$LINERA_RETRY_ATTEMPTS" \
               --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
               create-application $module_id $chain_id \
               --json-argument "$argument"
    elif [ "x$parameters" != "x" ]; then
        run_linera_capture_retry "create_application ${wallet_name}" "$LINERA_RETRY_ATTEMPTS" \
               --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
               create-application $module_id $chain_id \
               --json-parameters "$parameters"
    else
        run_linera_capture_retry "create_application ${wallet_name}" "$LINERA_RETRY_ATTEMPTS" \
               --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
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
    shift 2

    owners=("$@")
    owners_json=$(to_map "${owners[@]}")

    run_linera "change_ownership ${wallet_name} ${chain_id}" \
        --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
        --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
        --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
        change-ownership \
        --chain-id $chain_id \
        --owners "$owners_json" \
        --multi-leader-rounds 0
}

change_multi_owner_chain_single_leader blob-gateway $BLOB_GATEWAY_CHAIN_ID $BLOB_GATEWAY_OWNERS
change_multi_owner_chain_single_leader ams $AMS_CHAIN_ID $AMS_OWNERS
change_multi_owner_chain_single_leader proxy $PROXY_CHAIN_ID $PROXY_OWNERS
change_multi_owner_chain_single_leader swap $SWAP_CHAIN_ID $SWAP_OWNERS

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

    mutation_servers=$(service_servers $port_base $count)
    query_servers='"localhost:24080"'
    echo "{
        \"service\": {
            \"mutation_endpoint\": \"$endpoint\",
            \"mutation_servers\": [$mutation_servers],
            \"query_endpoint\": \"${endpoint}_query\",
            \"query_servers\": [$query_servers],
            \"domain\": \"$domain\",
            \"sub_domain\": \"$SUB_DOMAIN\",
            \"api_endpoint\": \"$endpoint\"
        }
    }" > ${CONFIG_DIR}/$endpoint.nginx.json

    jinja -d ${CONFIG_DIR}/$endpoint.nginx.json $NGINX_TEMPLATE_FILE > ${CONFIG_DIR}/$endpoint.nginx.conf
    sudo_run cp -v ${CONFIG_DIR}/$endpoint.nginx.conf /etc/nginx/sites-enabled/
}

SUB_DOMAIN=$(echo "api.${CLUSTER}." | sed 's/\.\./\./g')

# Generate service nginx conf
generate_nginx_conf 20080 blobs blobgateway.com $CHAIN_OWNER_COUNT
generate_nginx_conf 21080 ams ams.respeer.ai $CHAIN_OWNER_COUNT
generate_nginx_conf 22080 swap lineraswap.fun $CHAIN_OWNER_COUNT
generate_nginx_conf 23080 proxy linerameme.fun $CHAIN_OWNER_COUNT
generate_nginx_conf 25080 kline kline.lineraswap.fun 1

sudo_run nginx -s reload

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
echo -e "   http://${SUB_DOMAIN}blobgateway.com/api/blobs/query/chains/$BLOB_GATEWAY_CHAIN_ID/applications/$BLOB_GATEWAY_APPLICATION_ID"
echo -e "   http://${SUB_DOMAIN}ams.respeer.ai/api/ams/query/chains/$AMS_CHAIN_ID/applications/$AMS_APPLICATION_ID"
echo -e "   http://${SUB_DOMAIN}linerameme.fun/api/proxy/query/chains/$PROXY_CHAIN_ID/applications/$PROXY_APPLICATION_ID"
echo -e "   http://${SUB_DOMAIN}lineraswap.fun/api/swap/query/chains/$SWAP_CHAIN_ID/applications/$SWAP_APPLICATION_ID\n\n"

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
    comma=''

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
run_services blob-gateway 20080 0 $IMAGE_NAME
run_services ams 21080 1 $IMAGE_NAME
run_services swap 22080 1 $IMAGE_NAME
run_services proxy 23080 1 $IMAGE_NAME

echo '  ]' >> $CONFIG_DIR/docker-compose.json
echo "  ,\"lan_ip\": \"${LAN_IP}\"" >> $CONFIG_DIR/docker-compose.json
echo '}' >> $CONFIG_DIR/docker-compose.json

jinja -d ${CONFIG_DIR}/docker-compose.json $COMPOSE_TEMPLATE_FILE > ${CONFIG_DIR}/docker-compose.yml

cd $OUTPUT_DIR

cp -v "$EXTERNAL_LINERA_DOCKER_DIR"/rpc-entrypoint.sh "$DOCKER_DIR"/
cp -v "$EXTERNAL_LINERA_DOCKER_DIR"/wallet-entrypoint.sh "$DOCKER_DIR"/

rm -rf $WALLET_DIR/query/0
mkdir -p $WALLET_DIR/query/0
run_linera_retry "wallet_init query/0" "$LINERA_RETRY_ATTEMPTS" \
  --wallet $WALLET_DIR/query/0/wallet.json --keystore $WALLET_DIR/query/0/keystore.json --storage rocksdb://$WALLET_DIR/query/0/client.db wallet init --faucet $CHAIN_FAUCET_URL
run_linera_retry "wallet_request_chain query/0" "$LINERA_RETRY_ATTEMPTS" \
  --wallet $WALLET_DIR/query/0/wallet.json --keystore $WALLET_DIR/query/0/keystore.json --storage rocksdb://$WALLET_DIR/query/0/client.db wallet request-chain --faucet $CHAIN_FAUCET_URL

cp -v $ROOT_DIR/docker/docker-compose-query.yml $DOCKER_DIR
SUB_DOMAIN=$CLUSTER. LINERA_IMAGE=$IMAGE_NAME docker compose -f docker/docker-compose-query.yml up --wait

function wait_query_service_ready() {
    payload='{"query":"query Chains { chains { list } }"}'

    for attempt in $(seq 1 120); do
        resp=$(curl --noproxy '*' -vv http://localhost:24080 -H 'Content-Type: application/json' --data "$payload" 2>&1 || true)
        if echo "$resp" | grep -q '"data"'; then
            echo "query-service GraphQL is ready"
            return 0
        fi
        echo "waiting for query-service GraphQL readiness: attempt $attempt/120"
        echo "query-service readiness response: $resp"
        sleep 2
    done

    echo "query-service GraphQL readiness check failed"
    echo "$resp"
    exit 1
}

wait_query_service_ready

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
        resp=$(curl --noproxy '*' -sS http://localhost:24080 -H 'Content-Type: application/json' --data "$payload" 2>&1 || true)
        verify=$(curl --noproxy '*' -sS http://localhost:24080 -H 'Content-Type: application/json' --data "$verify_payload" 2>&1 || true)
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

import_query_chain "$BLOB_GATEWAY_QUERY_OWNER" "$BLOB_GATEWAY_CHAIN_ID" blob-gateway
import_query_chain "$AMS_QUERY_OWNER" "$AMS_CHAIN_ID" ams
import_query_chain "$PROXY_QUERY_OWNER" "$PROXY_CHAIN_ID" proxy
import_query_chain "$SWAP_QUERY_OWNER" "$SWAP_CHAIN_ID" swap

LINERA_IMAGE=$IMAGE_NAME docker compose -f config/docker-compose.yml up --wait

rm -rf $WALLET_DIR/maker/0
mkdir -p $WALLET_DIR/maker/0
run_linera_retry "wallet_init maker/0" "$LINERA_RETRY_ATTEMPTS" \
  --wallet $WALLET_DIR/maker/0/wallet.json --keystore $WALLET_DIR/maker/0/keystore.json --storage rocksdb://$WALLET_DIR/maker/0/client.db wallet init --faucet $CHAIN_FAUCET_URL
run_linera_retry "wallet_request_chain maker/0" "$LINERA_RETRY_ATTEMPTS" \
  --wallet $WALLET_DIR/maker/0/wallet.json --keystore $WALLET_DIR/maker/0/keystore.json --storage rocksdb://$WALLET_DIR/maker/0/client.db wallet request-chain --faucet $CHAIN_FAUCET_URL
MAKER_OWNER=$(wallet_owner maker 0)
MAKER_CHAIN_ID=$(wallet_chain_id maker 0)

cp -v $ROOT_DIR/docker/docker-compose-wallet.yml $DOCKER_DIR
SUB_DOMAIN=$CLUSTER. LINERA_IMAGE=$WALLET_IMAGE_NAME docker compose -f docker/docker-compose-wallet.yml up --wait

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

function run_mysql() {
    docker stop docker-mysql-1 > /dev/null 2>&1 || true
    docker rm docker-mysql-1 > /dev/null 2>&1 || true

    MYSQL_ROOT_PASSWORD=12345679 MYSQL_DATABASE=$DATABASE_NAME MYSQL_USER=$DATABASE_USER MYSQL_PASSWORD=$DATABASE_PASSWORD \
      docker compose -f $ROOT_DIR/docker/docker-compose-mysql.yml up --wait
}

# Build kline and maker
function run_kline() {
    docker stop kline maker > /dev/null 2>&1 || true
    docker rm kline maker > /dev/null 2>&1 || true

    cp -v $ROOT_DIR/docker/*-entrypoint.sh $DOCKER_DIR
    docker build --build-arg all_proxy="${all_proxy:-${ALL_PROXY:-}}" -f $ROOT_DIR/docker/Dockerfile $ROOT_DIR -t kline || exit 1

    NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
      LAN_IP=$LAN_IP DATABASE_HOST=$LAN_IP DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      PROXY_HOST=$PROXY_HOST PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID \
      CHAIN_GRAPHQL_URL=http://query-service:30080 \
      CATCH_UP_CHAIN_IDS=$SWAP_CHAIN_ID,$PROXY_CHAIN_ID \
      CATCH_UP_MAX_BLOCKS_PER_CHAIN=100 \
      SUB_DOMAIN=$CLUSTER. \
      docker compose -f $ROOT_DIR/docker/docker-compose-kline.yml up --wait
    NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
      LAN_IP=$LAN_IP SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID WALLET_HOST=$LAN_IP:40082 WALLET_METRICS_URL=http://$LAN_IP:40084/metrics WALLET_OWNER=$MAKER_OWNER WALLET_CHAIN=$MAKER_CHAIN_ID \
      SWAP_HOST=$SWAP_HOST PROXY_HOST=$PROXY_HOST DATABASE_HOST=$LAN_IP DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SUB_DOMAIN=$CLUSTER. \
      docker compose -f $ROOT_DIR/docker/docker-compose-maker.yml up --wait
}

function run_funder() {
    docker stop funder > /dev/null 2>&1 || true
    docker rm funder > /dev/null 2>&1 || true

    image_exists=`docker images | grep "^funder " | wc -l`
    if [ "x$image_exists" != "x1" ]; then
        cp -v $ROOT_DIR/docker/*-entrypoint.sh $DOCKER_DIR
        docker build --build-arg all_proxy="${all_proxy:-${ALL_PROXY:-}}" -f $ROOT_DIR/docker/Dockerfile.funder $ROOT_DIR -t funder || exit 1
    fi

    NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
      LAN_IP=$LAN_IP SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
      WALLET_HOST=$LAN_IP:40082 WALLET_OWNER=$MAKER_OWNER WALLET_CHAIN=$MAKER_CHAIN_ID \
      MAKER_WALLET_HOST=$LAN_IP:40082 MAKER_WALLET_CHAIN_ID=$MAKER_CHAIN_ID \
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

run_mysql
run_kline
run_funder
