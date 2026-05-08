FROM rust:1.86 AS rust-decoder-builder

ARG all_proxy

WORKDIR /workspace

COPY Cargo.toml ./
COPY Cargo.lock ./
COPY abi ./abi
COPY ams ./ams
COPY base ./base
COPY blob-gateway ./blob-gateway
COPY meme ./meme
COPY pool ./pool
COPY proxy ./proxy
COPY runtime ./runtime
COPY swap ./swap
COPY service/decoder ./service/decoder

RUN CARGO_NET_GIT_FETCH_WITH_CLI=true all_proxy=${all_proxy} cargo build --release -p decoder --bin canonical_decoder -j 1

FROM python:3.10

ARG swap_application_id
ARG wallet_host
ARG wallet_owner
ARG wallet_chain
ARG swap_host
ARG all_proxy

ENV SWAP_APPLICATION_ID=${swap_application_id}
ENV SWAP_HOST=${swap_host}
ENV WALLET_HOST=${wallet_host}
ENV WALLET_OWNER=${wallet_owner}
ENV WALLET_CHAIN=${wallet_chain}
ENV KLINE_RUST_DECODER_BIN=/usr/local/bin/kline-canonical-decoder

COPY --from=rust-decoder-builder /workspace/target/release/canonical_decoder /usr/local/bin/kline-canonical-decoder

COPY service/kline kline

WORKDIR kline

RUN all_proxy= pip3 install pysocks
RUN all_proxy=${all_proxy} pip3 install uvicorn[standard]
RUN all_proxy=${all_proxy} pip3 install --upgrade pip
RUN all_proxy=${all_proxy} pip3 install -r requirements.txt
RUN all_proxy=${all_proxy} pip3 install -e .

COPY --chmod=755 \
  docker/kline-entrypoint.sh \
  docker/maker-entrypoint.sh \
  ./
