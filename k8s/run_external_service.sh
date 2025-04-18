#!/bin/bash

####
## ./run_external_service.sh -p api.linera-respeer-devnet
####

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
TEMPLATE_FILE="${SCRIPT_DIR}/../configuration/template/external-ingress.conf.j2"

DOMAIN_PREFIX=api

options="p:"

while getopts $options opt; do
  case ${opt} in
    p) DOMAIN_PREFIX=${OPTARG} ;;
  esac
done

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../output/k8s"
mkdir -p $OUTPUT_DIR

# All generated config files will be put here
CONFIG_DIR="${OUTPUT_DIR}/config"
mkdir -p $CONFIG_DIR

function generate_external_ingress() {
    endpoint=$1 
    host=$DOMAIN_PREFIX.$2
    external_host=$DOMAIN_PREFIX.external.$2
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

generate_external_ingress ams ams.respeer.ai
generate_external_ingress blob blobgateway.com
generate_external_ingress kline kline.lineraswap.fun
generate_external_ingress proxy linerameme.fun
generate_external_ingress swap lineraswap.fun
