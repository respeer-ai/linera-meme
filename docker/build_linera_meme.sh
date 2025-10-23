#!/bin/bash

####
## E.g. ./build_linera_meme.sh
####

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..

cd $ROOT_DIR

cargo build --release --target wasm32-unknown-unknown

docker rmi linera-meme npool/linera-meme

GIT_COMMIT=$(git rev-parse --short HEAD)
docker build --build-arg git_commit="$GIT_COMMIT" -f docker/Dockerfile.meme . -t linera-meme || exit 1

docker tag linera-meme:latest docker.io/npool/linera-meme:latest
docker push npool/linera-meme:latest
