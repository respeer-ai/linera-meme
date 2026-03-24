#!/bin/bash

####
## E.g. ./build_miner.sh
####

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..
MINER_DIR=$ROOT_DIR/service/miner

OUTPUT_DIR=$ROOT_DIR/output/compose/miner

mkdir -p $OUTPUT_DIR/miner

cp $SCRIPT_DIR/Dockerfile.miner $SCRIPT_DIR/miner-entrypoint.sh $OUTPUT_DIR
cp $MINER_DIR/build.rs $MINER_DIR/Cargo.lock $MINER_DIR/Cargo.toml $MINER_DIR/README.md $MINER_DIR/rust-toolchain.toml $MINER_DIR/src $OUTPUT_DIR/miner -rf

docker rmi linera-meme-miner npool/linera-meme-miner

cd $ROOT_DIR

GIT_COMMIT=$(git rev-parse --short HEAD)

cd $OUTPUT_DIR
docker build --build-arg git_commit="$GIT_COMMIT" --build-arg all_proxy=$all_proxy -f Dockerfile.miner . -t linera-meme-miner || exit 1

docker tag linera-meme-miner:latest docker.io/npool/linera-meme-miner:latest
docker push npool/linera-meme-miner:latest
