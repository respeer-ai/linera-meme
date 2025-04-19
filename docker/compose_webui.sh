#!/bin/bash

####
## E.g. ./compose_webui.sh -C 0 -z testnet-babbage
####

options="C:z:"

while getopts $options opt; do
  case ${opt} in
    C) COMPILE=${OPTARG} ;;
    z) CLUSTER=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

OUTPUT_DIR="${SCRIPT_DIR}/../output/compose"
mkdir -p $OUTPUT_DIR

CONFIG_DIR=$OUTPUT_DIR/config
mkdir -p $CONFIG_DIR

WEBUI_DIR=$SCRIPT_DIR/../webui

# Cleanup before building
docker stop linera-meme-webui
docker rm linera-meme-webui
docker rmi linera-meme-webui

NGINX_TEMPLATE_FILE=${SCRIPT_DIR}/../configuration/template/nginx.conf.j2

cd "$WEBUI_DIR"
if [ "x$COMPILE" = "x1" ]; then
  yarn
  yarn build:wasm
fi

yarn build
docker build --no-cache -f Dockerfile -t linera-meme-webui . || exit 1

cd $SCRIPT_DIR
# Compose up webui
docker compose -f docker-compose-webui.yml up --wait


function generate_nginx_conf() {
  port_base=$1
  endpoint=$2
  domain=$3

  echo "{
      \"service\": {
      \"endpoint\": \"$endpoint\",
      \"servers\": [\"localhost:$port_base\"],
      \"domain\": \"$domain\",
      \"sub_domain\": \"$SUB_DOMAIN\",
      \"api_endpoint\": \"$endpoint\"
    }
  }" > ${CONFIG_DIR}/$endpoint.nginx.json

  jinja -d ${CONFIG_DIR}/$endpoint.nginx.json $NGINX_TEMPLATE_FILE > ${CONFIG_DIR}/$endpoint.nginx.conf
  cp -v ${CONFIG_DIR}/$endpoint.nginx.conf /etc/nginx/sites-enabled/
}

SUB_DOMAIN=$(echo "webui.${CLUSTER}." | sed 's/\.\./\./g')
generate_nginx_conf 18080 linera-meme-webui linerameme.fun

sudo nginx -s reload
