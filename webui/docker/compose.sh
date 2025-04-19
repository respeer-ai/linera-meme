#!/bin/bash

####
## E.g. ./compose.sh -C 0 -z testnet-babbage
## This script must be run without proxy
####

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
TEMPLATE_FILE=${SCRIPT_DIR}/../../configuration/template/nginx.conf.j2
ROOT_DIR=$SCRIPT_DIR/..
CONF_DIR=$ROOT_DIR/configuration/compose
CLUSTER=

options="C:z:"

while getopts $options opt; do
  case ${opt} in
    C) COMPILE=${OPTARG} ;;
    z) CLUSTER=${OPTARG} ;;
  esac
done

# All generated files will be put here
OUTPUT_DIR="${SCRIPT_DIR}/../../output/compose"
mkdir -p $OUTPUT_DIR

# Generate config
CONFIG_DIR="${OUTPUT_DIR}/config"
mkdir -p $CONFIG_DIR

docker stop meme-webui
docker rm meme-webui
docker rmi meme-webui


cd $ROOT_DIR

if [ "x$COMPILE" = "x1" ]; then
  yarn build:wasm
fi

yarn build
docker build -f Dockerfile -t meme-webui .

function generate_nginx_conf() {
    endpoint=meme-webui
    domain=linerameme.fun

    echo "{
        \"service\": {
            \"endpoint\": \"$endpoint\",
            \"servers\": [\"localhost:18080\"],
            \"domain\": \"$domain\",
            \"sub_domain\": \"$SUB_DOMAIN\",
            \"api_endpoint\": \"$endpoint\"
        }
    }" > ${CONFIG_DIR}/$endpoint.nginx.json

    jinja -d ${CONFIG_DIR}/$endpoint.nginx.json $TEMPLATE_FILE > ${CONFIG_DIR}/$endpoint.nginx.conf
    echo "cp ${CONFIG_DIR}/$endpoint.nginx.conf /etc/nginx/sites-enabled/"
}

SUB_DOMAIN=$(echo "webui.${CLUSTER}." | sed 's/\.\./\./g')
# Generate service nginx conf
generate_nginx_conf

# run compose
cd $SCRIPT_DIR
docker compose -f docker-compose.yml up --wait
