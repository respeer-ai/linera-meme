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
- `from_account` is intended to represent the actor identity
- Liquidity funds can appear to move without a corresponding `AddLiquidity` transaction landing in pool history if the async flow breaks before `NewTransaction`

## Implications

- Missing positions or wrong positions should first be traced to transaction persistence and actor identity, not to frontend rendering
- Kline issues may come from upstream settlement or persistence problems even when the chart symptom is client-visible
