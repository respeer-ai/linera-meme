#!/bin/bash

####
## ./apply_ingress.sh -z testnet-babbage
####

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
TEMPLATE_FILE="${SCRIPT_DIR}/../configuration/template/ingress-route.yaml.j2"

CLUSTER=

options="z:"

while getopts $options opt; do
  case ${opt} in
    z) CLUSTER=${OPTARG} ;;
  esac
done

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../output/k8s"
mkdir -p $OUTPUT_DIR

# All generated config files will be put here
CONFIG_DIR="${OUTPUT_DIR}/config"
mkdir -p $CONFIG_DIR

function generate_ingress_route() {
    endpoint=$1
    domain=$(echo "api.${CLUSTER}.$2" | sed 's/\.\./\./g')
    target_host=$(echo "${CLUSTER}.target.$2" | sed 's/\.\./\./g')
    name=$(echo "${CLUSTER}.$2" | sed 's/\.\./\./g' | sed 's/\./-/g')
    echo "{
        \"ingress\": {
            \"name\": \"$name\",
            \"target_host\": \"$target_host\",
            \"domain\": \"$domain\"
        }
    }" > ${CONFIG_DIR}/$endpoint-ingress.json

    jinja -d ${CONFIG_DIR}/$endpoint-ingress.json $TEMPLATE_FILE > ${CONFIG_DIR}/$endpoint-ingress.yaml
    kubectl apply -f ${CONFIG_DIR}/$endpoint-ingress.yaml
}

generate_ingress_route ams ams.respeer.ai
generate_ingress_route blob blobgateway.com
generate_ingress_route kline kline.lineraswap.fun
generate_ingress_route proxy linerameme.fun
generate_ingress_route swap lineraswap.fun
