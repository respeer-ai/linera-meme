#!/bin/bash

####
## E.g. ./restart.sh -C 1 -z testnet-conway
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

DOMAIN_FILE="${ROOT_DIR}/webui-v2/src/constant/domain.ts"
SUDO_PASSWORD=${SUDO_PASSWORD:-}

function sudo_run() {
    if [ -n "$SUDO_PASSWORD" ]; then
        printf '%s\n' "$SUDO_PASSWORD" | sudo -S "$@"
    else
        sudo "$@"
    fi
}

function get_domain_value() {
    application=$1
    sed ':a;N;s/=\n/=/;ta;P;D' "$DOMAIN_FILE" | grep "$application" | awk '{ print $NF }' | tr -d "'\""
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
DATABASE_HOST=docker-mysql-1
SWAP_HOST=${SUB_DOMAIN}lineraswap.fun
PROXY_HOST=${SUB_DOMAIN}linerameme.fun

export PATH=$BIN_DIR:$PATH
function ensure_mysql() {
    local local_no_proxy no_proxy_value
    local_no_proxy=localhost,127.0.0.1,::1,query-service,rpc,maker-wallet,maker,funder,kline,docker-mysql-1,api.lineraswap.fun,api.linerameme.fun,api.testnet-conway.lineraswap.fun,api.testnet-conway.linerameme.fun
    no_proxy_value=${no_proxy:-${NO_PROXY:-}}
    if [ -n "$no_proxy_value" ]; then
        no_proxy_value="$no_proxy_value,$local_no_proxy"
    else
        no_proxy_value="$local_no_proxy"
    fi

    docker stop docker-mysql-1 > /dev/null 2>&1 || true
    docker rm docker-mysql-1 > /dev/null 2>&1 || true

    MYSQL_ROOT_PASSWORD=$DATABASE_PASSWORD \
    MYSQL_DATABASE=$DATABASE_NAME \
    MYSQL_USER=$DATABASE_USER \
    MYSQL_PASSWORD=$DATABASE_PASSWORD \
    MYSQL_PORT=$DATABASE_PORT \
    LAN_IP=$LAN_IP \
    NO_PROXY="$no_proxy_value" \
    no_proxy="$no_proxy_value" \
      docker compose -f $ROOT_DIR/docker/docker-compose-mysql.yml up --wait
}


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

function wait_kline_ready() {
    local endpoint=http://localhost:25080/health

    for attempt in $(seq 1 120); do
        if curl --noproxy '*' -fsS --max-time 2 "$endpoint" > /dev/null 2>&1; then
            echo "kline HTTP is ready"
            return 0
        fi
        echo "waiting for kline HTTP readiness: attempt $attempt/120"
        sleep 2
    done

    echo "kline HTTP readiness check failed"
    curl --noproxy '*' -si --max-time 5 "$endpoint" || true
    exit 1
}

function restart_kline() {
    local local_no_proxy no_proxy_value
    local_no_proxy=localhost,127.0.0.1,::1,query-service,rpc,maker-wallet,maker,funder,kline,docker-mysql-1,api.lineraswap.fun,api.linerameme.fun,api.testnet-conway.lineraswap.fun,api.testnet-conway.linerameme.fun
    no_proxy_value=${no_proxy:-${NO_PROXY:-}}
    if [ -n "$no_proxy_value" ]; then
        no_proxy_value="$no_proxy_value,$local_no_proxy"
    else
        no_proxy_value="$local_no_proxy"
    fi
    LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-wallet.yml down
    MAKER_OWNER=$(wallet_owner maker 0)
    MAKER_CHAIN_ID=$(wallet_chain_id maker 0)
    BLOB_GATEWAY_OWNER=$(wallet_owner blob-gateway 0)
    AMS_OWNER=$(wallet_owner ams 0)
    PROXY_OWNER=$(wallet_owner proxy 0)
    SWAP_OWNER=$(wallet_owner swap 0)

    cp -v $ROOT_DIR/docker/docker-compose-query.yml $DOCKER_DIR
    NO_PROXY=$no_proxy_value no_proxy=$no_proxy_value \
    LAN_IP=$LAN_IP LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-query.yml down
    NO_PROXY=$no_proxy_value no_proxy=$no_proxy_value \
    LAN_IP=$LAN_IP LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-query.yml up --wait

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

        verify_payload='{"query":"query Chains { chains { list } }"}'
        verify=$(curl --noproxy '*' -sS http://localhost:24080 -H 'Content-Type: application/json' --data "$verify_payload" 2>&1 || true)
        if echo "$verify" | grep -q "$chain_id"; then
            echo "$label chain $chain_id already available in query-service"
            return 0
        fi

        payload=$(jq -cn \
            --arg owner "$owner" \
            --arg chainId "$chain_id" \
            '{query:"mutation ImportChain($owner: AccountOwner!, $chainId: ChainId!) { importChain(owner: $owner, chainId: $chainId) }", variables:{owner:$owner, chainId:$chainId}}')

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

    import_query_chain "$BLOB_GATEWAY_OWNER" "$BLOB_GATEWAY_CHAIN_ID" blob-gateway
    import_query_chain "$AMS_OWNER" "$AMS_CHAIN_ID" ams
    import_query_chain "$PROXY_OWNER" "$PROXY_CHAIN_ID" proxy
    import_query_chain "$SWAP_OWNER" "$SWAP_CHAIN_ID" swap

    start_chains
    NO_PROXY=$no_proxy_value no_proxy=$no_proxy_value \
    LAN_IP=$LAN_IP \
    LINERA_IMAGE=linera-respeer docker compose -f docker/docker-compose-wallet.yml up --wait

    NO_PROXY=$no_proxy_value no_proxy=$no_proxy_value \
    LAN_IP=$LAN_IP DATABASE_HOST=$DATABASE_HOST DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
      CHAIN_GRAPHQL_URL=http://query-service:30080 \
      CHAIN_GRAPHQL_WS_URL=ws://query-service:30080/ws \
      CATCH_UP_CHAIN_IDS=$SWAP_CHAIN_ID,$PROXY_CHAIN_ID \
      CATCH_UP_MAX_BLOCKS_PER_CHAIN=100 \
      docker compose -f $ROOT_DIR/docker/docker-compose-kline.yml down
    NO_PROXY=$no_proxy_value no_proxy=$no_proxy_value \
    LAN_IP=$LAN_IP DATABASE_HOST=$DATABASE_HOST DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
      PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
      CHAIN_GRAPHQL_URL=http://query-service:30080 \
      CHAIN_GRAPHQL_WS_URL=ws://query-service:30080/ws \
      CATCH_UP_CHAIN_IDS=$SWAP_CHAIN_ID,$PROXY_CHAIN_ID \
      CATCH_UP_MAX_BLOCKS_PER_CHAIN=100 \
      docker compose -f $ROOT_DIR/docker/docker-compose-kline.yml up --wait

    wait_kline_ready

    NO_PROXY=$no_proxy_value no_proxy=$no_proxy_value \
    LAN_IP=$LAN_IP DATABASE_HOST=$DATABASE_HOST DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID WALLET_HOST=$LAN_IP:40082 WALLET_METRICS_URL=http://$LAN_IP:40084/metrics WALLET_OWNER=$MAKER_OWNER WALLET_CHAIN=$MAKER_CHAIN_ID \
      SWAP_HOST=$SWAP_HOST PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-maker.yml down
    NO_PROXY=$no_proxy_value no_proxy=$no_proxy_value \
    LAN_IP=$LAN_IP DATABASE_HOST=$DATABASE_HOST DATABASE_USER=$DATABASE_USER DATABASE_PASSWORD=$DATABASE_PASSWORD DATABASE_PORT=$DATABASE_PORT DATABASE_NAME=$DATABASE_NAME \
      SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID WALLET_HOST=$LAN_IP:40082 WALLET_METRICS_URL=http://$LAN_IP:40084/metrics WALLET_OWNER=$MAKER_OWNER WALLET_CHAIN=$MAKER_CHAIN_ID \
      SWAP_HOST=$SWAP_HOST PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
      docker compose -f $ROOT_DIR/docker/docker-compose-maker.yml up --wait
}

function restart_webui() {
    docker compose -f $ROOT_DIR/docker/docker-compose-webui.yml down
    docker compose -f $ROOT_DIR/docker/docker-compose-webui.yml up -d --wait

    local nginx_template_file=$ROOT_DIR/configuration/template/nginx.conf.j2
    local webui_sub_domain
    webui_sub_domain=$(echo "${CLUSTER}." | sed "s/\.\./\./g")

    function generate_webui_nginx_conf() {
        local endpoint=$1
        local domain=$2

        echo "{
      \"service\": {
      \"mutation_endpoint\": \"$endpoint\",
      \"mutation_servers\": [\"localhost:18080\"],
      \"domain\": \"$domain\",
      \"sub_domain\": \"$webui_sub_domain\",
      \"api_endpoint\": \"$endpoint\"
    }
  }" > $CONFIG_DIR/$endpoint.nginx.json

        jinja -d $CONFIG_DIR/$endpoint.nginx.json $nginx_template_file > $CONFIG_DIR/$endpoint.nginx.conf
        sudo_run cp -v $CONFIG_DIR/$endpoint.nginx.conf /etc/nginx/sites-enabled/
    }

    generate_webui_nginx_conf linera-meme-webui linerameme.fun
    generate_webui_nginx_conf linera-swap-webui lineraswap.fun
    generate_webui_nginx_conf linera-blobgateway-webui blobgateway.com

    sudo_run nginx -s reload
}

function restart_funder() {
    local local_no_proxy no_proxy_value
    local_no_proxy=localhost,127.0.0.1,::1,query-service,rpc,maker-wallet,maker,funder,kline,docker-mysql-1,api.lineraswap.fun,api.linerameme.fun,api.testnet-conway.lineraswap.fun,api.testnet-conway.linerameme.fun
    no_proxy_value=${no_proxy:-${NO_PROXY:-}}
    if [ -n "$no_proxy_value" ]; then
        no_proxy_value="$no_proxy_value,$local_no_proxy"
    else
        no_proxy_value="$local_no_proxy"
    fi
    LAN_IP=$LAN_IP WALLET_HOST=$LAN_IP:40082 WALLET_OWNER=$MAKER_OWNER WALLET_CHAIN=$MAKER_CHAIN_ID MAKER_WALLET_HOST=$LAN_IP:40082 \
    SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
    PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
    docker compose -f $ROOT_DIR/docker/docker-compose-funder.yml down
    NO_PROXY=$no_proxy_value no_proxy=$no_proxy_value \
    LAN_IP=$LAN_IP WALLET_HOST=$LAN_IP:40082 WALLET_OWNER=$MAKER_OWNER WALLET_CHAIN=$MAKER_CHAIN_ID MAKER_WALLET_HOST=$LAN_IP:40082 \
    SWAP_CHAIN_ID=$SWAP_CHAIN_ID SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID SWAP_HOST=$SWAP_HOST \
    PROXY_CHAIN_ID=$PROXY_CHAIN_ID PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID PROXY_HOST=$PROXY_HOST \
    MAKER_WALLET_CHAIN_ID=$MAKER_CHAIN_ID \
    docker compose -f $ROOT_DIR/docker/docker-compose-funder.yml up --wait
}

cd $OUTPUT_DIR
stop_chains
ensure_mysql
restart_kline
restart_funder
restart_webui
