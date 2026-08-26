#!/bin/bash

set -euo pipefail

####
## E.g. ./run_local.sh -f http://api.testnet-conway.faucet.respeer.ai/api/faucet -C 0 -z testnet-conway
## Set HTTPS_PROXY or https_proxy externally when external network access needs a proxy.
####

LAN_IP=$( hostname -I | awk '{print $1}' )
FAUCET_URL=https://faucet.testnet-conway.linera.net
COMPILE=1
GIT_BRANCH=respeer-maas-testnet_conway-7e52827f-2026-03-15
CHAIN_OWNER_COUNT=1
CLUSTER=testnet-conway
RUN_MAKER=1
SUDO_PASSWORD=${SUDO_PASSWORD:-}

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
ROOT_DIR=$SCRIPT_DIR/..

TEMPLATE_FILE=${SCRIPT_DIR}/../configuration/template/nginx.conf.j2
DOMAIN_FILE="${SCRIPT_DIR}/../webui-v2/src/constant/domain.ts"

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../output/local"
mkdir -p $OUTPUT_DIR

# Track PIDs of background services so we can clean them up on exit or on
# the next run if a previous invocation left them behind.
RUN_LOCAL_PID_FILE="$OUTPUT_DIR/run_local_pids"

# Generate config
CONFIG_DIR="${OUTPUT_DIR}/config"
mkdir -p $CONFIG_DIR

# Wallet directory
WALLET_DIR="${OUTPUT_DIR}/wallet"
mkdir -p $WALLET_DIR

# Source code directory
SOURCE_DIR="${OUTPUT_DIR}/source"
mkdir -p $SOURCE_DIR

# Keep Linera source and build cache under output/local so generated runtime
# artifacts stay in one tree while fresh restarts still reuse clone/build work.
PERSISTENT_CACHE_DIR="${OUTPUT_DIR}/cache/run_local"
PERSISTENT_LINERA_SOURCE_DIR="${PERSISTENT_CACHE_DIR}/linera-protocol"
mkdir -p "$PERSISTENT_CACHE_DIR"

# Run shared linera binary for common paths
COMMON_BIN_DIR="${OUTPUT_DIR}/bin/common"
mkdir -p $COMMON_BIN_DIR

# Run maker wallet with native RPC
MAKER_BIN_DIR="${OUTPUT_DIR}/bin/maker"
mkdir -p $MAKER_BIN_DIR

USER_WALLET_PORT=${USER_WALLET_PORT:-40092}

export PATH=$COMMON_BIN_DIR:$PATH

LINERA_SERVICE_HELP="$(linera service --help 2>&1 || true)"
LINERA_SERVICE_EXTRA_ARGS=()
if echo "$LINERA_SERVICE_HELP" | grep -q -- '--with-application-logs'; then
    LINERA_SERVICE_EXTRA_ARGS+=(--with-application-logs)
fi

# Install the linest deployment tool into a local venv.
LINEST_VENV_DIR="$OUTPUT_DIR/linest-venv"
LINEST_BIN="$LINEST_VENV_DIR/bin/linest"
if [ ! -x "$LINEST_BIN" ]; then
    python3 -m venv "$LINEST_VENV_DIR"
    "$LINEST_VENV_DIR/bin/pip" install -r "$ROOT_DIR/tools/deploy/requirements.txt"
    "$LINEST_VENV_DIR/bin/pip" install -e "$ROOT_DIR/tools/deploy"
fi

function external_proxy_env_args() {
    local all_proxy_val="${ALL_PROXY:-${all_proxy:-}}"
    local http_proxy_val="${HTTP_PROXY:-${http_proxy:-}}"
    local https_proxy_val="${HTTPS_PROXY:-${https_proxy:-}}"

    [ -n "$all_proxy_val" ] && printf 'all_proxy=%s\nALL_PROXY=%s\n' "$all_proxy_val" "$all_proxy_val"
    [ -n "$http_proxy_val" ] && printf 'http_proxy=%s\nHTTP_PROXY=%s\n' "$http_proxy_val" "$http_proxy_val"
    [ -n "$https_proxy_val" ] && printf 'https_proxy=%s\nHTTPS_PROXY=%s\n' "$https_proxy_val" "$https_proxy_val"
}

function no_external_proxy_env_args() {
    printf 'all_proxy=\nhttp_proxy=\nhttps_proxy=\nALL_PROXY=\nHTTP_PROXY=\nHTTPS_PROXY=\n'
}

function linera_env_args() {
    external_proxy_env_args
}

function ensure_linera_protocol_checkout() {
    # Ensure a fresh, correct-branch checkout of the respeer fork.
    if [ -d "$PERSISTENT_LINERA_SOURCE_DIR/.git" ]; then
        cd "$PERSISTENT_LINERA_SOURCE_DIR"
        local current_branch
        current_branch=$(git rev-parse --abbrev-ref HEAD)
        if [ "x$current_branch" != "x$GIT_BRANCH" ]; then
            cd - >/dev/null
            rm -rf "$PERSISTENT_LINERA_SOURCE_DIR"
        fi
    else
        rm -rf "$PERSISTENT_LINERA_SOURCE_DIR"
    fi

    if [ ! -d "$PERSISTENT_LINERA_SOURCE_DIR/.git" ]; then
        # We should run with respeer fork for blob query
        env $(external_proxy_env_args) git clone --branch $GIT_BRANCH --single-branch --depth 1 https://github.com/respeer-ai/linera-protocol.git "$PERSISTENT_LINERA_SOURCE_DIR"
    fi
    cd "$PERSISTENT_LINERA_SOURCE_DIR"
}

if [ "x$COMPILE" = "x1" ]; then
    # Install official linera for genesis cluster
    mkdir -p "$SOURCE_DIR"
    ensure_linera_protocol_checkout

    # Refresh the branch head when reusing the persistent checkout.
    env $(external_proxy_env_args) git fetch origin $GIT_BRANCH --depth 1
    git checkout $GIT_BRANCH
    git reset --hard origin/$GIT_BRANCH

    rm -rf "$SOURCE_DIR/linera-protocol"
    ln -s "$PERSISTENT_LINERA_SOURCE_DIR" "$SOURCE_DIR/linera-protocol"

    # Get latest commit to avoid compilation for the same version
    LATEST_COMMIT=`git rev-parse HEAD`
    LATEST_COMMIT=${LATEST_COMMIT:0:10}

    COMMON_COMMIT=""
    if [ -x "$COMMON_BIN_DIR/linera" ]; then
        COMMON_COMMIT=$("$COMMON_BIN_DIR/linera" --version | grep tree | awk -F '/' '{print $7}')
    fi

    if [ "x$LATEST_COMMIT" != "x$COMMON_COMMIT" ]; then
        CARGO_PROFILE_RELEASE_LTO=off \
        CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16 \
        cargo build --release --bin linera --features storage-service,enable-wallet-rpc -j 1
        rm -f $COMMON_BIN_DIR/linera
        cp target/release/linera $COMMON_BIN_DIR/linera
    fi
    test -x "$COMMON_BIN_DIR/linera"

    if [ "x$RUN_MAKER" = "x1" ]; then
        MAKER_COMMIT=""
        if [ -x "$MAKER_BIN_DIR/linera" ]; then
            MAKER_COMMIT=$("$MAKER_BIN_DIR/linera" --version | grep tree | awk -F '/' '{print $7}')
        fi

        if [ "x$LATEST_COMMIT" != "x$MAKER_COMMIT" ]; then
            rm -f $MAKER_BIN_DIR/linera
            cp target/release/linera $MAKER_BIN_DIR/linera
        fi
        test -x "$MAKER_BIN_DIR/linera"
    fi
fi

cd $SCRIPT_DIR/..

# Compile chain applications only. Host-only crates such as `service/decoder`
# should not participate in the wasm target build.
cargo build --release --target wasm32-unknown-unknown -j 1 \
    -p proxy \
    -p proxy-state \
    -p meme-app \
    -p meme-state \
    -p swap \
    -p pool \
    -p blob-gateway-app \
    -p blob-gateway-state \
    -p ams-app \
    -p ams-state

function cleanup_run_local_services() {
    # Kill known run_local background processes by command line pattern.
    # This handles cases where the PID file was lost or a previous run crashed
    # before writing all PIDs.
    pkill -f "linera.*service --port" 2>/dev/null || true
    pkill -f "service/kline/src/maker_api.py" 2>/dev/null || true
    pkill -f "service/kline/src/maker.py" 2>/dev/null || true
    pkill -f "service/kline/src/funder.py" 2>/dev/null || true

    # Kill any tracked background services from this or a previous run.
    if [ -f "$RUN_LOCAL_PID_FILE" ]; then
        local pids=()
        while IFS= read -r pid; do
            pids+=("$pid")
        done < "$RUN_LOCAL_PID_FILE"

        for pid in "${pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill -TERM "$pid" 2>/dev/null || true
            fi
        done

        sleep 1

        for pid in "${pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
        done

        rm -f "$RUN_LOCAL_PID_FILE"
    fi
}

# Make sure to clean up child processes on exit.
trap cleanup_run_local_services EXIT INT TERM

# Clean up services left behind by a previous interrupted run before we try to
# overwrite the shared linera binary (a running executable cannot be overwritten
# on Linux, leading to "Text file busy").
cleanup_run_local_services

RUN_LOCAL_LOG_DIR="$OUTPUT_DIR/logs"
mkdir -p "$RUN_LOCAL_LOG_DIR"
RUN_LOCAL_DEBUG_LOG="$RUN_LOCAL_LOG_DIR/run_local_debug.log"

function log_step() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$message" >> "$RUN_LOCAL_DEBUG_LOG"
    echo "$message" >&2
}

function run_linera() {
    local step_name=$1
    shift

    log_step "START $step_name"
    if ! env $(linera_env_args) linera "$@" >> "$RUN_LOCAL_DEBUG_LOG" 2>&1; then
        log_step "FAIL $step_name"
        tail -n 80 "$RUN_LOCAL_DEBUG_LOG" >&2
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

        log_step "RETRY $step_name sleeping before next attempt"
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
    if ! env $(linera_env_args) linera "$@" > "$stdout_file" 2>> "$RUN_LOCAL_DEBUG_LOG"; then
        log_step "FAIL $step_name"
        rm -f "$stdout_file"
        tail -n 80 "$RUN_LOCAL_DEBUG_LOG" >&2
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

        log_step "RETRY $step_name sleeping before next attempt"
        sleep 5
        attempt=$((attempt + 1))
    done
}

function run_linest() {
    local step_name=$1
    shift

    log_step "START $step_name"
    if ! env $(linera_env_args) "$@" 2>&1 | tee -a "$RUN_LOCAL_DEBUG_LOG"; then
        log_step "FAIL $step_name"
        tail -n 80 "$RUN_LOCAL_DEBUG_LOG" >&2
        return 1
    fi
    log_step "OK $step_name"
}

function sudo_run() {
    if [ -n "$SUDO_PASSWORD" ]; then
        printf '%s\n' "$SUDO_PASSWORD" | sudo -S "$@"
    else
        sudo "$@"
    fi
}

function wallet_init_clean() {
    local wallet_name=$1
    local wallet_index=$2

    local attempt=1
    while [ $attempt -le 3 ]; do
        rm -rf $WALLET_DIR/$wallet_name/$wallet_index
        mkdir -p $WALLET_DIR/$wallet_name/$wallet_index

        if run_linera "wallet_init ${wallet_name}/${wallet_index} attempt=${attempt}/3" \
               --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
               wallet init \
               --faucet $FAUCET_URL; then
            return 0
        fi

        if [ $attempt -eq 3 ]; then
            log_step "ABORT wallet_init ${wallet_name}/${wallet_index} exhausted retries"
            return 1
        fi

        log_step "RETRY wallet_init ${wallet_name}/${wallet_index} sleeping before next attempt"
        sleep 5
        attempt=$((attempt + 1))
    done
}

function create_wallet() {
    wallet_name=$1
    wallet_index=$2
    new_chain=$3

    wallet_init_clean $wallet_name $wallet_index || return 1
    if [ "x$new_chain" = "x1" ]; then
        run_linera_retry "wallet_request_chain ${wallet_name}/${wallet_index}" 3 \
               --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
               wallet request-chain \
               --faucet $FAUCET_URL || return 1
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
    expected_owner_count=$((CHAIN_OWNER_COUNT + 1))

    # Create creator chain which will be used to create multi-owner chain
    owners=()
    owner=$(create_wallet $wallet_name creator 1) || return 1
    owners+=("$owner")

    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        # Creator new wallet which only have owner
        owner=$(create_wallet $wallet_name $i 0) || return 1
        owners+=("$owner")
    done

    if [ "${#owners[@]}" -ne "$expected_owner_count" ]; then
        log_step "ABORT create_wallets ${wallet_name} expected ${expected_owner_count} owners, got ${#owners[@]}"
        return 1
    fi

    echo ${owners[@]}
}

function create_operator_wallet() {
    wallet_init_clean operator 0 || return 1
    run_linera_retry "wallet_request_chain operator/0" 3 \
           --wallet $WALLET_DIR/operator/0/wallet.json \
           --keystore $WALLET_DIR/operator/0/keystore.json \
           --storage rocksdb://$WALLET_DIR/operator/0/client.db \
           wallet request-chain \
           --faucet $FAUCET_URL || return 1
    wallet_owner operator 0
}

# Create wallet for swap
SWAP_OWNERS=$(create_wallets swap)

function publish_bytecode_on_chain() {
    application_name=$1
    wasm_name=$(echo $2 | sed 's/-/_/g')
    run_linera_capture_retry "publish_module ${application_name}/${wasm_name}" 3 \
           --wallet $WALLET_DIR/$application_name/creator/wallet.json \
           --keystore $WALLET_DIR/$application_name/creator/keystore.json \
           --storage rocksdb://$WALLET_DIR/$application_name/creator/client.db \
           publish-module $SCRIPT_DIR/../target/wasm32-unknown-unknown/release/${wasm_name}_{contract,service}.wasm
}

function publish_bytecode() {
    publish_bytecode_on_chain $1 $1
}

# Publish bytecode then create applications
SWAP_MODULE_ID=$(publish_bytecode swap)
POOL_MODULE_ID=$(publish_bytecode_on_chain swap pool)

function wallet_owner() {
    wallet_name=$1
    wallet_index=$2
    run_linera_capture_retry "wallet_show_owner ${wallet_name}/${wallet_index}" 3 \
           --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | awk '/^Default owner:/ { if ($3 != "No") print $3 }'
}

function wallet_chain_owner() {
    wallet_name=$1
    wallet_index=$2
    chain_id=$3

    run_linera_capture_retry "wallet_show_chain_owner ${wallet_name}/${wallet_index} chain=${chain_id}" 3 \
        --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
        --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
        --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
        wallet show \
        | awk -F: -v id="$chain_id" '$1 == "Chain ID" {gsub(/^[ \t]+/, "", $2); if ($2 == id) found=1; else found=0} $1 == "Default owner" {if (found) {gsub(/^[ \t]+/, "", $2); print $2; found=0}}'
}

function wallet_unassigned_owner() {
    wallet_name=$1
    wallet_index=$2
    cat $WALLET_DIR/$wallet_name/$wallet_index/wallet.json | jq -r '.unassigned_key_pairs | keys[]'
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
    run_linera_capture_retry "wallet_show_chain_id ${wallet_name}/${wallet_index}" 3 \
           --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
           wallet show \
           | awk '/^Chain ID:/ {chain=$3} /^Default owner:/ {if ($3 != "No") print chain}'
}

function assign_chain_to_owner() {
    wallet_name=$1
    wallet_index=$2
    chain_id=$3
    owner=$4

    run_linera_retry "assign_chain_to_owner ${wallet_name}/${wallet_index} chain=${chain_id}" 3 \
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

    # owners_json=$(to_json_list "${owners[@]}")
    owner_weights=$(to_map "${owners[@]}")

    chain_id=($(run_linera_capture_retry "open_multi_owner_chain ${wallet_name}" 3 \
           --wallet $WALLET_DIR/$wallet_name/creator/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/creator/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/creator/client.db \
           open-multi-owner-chain \
           --from $chain_id \
           --owners "$owner_weights" \
           --multi-leader-rounds 100 \
           --initial-balance "20."))

    # Assign newly created chain to unassigned key.
    assign_chain_to_owner $wallet_name creator $chain_id ${owners[0]} # > /dev/null 2>&1
    for i in $(seq 0 $((CHAIN_OWNER_COUNT - 1))); do
        assign_chain_to_owner $wallet_name $i $chain_id ${owners[$((i+1))]} # > /dev/null 2>&1
    done

    run_linera_retry "wallet_set_default ${wallet_name} chain=${chain_id}" 3 \
           --wallet $WALLET_DIR/$wallet_name/creator/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/creator/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/creator/client.db \
           wallet set-default \
           $chain_id > /dev/null 2>&1

    echo $chain_id
}

# Create swap multi owner chain (swap is not yet managed by linest).
SWAP_CHAIN_ID=$(open_multi_owner_chain swap $SWAP_OWNERS)

SWAP_QUERY_OWNER=$(wallet_chain_owner swap 0 $SWAP_CHAIN_ID)

function process_inbox() {
    wallet_name=$1
    wallet_index=$2

    run_linera_retry "process_inbox ${wallet_name}/${wallet_index}" 3 \
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

function run_named_service() {
    service_name=$1
    wallet_name=$2
    wallet_index=$3
    port=$4
    shift 4

    # Clean up any previous service listening on this port before starting.
    pkill -f "linera.*service --port $port" 2>/dev/null || true

    env $(linera_env_args) "$@" \
        linera "${LINERA_SERVICE_EXTRA_ARGS[@]}" \
               --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
               service --port $port > "${service_name}_${port}.log" 2>&1 &
    echo $! >> "$RUN_LOCAL_PID_FILE"
}

function wait_query_service_ready() {
    local bootstrap_pid=$1
    payload='{"query":"query Chains { chains { list } }"}'

    attempt=0
    while true; do
        if ! kill -0 "$bootstrap_pid" 2>/dev/null; then
            log_step "linest bootstrap process exited; aborting query service wait"
            exit 1
        fi

        resp=$(curl --noproxy '*' -sS http://localhost:24080 -H 'Content-Type: application/json' --data "$payload" 2>&1 || true)
        if echo "$resp" | grep -q '"data"'; then
            return 0
        fi

        attempt=$((attempt + 1))
        if [ $((attempt % 10)) -eq 0 ]; then
            log_step "Waiting for query service on localhost:24080 to become ready (attempt $attempt)"
        fi

        sleep 2
    done
}

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

# Exhaust swap chain messages (proxy inboxes are handled by linest post-deploy sync).
process_inboxes swap

# Bootstrap shared wallets and services for linest.
# Start from a clean linest state so stale domain/deployment records from
# previous runs (which reference old chain IDs) are not reused.
LINEST_BASE_DIR="$OUTPUT_DIR/linest"
mkdir -p "$LINEST_BASE_DIR"

env $(linera_env_args) "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    bootstrap \
    --faucet-url "$FAUCET_URL" \
    --wallet-dir "$WALLET_DIR" \
    --operator-wallet-dir "$WALLET_DIR/operator/0" \
    --query-wallet-dir "$WALLET_DIR/query/0" \
    --query-service-port 24080 > "$RUN_LOCAL_LOG_DIR/linest_bootstrap.log" 2>&1 &
linest_bootstrap_pid=$!
echo "$linest_bootstrap_pid" >> "$RUN_LOCAL_PID_FILE"

wait_query_service_ready "$linest_bootstrap_pid"

# Deploy blob-gateway business app and typed state app via linest.
# Ensure the blob-gateway wallet tree exists. If it was wiped externally,
# also clear the linest registry so the deployment starts fresh instead of
# trying to reuse stale owner/chain records.
if [ ! -d "$WALLET_DIR/blob-gateway" ]; then
    rm -f "$LINEST_BASE_DIR/deployments/local/blob-gateway.json"
fi
mkdir -p "$WALLET_DIR/blob-gateway"

run_linest "linest_deploy_blob_gateway" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    app deploy \
    --repo-dir "$ROOT_DIR" \
    --name blob-gateway \
    --contract-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/blob_gateway_app_contract.wasm" \
    --service-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/blob_gateway_app_service.wasm" \
    --state-contract-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/blob_gateway_state_contract.wasm" \
    --state-service-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/blob_gateway_state_service.wasm" \
    --ensure-wallet \
    --faucet-url "$FAUCET_URL" \
    --wallet-owner-count "$CHAIN_OWNER_COUNT" \
    --no-business-argument

BLOB_GATEWAY_STATUS_JSON=$("$LINEST_BIN" --base-dir "$LINEST_BASE_DIR" --env local app status --name blob-gateway --format json)
BLOB_GATEWAY_CHAIN_ID=$(echo "$BLOB_GATEWAY_STATUS_JSON" | jq -r '.business_app.creator_chain_id')
BLOB_GATEWAY_APPLICATION_ID=$(echo "$BLOB_GATEWAY_STATUS_JSON" | jq -r '.business_app.application_id')
BLOB_GATEWAY_STATE_APPLICATION_ID=$(echo "$BLOB_GATEWAY_STATUS_JSON" | jq -r '.state_apps[0].application_id // empty')

import_query_chain "$SWAP_QUERY_OWNER" "$SWAP_CHAIN_ID" swap

function create_application() {
    wallet_name=$1
    module_id=$2
    argument=$3
    parameters=$4
    chain_id=$5

    if [ "x$argument" != "x" -a "x$parameters" != "x" ]; then
        run_linera_capture_retry "create_application ${wallet_name} chain=${chain_id}" 3 \
               --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
               create-application $module_id $chain_id \
               --json-argument "$argument" \
               --json-parameters "$parameters"
    elif [ "x$argument" != "x" ]; then
        run_linera_capture_retry "create_application ${wallet_name} chain=${chain_id}" 3 \
               --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
               create-application $module_id $chain_id \
               --json-argument "$argument"
    elif [ "x$parameters" != "x" ]; then
        run_linera_capture_retry "create_application ${wallet_name} chain=${chain_id}" 3 \
               --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
               create-application $module_id $chain_id \
               --json-parameters "$parameters"
    else
        run_linera_capture_retry "create_application ${wallet_name} chain=${chain_id}" 3 \
               --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
               create-application $module_id $chain_id
    fi
}

# Create applications
SWAP_APPLICATION_ID=$(create_application swap $SWAP_MODULE_ID "{\"pool_bytecode_id\": \"$POOL_MODULE_ID\"}" '{}' $SWAP_CHAIN_ID)

# Deploy meme bytecode via linest (bytecode-only: no application instances are created).
# Proxy will later use these module ids when it creates individual meme apps.
mkdir -p "$WALLET_DIR/meme"

run_linest "linest_deploy_meme_bytecode" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    app deploy \
    --repo-dir "$ROOT_DIR" \
    --name meme \
    --bytecode-only \
    --contract-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/meme_app_contract.wasm" \
    --service-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/meme_app_service.wasm" \
    --state-contract-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/meme_state_contract.wasm" \
    --state-service-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/meme_state_service.wasm" \
    --ensure-wallet \
    --faucet-url "$FAUCET_URL" \
    --wallet-owner-count "$CHAIN_OWNER_COUNT"

MEME_STATUS_JSON=$("$LINEST_BIN" --base-dir "$LINEST_BASE_DIR" --env local app status --name meme --format json)
MEME_MODULE_ID=$(echo "$MEME_STATUS_JSON" | jq -r '.business_module_id // empty')
MEME_STATE_VERSION=$(echo "$MEME_STATUS_JSON" | jq -r '.state_apps[0].version // empty')
MEME_STATE_MODULE_ID=$(echo "$MEME_STATUS_JSON" | jq -r '.state_apps[0].module_id // empty')

if [ -z "$MEME_MODULE_ID" ] || [ -z "$MEME_STATE_VERSION" ] || [ -z "$MEME_STATE_MODULE_ID" ]; then
    echo "Failed to resolve meme bytecode module ids from linest status" >&2
    exit 1
fi

run_linest "linest_deploy_proxy" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    app deploy \
    --repo-dir "$ROOT_DIR" \
    --name proxy \
    --contract-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/proxy_contract.wasm" \
    --service-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/proxy_service.wasm" \
    --state-contract-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/proxy_state_contract.wasm" \
    --state-service-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/proxy_state_service.wasm" \
    --ensure-wallet \
    --faucet-url "$FAUCET_URL" \
    --wallet-owner-count "$CHAIN_OWNER_COUNT"

PROXY_STATUS_JSON=$("$LINEST_BIN" --base-dir "$LINEST_BASE_DIR" --env local app status --name proxy --format json)
PROXY_CHAIN_ID=$(echo "$PROXY_STATUS_JSON" | jq -r '.business_app.creator_chain_id')
PROXY_APPLICATION_ID=$(echo "$PROXY_STATUS_JSON" | jq -r '.business_app.application_id')
PROXY_STATE_APPLICATION_ID=$(echo "$PROXY_STATUS_JSON" | jq -r '.state_apps[0].application_id // empty')

INIT_MUTATION='mutation Initialize($argument: InitializeArgument!) { initialize(argument: $argument) }'
INIT_VARS=$(jq -n \
    --arg swap "$SWAP_APPLICATION_ID" \
    --arg meme "$MEME_MODULE_ID" \
    --argjson meme_state_version "$MEME_STATE_VERSION" \
    --arg meme_state_module "$MEME_STATE_MODULE_ID" \
    '{argument: {initialOperators: [], genesisMinerOwners: [], swapApplicationId: $swap, memeBytecodeId: $meme, memeStateBytecodeIds: [{version: $meme_state_version, moduleId: $meme_state_module}]}}')

PROXY_INIT_OPERATION=$(run_linera_capture "bcs_serialize_proxy_initialize" \
    --wallet $WALLET_DIR/proxy/0/wallet.json \
    --keystore $WALLET_DIR/proxy/0/keystore.json \
    --storage rocksdb://$WALLET_DIR/proxy/0/client.db \
    bcs-serilize-application-operation \
    --operation-type-crate "$ROOT_DIR/abi" \
    --operation-type "abi::proxy::ProxyOperation" \
    --query "$INIT_MUTATION" \
    --variables "$INIT_VARS")

run_linera "execute_proxy_initialize" \
    --wallet $WALLET_DIR/proxy/0/wallet.json \
    --keystore $WALLET_DIR/proxy/0/keystore.json \
    --storage rocksdb://$WALLET_DIR/proxy/0/client.db \
    execute-application-operation \
    --chain-id "$PROXY_CHAIN_ID" \
    --application-id "$PROXY_APPLICATION_ID" \
    --operation "$PROXY_INIT_OPERATION"

# Register non-linest apps so domain.ts can be generated from one place.
run_linest "linest_domain_register_blob_gateway" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    domain register \
    --name blob-gateway \
    --chain-id "$BLOB_GATEWAY_CHAIN_ID" \
    --application-id "$BLOB_GATEWAY_APPLICATION_ID"

run_linest "linest_domain_register_swap" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    domain register \
    --name swap \
    --chain-id "$SWAP_CHAIN_ID" \
    --application-id "$SWAP_APPLICATION_ID"

run_linest "linest_domain_register_proxy" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    domain register \
    --name proxy \
    --chain-id "$PROXY_CHAIN_ID" \
    --application-id "$PROXY_APPLICATION_ID"

# Deploy AMS business app and typed state app via linest.
# Start from a clean AMS wallet tree so stale owner keys/chains from previous
# runs are not reused.
mkdir -p "$WALLET_DIR/ams"

run_linest "linest_deploy_ams" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    app deploy \
    --repo-dir "$ROOT_DIR" \
    --name ams \
    --contract-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/ams_app_contract.wasm" \
    --service-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/ams_app_service.wasm" \
    --state-contract-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/ams_state_contract.wasm" \
    --state-service-bytecode "$ROOT_DIR/target/wasm32-unknown-unknown/release/ams_state_service.wasm" \
    --ensure-wallet \
    --faucet-url "$FAUCET_URL" \
    --wallet-owner-count "$CHAIN_OWNER_COUNT"

AMS_STATUS_JSON=$("$LINEST_BIN" --base-dir "$LINEST_BASE_DIR" --env local app status --name ams --format json)
AMS_APPLICATION_ID=$(echo "$AMS_STATUS_JSON" | jq -r '.business_app.application_id')
AMS_CHAIN_ID=$(echo "$AMS_STATUS_JSON" | jq -r '.business_app.creator_chain_id')
AMS_STATE_APPLICATION_ID=$(echo "$AMS_STATUS_JSON" | jq -r '.state_apps[0].application_id // empty')

# Register AMS so domain.ts generation includes it.
run_linest "linest_domain_register_ams" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    domain register \
    --name ams \
    --chain-id "$AMS_CHAIN_ID" \
    --application-id "$AMS_APPLICATION_ID"

# Exhaust chain messages for the remaining apps.
process_inboxes proxy
process_inboxes swap

function change_multi_owner_chain_single_leader() {
    wallet_name=$1
    chain_id=$2
    shift 2

    owners=("$@")
    # owners_json=$(to_json_list "${owners[@]}")
    owner_weights=$(to_map "${owners[@]}")

    run_linera_retry "change_ownership ${wallet_name} chain=${chain_id}" 3 \
           --wallet $WALLET_DIR/$wallet_name/0/wallet.json \
           --keystore $WALLET_DIR/$wallet_name/0/keystore.json \
           --storage rocksdb://$WALLET_DIR/$wallet_name/0/client.db \
           change-ownership \
           --chain-id $chain_id \
           --owners "$owner_weights" \
           --multi-leader-rounds 0
}

# Proxy ownership is switched to single-leader by linest post-deploy sync.
change_multi_owner_chain_single_leader swap $SWAP_CHAIN_ID $SWAP_OWNERS

# Top up linest-managed chains (e.g. AMS) to the target minimum balance.
run_linest "linest_fund_chains" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    fund chains \
    --claim-from-faucet \
    --faucet-url "$FAUCET_URL" \
    --min-balance 100

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
    query_servers=$(service_servers $port_base $count)
    mutation_endpoint="${endpoint}_mutation"
    query_endpoint="${endpoint}_query"
    echo "{
        \"service\": {
            \"mutation_endpoint\": \"$mutation_endpoint\",
            \"mutation_servers\": [$mutation_servers],
            \"query_endpoint\": \"$query_endpoint\",
            \"query_servers\": [$query_servers],
            \"domain\": \"$domain\",
            \"sub_domain\": \"$SUB_DOMAIN\",
            \"api_endpoint\": \"$endpoint\"
        }
    }" > ${CONFIG_DIR}/$endpoint.nginx.json

    jinja -d ${CONFIG_DIR}/$endpoint.nginx.json $TEMPLATE_FILE > ${CONFIG_DIR}/$endpoint.nginx.conf
    sudo_run cp ${CONFIG_DIR}/$endpoint.nginx.conf /etc/nginx/sites-enabled/
}

SUB_DOMAIN=$(echo "api.${CLUSTER}." | sed 's/\.\./\./g')

# Generate service nginx conf
generate_nginx_conf 20080 blobs blobgateway.com $CHAIN_OWNER_COUNT
generate_nginx_conf 21080 ams ams.respeer.ai $CHAIN_OWNER_COUNT
generate_nginx_conf 22080 swap lineraswap.fun $CHAIN_OWNER_COUNT
generate_nginx_conf 23080 proxy linerameme.fun $CHAIN_OWNER_COUNT
generate_nginx_conf 25080 kline kline.lineraswap.fun 1
sudo_run nginx -t
sudo_run systemctl reload nginx

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

# Generate domain.ts from the unified registry.
run_linest "linest_domain_generate" \
    "$LINEST_BIN" \
    --base-dir "$LINEST_BASE_DIR" \
    --env local \
    domain generate \
    --cluster "$CLUSTER" \
    --output "$DOMAIN_FILE"

function run_service() {
    wallet_name=$1
    wallet_index=$2
    port=$3

    env $(linera_env_args) \
        linera "${LINERA_SERVICE_EXTRA_ARGS[@]}" \
               --wallet $WALLET_DIR/$wallet_name/$wallet_index/wallet.json \
               --keystore $WALLET_DIR/$wallet_name/$wallet_index/keystore.json \
               --storage rocksdb://$WALLET_DIR/$wallet_name/$wallet_index/client.db \
               service --port $port > ${wallet_name}_${port}.log 2>&1 &
    echo $! >> "$RUN_LOCAL_PID_FILE"
}

function ensure_background_process() {
    local pid=$1
    local name=$2
    local log_file=$3

    sleep 2
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "$name exited during startup"
        if [ -f "$log_file" ]; then
            tail -n 120 "$log_file"
        fi
        exit 1
    fi
    echo "$pid" >> "$RUN_LOCAL_PID_FILE"
}

function wait_http_ready() {
    local name=$1
    local url=$2

    for attempt in $(seq 1 60); do
        if curl --noproxy '*' -sS "$url" > /dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done

    echo "$name readiness check failed: $url"
    return 1
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

# Run wallet services for runtime access.
run_services blob-gateway 20080
run_services ams 21080
run_services swap 22080
run_services proxy 23080

DATABASE_NAME=linera_swap_kline
DATABASE_USER=linera-swap
DATABASE_PASSWORD=12345679
DATABASE_HOST=localhost
DATABASE_PORT=3306
SWAP_HOST=${SUB_DOMAIN}lineraswap.fun
PROXY_HOST=${SUB_DOMAIN}linerameme.fun
OBSERVABILITY_CHAIN_GRAPHQL_URL=http://localhost:24080/
OBSERVABILITY_CATCH_UP_CHAINS="$SWAP_CHAIN_ID,$PROXY_CHAIN_ID"

function run_mysql() {
    docker stop docker-mysql-1 || true
    docker rm docker-mysql-1 || true

    MYSQL_ROOT_PASSWORD=12345679 MYSQL_DATABASE=$DATABASE_NAME MYSQL_USER=$DATABASE_USER MYSQL_PASSWORD=$DATABASE_PASSWORD \
      docker compose -f $ROOT_DIR/docker/docker-compose-mysql.yml up --wait
}

run_mysql

VENV_DIR=$HOME/.linera-meme-service-venv
mkdir -p $VENV_DIR
python3 -m venv $VENV_DIR

PYTHON3=$VENV_DIR/bin/python3
PIP3=$VENV_DIR/bin/pip3

env $(external_proxy_env_args) $PIP3 install PySocks

function run_kline() {
    cargo build --release -p decoder --bin canonical_decoder -j 1

    cd service/kline

    env $(external_proxy_env_args) $PIP3 install 'uvicorn[standard]'
    env $(external_proxy_env_args) $PIP3 install --upgrade pip
    env $(external_proxy_env_args) $PIP3 install -r requirements.txt
    env $(external_proxy_env_args) $PIP3 install -e .

    $PIP3 uninstall websocket -y
    $PIP3 uninstall websocket-client -y
    env $(external_proxy_env_args) $PIP3 install websocket-client

    env $(no_external_proxy_env_args) KLINE_RUST_DECODER_BIN=$PWD/../../target/release/canonical_decoder $PYTHON3 -u src/kline.py \
        --host "0.0.0.0" \
        --port 25080 \
        --chain-graphql-url "$OBSERVABILITY_CHAIN_GRAPHQL_URL" \
        --catch-up-chain-ids "$OBSERVABILITY_CATCH_UP_CHAINS" \
        --catch-up-max-blocks-per-chain 100 \
        --swap-chain-id "$SWAP_CHAIN_ID" \
        --swap-application-id "$SWAP_APPLICATION_ID" \
        --database-host "$DATABASE_HOST" \
        --database-port "$DATABASE_PORT" \
        --database-user "$DATABASE_USER" \
        --database-password "$DATABASE_PASSWORD" \
        --database-name "$DATABASE_NAME" \
        --swap-host "$SWAP_HOST" \
        --proxy-host "$PROXY_HOST" \
        --proxy-chain-id "$PROXY_CHAIN_ID" \
        --proxy-application-id "$PROXY_APPLICATION_ID" > kline.log 2>&1 &
    kline_pid=$!
    ensure_background_process "$kline_pid" "kline" "$PWD/kline.log"
    wait_http_ready "kline" "http://localhost:25080/protocol/stats"
    cd $ROOT_DIR
}

function run_maker() {
    rm -rf $WALLET_DIR/maker/0
    mkdir -p $WALLET_DIR/maker/0

    create_wallet maker 0 1 > /dev/null
    owner=$(wallet_owner maker 0)
    chain=$(wallet_chain_id maker 0)

    MAKER_WALLET_OWNER=$owner
    MAKER_WALLET_CHAIN_ID=$chain
    export MAKER_WALLET_OWNER MAKER_WALLET_CHAIN_ID

    export PATH=$MAKER_BIN_DIR:$PATH
    run_named_service maker-wallet maker 0 40082

    sleep 10

    cd $ROOT_DIR/service/kline
    env $(no_external_proxy_env_args) WALLET_OWNER="$owner" WALLET_CHAIN="$chain" $PYTHON3 -u src/maker.py \
        --swap-chain-id "$SWAP_CHAIN_ID" \
        --swap-application-id "$SWAP_APPLICATION_ID" \
        --database-host "$DATABASE_HOST" \
        --database-port "$DATABASE_PORT" \
        --database-user "$DATABASE_USER" \
        --database-password "$DATABASE_PASSWORD" \
        --database-name "$DATABASE_NAME" \
        --wallet-host "localhost:40082" \
        --swap-host "$SWAP_HOST" \
        --proxy-host "$PROXY_HOST" \
        --proxy-chain-id "$PROXY_CHAIN_ID" \
        --proxy-application-id "$PROXY_APPLICATION_ID" > maker.log 2>&1 &
    maker_pid=$!
    ensure_background_process "$maker_pid" "maker" "$PWD/maker.log"

    env $(no_external_proxy_env_args) WALLET_OWNER="$owner" WALLET_CHAIN="$chain" $PYTHON3 -u src/maker_api.py \
        --host "0.0.0.0" \
        --port 25081 \
        --database-host "$DATABASE_HOST" \
        --database-port "$DATABASE_PORT" \
        --database-user "$DATABASE_USER" \
        --database-password "$DATABASE_PASSWORD" \
        --database-name "$DATABASE_NAME" \
        --wallet-url "http://localhost:40082" \
        --wallet-metrics-url "http://localhost:40084/metrics" \
        --wallet-memory-limit-bytes 0 > maker_api.log 2>&1 &
    maker_api_pid=$!
    ensure_background_process "$maker_api_pid" "maker_api" "$PWD/maker_api.log"
    wait_http_ready "maker_api" "http://localhost:25081/debug/health"
    cd $ROOT_DIR
}

function init_user_wallet() {
    rm -rf $WALLET_DIR/user/0
    mkdir -p $WALLET_DIR/user/0

    create_wallet user 0 1 > /dev/null

    USER_WALLET_OWNER=$(wallet_owner user 0)
    USER_WALLET_CHAIN_ID=$(wallet_chain_id user 0)

    export USER_WALLET_OWNER
    export USER_WALLET_CHAIN_ID
}

function run_user_wallet() {
    init_user_wallet

    export PATH=$MAKER_BIN_DIR:$PATH
    run_named_service user-wallet user 0 "$USER_WALLET_PORT"

    wait_http_ready "user-wallet" "http://localhost:${USER_WALLET_PORT}"
}

function run_funder() {
    owner=$(wallet_owner maker 0)
    chain=$(wallet_chain_id maker 0)

    cd $ROOT_DIR/service/kline
    env $(no_external_proxy_env_args) WALLET_OWNER="$owner" WALLET_CHAIN="$chain" $PYTHON3 -u src/funder.py \
        --swap-chain-id "$SWAP_CHAIN_ID" \
        --swap-application-id "$SWAP_APPLICATION_ID" \
        --wallet-host "localhost:40082" \
        --swap-host "$SWAP_HOST" \
        --proxy-host "$PROXY_HOST" \
        --proxy-chain-id "$PROXY_CHAIN_ID" \
        --proxy-application-id "$PROXY_APPLICATION_ID" \
        --maker-wallet-host "localhost:40082" \
        --maker-wallet-chain-id "$chain" > funder.log 2>&1 &
    funder_pid=$!
    ensure_background_process "$funder_pid" "funder" "$PWD/funder.log"
    cd $ROOT_DIR
}

function print_deployment_summary() {
    echo -e "\n\n========================================"
    echo -e "  DEPLOYMENT READY"
    echo -e "  All services are up; you can now send requests via the web UI."
    echo -e "========================================"
    echo -e "Chain and Application IDs:"
    echo -e "  BLOB_GATEWAY_CHAIN_ID=$BLOB_GATEWAY_CHAIN_ID"
    echo -e "  BLOB_GATEWAY_APPLICATION_ID=$BLOB_GATEWAY_APPLICATION_ID"
    if [ -n "${BLOB_GATEWAY_STATE_APPLICATION_ID:-}" ]; then
        echo -e "  BLOB_GATEWAY_STATE_APPLICATION_ID=$BLOB_GATEWAY_STATE_APPLICATION_ID"
    fi
    echo -e "  AMS_CHAIN_ID=$AMS_CHAIN_ID"
    echo -e "  AMS_APPLICATION_ID=$AMS_APPLICATION_ID"
    if [ -n "${AMS_STATE_APPLICATION_ID:-}" ]; then
        echo -e "  AMS_STATE_APPLICATION_ID=$AMS_STATE_APPLICATION_ID"
    fi
    echo -e "  PROXY_CHAIN_ID=$PROXY_CHAIN_ID"
    echo -e "  PROXY_APPLICATION_ID=$PROXY_APPLICATION_ID"
    if [ -n "${PROXY_STATE_APPLICATION_ID:-}" ]; then
        echo -e "  PROXY_STATE_APPLICATION_ID=$PROXY_STATE_APPLICATION_ID"
    fi
    echo -e "  SWAP_CHAIN_ID=$SWAP_CHAIN_ID"
    echo -e "  SWAP_APPLICATION_ID=$SWAP_APPLICATION_ID"
    if [ -n "${MEME_MODULE_ID:-}" ]; then
        echo -e "  MEME_MODULE_ID=$MEME_MODULE_ID"
        echo -e "  MEME_STATE_MODULE_ID=$MEME_STATE_MODULE_ID"
    fi
    if [ -n "${MAKER_WALLET_CHAIN_ID:-}" ]; then
        echo -e "  MAKER_WALLET_CHAIN_ID=$MAKER_WALLET_CHAIN_ID"
        echo -e "  MAKER_WALLET_OWNER=$MAKER_WALLET_OWNER"
    fi
    if [ -n "${USER_WALLET_CHAIN_ID:-}" ]; then
        echo -e "  USER_WALLET_CHAIN_ID=$USER_WALLET_CHAIN_ID"
        echo -e "  USER_WALLET_OWNER=$USER_WALLET_OWNER"
    fi
    echo -e "----------------------------------------"
    echo -e "Service URLs:"
    echo -e "  http://${SUB_DOMAIN}blobgateway.com/api/blobs/query/chains/$BLOB_GATEWAY_CHAIN_ID/applications/$BLOB_GATEWAY_APPLICATION_ID"
    echo -e "  http://${SUB_DOMAIN}ams.respeer.ai/api/ams/query/chains/$AMS_CHAIN_ID/applications/$AMS_APPLICATION_ID"
    echo -e "  http://${SUB_DOMAIN}linerameme.fun/api/proxy/query/chains/$PROXY_CHAIN_ID/applications/$PROXY_APPLICATION_ID"
    echo -e "  http://${SUB_DOMAIN}lineraswap.fun/api/swap/query/chains/$SWAP_CHAIN_ID/applications/$SWAP_APPLICATION_ID"
    echo -e "========================================\n"
}

run_kline
run_user_wallet

if [ "x$RUN_MAKER" = "x1" ]; then
    run_maker
    run_funder
fi

print_deployment_summary

if [ -t 0 ]; then
    read
else
    while true; do
        sleep 300
    done
fi

kill -9 `ps -ef | grep $SWAP_APPLICATION_ID | awk '{print $2}'` > /dev/null 2>&1
