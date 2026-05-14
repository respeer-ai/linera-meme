# System Map

Type: Context
Audience: Coding assistants
Authority: High

## Purpose

Canonical high-level module map and runtime shape for the repository.

## Facts

- Module map:
  - `meme/`: token contract, mining, approvals, redemption, liquidity funding support
  - `pool/`: liquidity pool contract, add/remove liquidity, swaps, reserves, LP accounting, and pool-side protocol facts
  - `swap/`: router, pool registry, pool creation, pool metadata updates
  - `proxy/`: governance, miner management, meme creation orchestration
  - `ams/`: application indexing and discovery support
  - `service/kline/`: off-chain aggregation for transactions, klines, positions
  - `service/miner/`: mining worker
  - `webui-v2/`: primary frontend

- Frontend talks to product APIs and wallet integrations
- `proxy` orchestrates meme creation and governance flows
- `swap` owns pool registry and receives pool updates
- `pool` executes per-market swap and liquidity flows
- `meme` owns token and mining state
- `service/kline` ingests parsed chain facts and derives charts, transactions, tickers, positions, stats, and diagnostics
- Query and mutation traffic are logically separated
- Shared query routing is the intended normal read path
- Local compose should mirror k8s read/write separation semantics
- `service/kline` depends on parsed chain facts and derived projections, not on speculative frontend state or live pool-history queries

## Implications

- pool add/remove liquidity is asynchronous and message-driven
- meme-native liquidity flow has a native-funding branch that deserves extra scrutiny
- `latestTransactions` or equivalent pool-local history queues must not be product truth
