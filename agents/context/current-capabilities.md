# Current Capabilities

Type: Context
Audience: Coding assistants
Authority: Medium

## Purpose

Snapshot of implemented capability and currently confirmed operational facts.

## Facts

- Positions tab and route exist in `webui-v2`
- The page supports `all`, `active`, and `closed`
- `service/kline` exposes a positions API backed by recorded liquidity transactions
- `service/kline` exposes `/position-metrics` through projection-backed snapshot/replay inputs; product runtime no longer depends on live pool GraphQL for business truth
- Current positions accuracy depends on `transactions` having correct `AddLiquidity` and `RemoveLiquidity` records with stable `from_account`
- Kline service persists transactions, pool metadata, and candle data concerns
- Candle storage design exists and uses millisecond timestamps and `(pool_id, token_reversed, interval, bucket_start_ms)` as the candle key
- Query correctness depends on settled transaction history reaching `service/kline`
- Startup and chart consistency work is still an ongoing area, especially around fetch ordering, live updates, and cross-device consistency
- k8s ingress shape already separates `/query` from mutation and compatibility paths
- local `docker/compose.sh` and `docker/restart.sh` are being aligned to the same read/write split
- local query service and maker wallet must not share wallets
- Missing positions were not caused by the 5000-entry transaction window alone
- `pool_application` identifies a pool, not the acting user
- Current projection consumers use `pool_application` as the stable pool identity
- Historical `pools(pool_id, pool_application, token_0, token_1)` still exists as a legacy identity bridge for some read paths
- Current parse-block `swap_pool_created_recorded` / `swap_user_pool_created_recorded` payloads expose `pool_application` and token pair, but not `pool_id`
- `from_account` is intended to represent the actor identity
- Liquidity funds can appear to move without a corresponding `AddLiquidity` transaction landing in pool history if the async flow breaks before `NewTransaction`
- For `POS-022`, exact `principal/fee` is supported when a position has no swap history after opening, regardless of `virtualInitialLiquidity`
- If swaps occurred after opening, current code supports one strict complete subset based on the user's latest liquidity-change event. There must be no later pool `AddLiquidity` or `RemoveLiquidity` after that event. If the latest change is `AddLiquidity`, there also must be no earlier swap before it. If the latest change is `RemoveLiquidity`, earlier swaps are allowed and the remaining LP after that remove becomes the new basis, so swap-after-remove residual positions are now covered. The service reconstructs current `total_supply`, reserves, and `k_last` from full pool transaction history under the current V2 fee-on semantics, then computes `principal_amount0/1` from a fee-free counterfactual swap path and attributes the remainder to `fee_amount0/1`
- If swaps occurred after opening outside that strict subset, current code reports blockers and does not provide approximate Uniswap V2 `fee_amount0/1` or `principal_amount0/1`

## Implications

- Missing positions or wrong positions should first be traced to transaction persistence and actor identity, not to frontend rendering
- Kline issues may come from upstream settlement or persistence problems even when the chart symptom is client-visible
- Do not reintroduce 24h-volume or TVL-based fee approximations in the frontend for positions
- Do not reintroduce projection pool-catalog writes from ticker or websocket paths; the remaining pool catalog gap is a producer-side projection design issue, not a reason to restore projection writeback
