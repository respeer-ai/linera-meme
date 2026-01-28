#!/bin/bash

####
## E.g. ./build_miner.sh
####

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..
MINER_DIR=$ROOT_DIR/service/miner

cd $MINER_DIR

cargo build --release

cd $ROOT_DIR

docker rmi linera-meme-miner npool/linera-meme-miner

GIT_COMMIT=$(git rev-parse --short HEAD)
docker build --build-arg git_commit="$GIT_COMMIT" -f docker/Dockerfile.miner . -t linera-meme-miner || exit 1

docker tag linera-meme-miner:latest docker.io/npool/linera-meme-miner:latest
docker push npool/linera-meme-miner:latest
