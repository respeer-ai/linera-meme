FROM python:3.10

ARG swap_application_id
ARG wallet_host
ARG wallet_owner
ARG wallet_chain
ARG swap_host

ENV SWAP_APPLICATION_ID=${swap_application_id}
ENV SWAP_HOST=${swap_host}
ENV WALLET_HOST=${wallet_host}
ENV WALLET_OWNER=${wallet_owner}
ENV WALLET_CHAIN=${wallet_chain}

COPY docker/kline kline

WORKDIR kline

RUN pip3 install uvicorn[standard]
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN pip3 install -e .

COPY --chmod=755 \
  docker/kline-entrypoint.sh \
  docker/maker-entrypoint.sh \
  ./
