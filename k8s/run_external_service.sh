#!/bin/bash

####
## export AMS_EXTERNAL_HOST=api.ams.external.respeer.ai
## export AMS_HOST=api.ams.respeer.ai
## ./run_external_service.sh
####

[ "x" == "x$AMS_EXTERNAL_HOST" ] && AMS_EXTERNAL_HOST=api.ams.external.respeer.ai
[ "x" == "x$AMS_HOST" ] && AMS_HOST=api.ams.respeer.ai
[ "x" == "x$BLOB_EXTERNAL_HOST" ] && BLOB_EXTERNAL_HOST=api.external.blobgateway.com
[ "x" == "x$BLOB_HOST" ] && BLOB_HOST=api.blobgateway.com
[ "x" == "x$FAUCET_EXTERNAL_HOST" ] && FAUCET_EXTERNAL_HOST=api.faucet.external.respeer.ai
[ "x" == "x$FAUCET_HOST" ] && FAUCET_HOST=api.faucet.respeer.ai
[ "x" == "x$KLINE_EXTERNAL_HOST" ] && KLINE_EXTERNAL_HOST=api.kline.external.lineraswap.fun
[ "x" == "x$KLINE_HOST" ] && KLINE_HOST=api.kline.lineraswap.fun
[ "x" == "x$PROXY_EXTERNAL_HOST" ] && PROXY_EXTERNAL_HOST=api.external.linerameme.fun
[ "x" == "x$PROXY_HOST" ] && PROXY_HOST=api.linerameme.fun
[ "x" == "x$SWAP_EXTERNAL_HOST" ] && SWAP_EXTERNAL_HOST=api.external.lineraswap.fun
[ "x" == "x$SWAP_HOST" ] && SWAP_HOST=api.lineraswap.fun

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
TEMPLATE_FILE="${SCRIPT_DIR}/../configuration/template/external-ingress.conf.j2"

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../output/k8s"
mkdir -p $OUTPUT_DIR

# All generated config files will be put here
CONFIG_DIR="${OUTPUT_DIR}/config"
mkdir -p $CONFIG_DIR

function generate_external_ingress() {
    endpoint=$1 
    host=$2
    external_host=$3
    domain=`echo $host | sed 's/\./-/g'`
    echo "{
        \"service\": {
            \"name\": \"$endpoint\",
            \"external_name\": \"$external_host\",
            \"host\": \"$host\",
            \"domain\": \"$domain\"
        }
    }" > ${CONFIG_DIR}/$endpoint.external.ingress.json

    jinja -d ${CONFIG_DIR}/$endpoint.external.ingress.json $TEMPLATE_FILE > ${CONFIG_DIR}/$endpoint-external-ingress.yaml
    kubectl apply -f ${CONFIG_DIR}/$endpoint-external-ingress.yaml
}

generate_external_ingress ams $AMS_HOST $AMS_EXTERNAL_HOST
generate_external_ingress blob $BLOB_HOST $BLOB_EXTERNAL_HOST
generate_external_ingress faucet $FAUCET_HOST $FAUCET_EXTERNAL_HOST
generate_external_ingress kline $KLINE_HOST $KLINE_EXTERNAL_HOST
generate_external_ingress proxy $PROXY_HOST $PROXY_EXTERNAL_HOST
generate_external_ingress swap $SWAP_HOST $SWAP_EXTERNAL_HOST
