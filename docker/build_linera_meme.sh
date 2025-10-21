#!/bin/bash

####
## E.g. ./build_linera_meme.sh
####

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..

cd $ROOT_DIR

docker rmi linera-meme

GIT_COMMIT=$(git rev-parse --short HEAD)
docker build --build-arg git_commit="$GIT_COMMIT" -f docker/Dockerfile.meme . -t linera-meme || exit 1

