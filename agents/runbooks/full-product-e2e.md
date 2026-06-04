# Full Product E2E

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Run the complete local product E2E for `linera-meme` using the repository bootstrap path.

## Facts

- Environment bootstrap is driven by `scripts/run_local.sh`.
- Product workflow validation is driven by `scripts/product_workflow_e2e.py`.
- Use the official faucet unless the user explicitly asks for another faucet.
- `run_local.sh` is a foreground long-running process; run product E2E from another shell/session.
- `run_local.sh` writes runtime chain/application constants to `webui-v2/src/constant/domain.ts`.
- Product workflow covers meme/native and meme/meme pool paths. It creates meme tokens, discovers pools, creates the meme/meme pool, executes swap, add liquidity, remove liquidity, claim-producing add-liquidity excess/failure paths, claim settlement, and observability checks.

## Rules

- Do not shorten required waits or skip message-processing delays to make the E2E finish faster.
- Do not use legacy `webui/` for current product validation.
- Do not treat kline/observability as protocol truth; use it as product read validation.
- Do not report E2E complete unless `scripts/product_workflow_e2e.py` prints `[product-e2e] completed`.
- If strict claim is disabled, report that claim capability was checked but claimable production was not required.
- If a command fails because of sandbox or network restrictions, rerun with approval instead of changing the workflow.

## Flow

1. Start local environment from the repository root:

   ```bash
   ./scripts/run_local.sh -C 0 -z testnet-conway
   ```

2. Wait until the script has created applications, updated `webui-v2/src/constant/domain.ts`, and started services.

3. In a separate shell/session, extract constants:

   ```bash
   PROXY_CHAIN_ID=$(sed -n "s/^export const PROXY_CHAIN_ID = '\\(.*\\)'/\\1/p" webui-v2/src/constant/domain.ts)
   PROXY_APPLICATION_ID=$(sed -n "s/^export const PROXY_APPLICATION_ID = '\\(.*\\)'/\\1/p" webui-v2/src/constant/domain.ts)
   SWAP_CHAIN_ID=$(sed -n "s/^export const SWAP_CHAIN_ID = '\\(.*\\)'/\\1/p" webui-v2/src/constant/domain.ts)
   SWAP_APPLICATION_ID=$(sed -n "s/^export const SWAP_APPLICATION_ID = '\\(.*\\)'/\\1/p" webui-v2/src/constant/domain.ts)
   AMS_APPLICATION_ID=$(sed -n "s/^export const AMS_APPLICATION_ID = '\\(.*\\)'/\\1/p" webui-v2/src/constant/domain.ts)
   BLOB_GATEWAY_APPLICATION_ID=$(sed -n "s/^export const BLOB_GATEWAY_APPLICATION_ID = '\\(.*\\)'/\\1/p" webui-v2/src/constant/domain.ts)
   ```

4. Run product workflow:

   ```bash
   python3 scripts/product_workflow_e2e.py \
     --proxy-chain-id "$PROXY_CHAIN_ID" \
     --proxy-application-id "$PROXY_APPLICATION_ID" \
     --swap-chain-id "$SWAP_CHAIN_ID" \
     --swap-application-id "$SWAP_APPLICATION_ID" \
     --ams-application-id "$AMS_APPLICATION_ID" \
     --blob-gateway-application-id "$BLOB_GATEWAY_APPLICATION_ID"
   ```

5. Add `--strict-claim` only when the current implementation and selected path are expected to produce `claimable > 0`.

## Readiness

- User wallet: `http://localhost:40092`
- Proxy wallet/API: `http://localhost:23080`
- Swap wallet/API: `http://localhost:22080`
- Query service: `http://localhost:24080`
- Kline: `http://localhost:25080/protocol/stats`

## Failure Triage

- Bootstrap failure: inspect `output/local/logs/run_local_debug.log`.
- Wallet/API readiness failure: inspect `proxy_*.log`, `swap_*.log`, `query-service_24080.log`, or `user-wallet_*.log`.
- Product workflow mutation/query failure: inspect `scripts/product_workflow_e2e.py` stdout and wallet service logs.
- Observability failure: inspect `service/kline/kline.log`, MySQL availability, and query-service import/readiness.
- Funds workflow failure: identify the exact operation/message and record:
  - operation chain
  - message origin chain
  - message target chain
  - application caller
  - message signer
  - pool creator chain
  - token creator chain

## Validation

Report complete only when:

- `scripts/run_local.sh` boots successfully and remains alive.
- `scripts/product_workflow_e2e.py` prints `[product-e2e] completed`.
- The run includes meme/native and meme/meme pool paths with create meme, create meme/meme pool, swap, add liquidity, remove liquidity, claim-producing paths, claim settlement, and observability checks.
- Any disabled strict-claim behavior is stated.

