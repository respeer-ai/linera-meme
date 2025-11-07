#!/bin/bash

####
## E.g. ./compose_webui.sh -C 0 -z testnet-conway
####

options="z:"
COMPILE=1

while getopts $options opt; do
  case ${opt} in
    C) COMPILE=${OPTARG} ;;
  esac
done

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

WEBUI_DIR=$SCRIPT_DIR/../webui

# Cleanup before building
docker stop linera-meme-webui
docker rm linera-meme-webui
docker rmi linera-meme-webui npool/linera-meme-webui

cd "$WEBUI_DIR"
if [ "x$COMPILE" = "x1" ]; then
  yarn
  yarn build:wasm
fi

yarn build
docker build --no-cache -f Dockerfile -t linera-meme-webui . || exit 1

docker tag linera-meme-webui:latest docker.io/npool/linera-meme-webui:latest
docker push npool/linera-meme-webui:latest
