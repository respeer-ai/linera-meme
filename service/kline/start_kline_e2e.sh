#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
ROOT_DIR="$SCRIPT_DIR/../.."
KLINE_DIR="$SCRIPT_DIR"
VENV_DIR="$HOME/.linera-meme-service-venv"
PYTHON3="$VENV_DIR/bin/python3"
SERVICE_LOG="$KLINE_DIR/kline_e2e_service.log"

export KLINE_RUST_DECODER_BIN="$ROOT_DIR/target/release/canonical_decoder"

cd "$KLINE_DIR"

echo "Starting kline service..."
echo "Log: $SERVICE_LOG"

# All 3 chains from swap-creator wallet
CATCH_UP_CHAINS="8fd4233c5d03554f87d47a711cf70619727ca3d148353446cab81fb56922c9b7,f67850ab83749f4be91b1dd6eb5a416e483da846d584346093928a53b1fdf66d,7331fe10533ba670f0d015bc17bd6b83c35750bc290059b8421575f4a7466b75"

# Clear proxy for local connections
all_proxy= http_proxy= https_proxy= ALL_PROXY= HTTP_PROXY= HTTPS_PROXY= \
  nohup $PYTHON3 -u src/kline.py \
    --host "0.0.0.0" \
    --port 25080 \
    --chain-graphql-url "http://localhost:22080/" \
    --chain-graphql-ws-url "" \
    --catch-up-chain-ids "$CATCH_UP_CHAINS" \
    --catch-up-max-blocks-per-chain 100 \
    --disable-catch-up-on-startup \
    --database-host "localhost" \
    --database-port "3306" \
    --database-name "linera_swap_kline_test" \
    --database-user "root" \
    --database-password "12345679" \
    --swap-host "localhost:22080" \
    --swap-chain-id "f67850ab83749f4be91b1dd6eb5a416e483da846d584346093928a53b1fdf66d" \
    --swap-application-id "f3d2abcd1cfc836bf83e1be3a9d6e2d95b243a71cbb7702cf22c42d125eae301" \
  > "$SERVICE_LOG" 2>&1 &

KLINE_PID=$!
echo "$KLINE_PID" > /tmp/kline_e2e_pid.txt
echo "PID: $KLINE_PID"

# Wait for service to become ready (up to 30 seconds)
echo "Waiting for service to start..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:25080/debug/observability > /dev/null 2>&1; then
        echo "Service ready after ${i}s"
        exit 0
    fi
    if ! kill -0 $KLINE_PID 2>/dev/null; then
        echo "Service died during startup"
        tail -30 "$SERVICE_LOG"
        exit 1
    fi
    sleep 1
done
echo "Service not ready after 30s"
tail -30 "$SERVICE_LOG"
exit 1
