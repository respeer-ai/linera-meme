# Kline Capability Mapping

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Canonical mapping from current `service/kline` capabilities to the target modular kline service architecture.

## Facts

- This file covers current HTTP endpoints, websocket endpoints, background jobs, and debug/operator surfaces
- The goal is to preserve capability coverage while allowing internal rebuild
- Current implementation sources include:
  - `service/kline/src/kline.py`
  - `service/kline/src/maker_api.py`
  - `service/kline/src/ticker.py`
  - `service/kline/src/position_metrics.py`
  - `service/kline/src/trader.py`
  - `service/kline/src/maker.py`
  - `service/kline/src/funder.py`

## Rules

- Do not drop a current capability just because it is awkwardly implemented today
- Do not keep a capability in the `query` module if it is fundamentally diagnostics or operator support
- Do not keep a capability in API handlers if it belongs in a projection or background worker
- Do not assume maker-side APIs belong in the same deployable forever; map them by responsibility first

## Mapping

### Public Query Endpoints

- `/points/...`
  - current role:
    - kline/candle query
  - target module:
    - `query`
  - target read model:
    - candle read model from `projection`
- `/points/.../information`
  - current role:
    - kline range metadata
  - target module:
    - `query`
  - target read model:
    - candle coverage metadata
- `/transactions/...`
  - current role:
    - trade/history query
  - target module:
    - `query`
  - target read model:
    - transactions read model from settled trade projection
- `/transactions/information`
  - current role:
    - transaction range metadata
  - target module:
    - `query`
  - target read model:
    - transactions coverage metadata
- `/positions`
  - current role:
    - owner positions list
  - target module:
    - `query`
  - target read model:
    - position state projection
- `/position-metrics`
  - current role:
    - enriched position metrics and blockers
  - target module:
    - `query`
  - target read model:
    - position basis plus fee/redeemable projection
  - migration rule:
    - stop doing correctness-critical full history replay inside request path
- `/ticker/interval/{interval}`
  - current role:
    - market summary/ticker stats
  - target module:
    - `query`
  - target read model:
    - ticker stats projection
- `/poolstats/interval/{interval}`
  - current role:
    - per-pool summary stats
  - target module:
    - `query`
  - target read model:
    - pool stats projection
- `/protocol/stats`
  - current role:
    - protocol-wide summary stats
  - target module:
    - `query`
  - target read model:
    - protocol stats projection

### Diagnostics Endpoints

- `/transactions/audit/recent`
  - current role:
    - recent live-vs-db comparison for one pool
  - target module:
    - `diagnostics`
  - target read model:
    - recent parity audit model
- `/transactions/audit/replay`
  - current role:
    - replay inspection for pool history
  - target module:
    - `diagnostics`
  - target read model:
    - projection replay inspector
- `/diagnostics`
  - current role:
    - diagnostic event export
  - target module:
    - `diagnostics`
  - target read model:
    - diagnostic event store
- `/debug/traces`
  - current role:
    - request or mutation trace export
  - target module:
    - `diagnostics`
  - target read model:
    - debug trace store
- `/debug/pool`
  - current role:
    - one-pool transaction, gap, liquidity, and diagnostic export
  - target module:
    - `diagnostics`
  - target read model:
    - pool debug bundle model

### Realtime Endpoint

- `/ws`
  - current role:
    - websocket push for frontend updates
  - target module:
    - `query`
  - backing source:
    - projection-driven event stream
  - migration rule:
    - websocket payloads should be emitted from stable read-model changes, not ad hoc ticker loops

### Background Jobs

- `Ticker.run` loop
  - current role:
    - fetch pools
    - fetch transactions
    - backfill recent history
    - repair historical gaps
    - persist transactions and candles
    - push websocket updates
  - target modules:
    - `integration` for remote fetch
    - `ingestion` for chain or source ingestion
    - `projection` for transactions/candles materialization
    - `query` only for websocket fan-out
  - migration rule:
    - split this monolith; do not keep one class owning fetch, persist, audit, repair, and push

- startup/shutdown lifecycle in `kline.py`
  - current role:
    - boot db
    - boot swap client
    - spawn ticker task
  - target modules:
    - service bootstrap only
  - migration rule:
    - bootstrap should wire modules, not host business logic

### Maker And Operator Endpoints

- `/events/...`
  - current role:
    - maker event history
  - target module:
    - `diagnostics`
  - target read model:
    - maker event store
- `/debug/wallets`
  - current role:
    - wallet fleet summary
  - target module:
    - `diagnostics`
  - target integration:
    - wallet RPC and metrics adapters
- `/debug/wallets/{index}/metrics`
  - target module:
    - `diagnostics`
- `/debug/wallets/{index}/balances`
  - target module:
    - `diagnostics`
- `/debug/wallets/{index}/block`
  - target module:
    - `diagnostics`
- `/debug/wallets/{index}/pending-messages`
  - target module:
    - `diagnostics`
- `/debug/pools/stall`
  - current role:
    - correlate maker events, wallet traces, and pool DB progress
  - target module:
    - `diagnostics`
  - target read model:
    - stall diagnosis model
- `/debug/health`
  - current role:
    - operator health summary
  - target module:
    - `diagnostics`

### Non-HTTP Capabilities

- `position_metrics.py`
  - current role:
    - correctness logic and blocker derivation for live position metrics
  - target modules:
    - `projection` for exactness-critical accounting
    - `diagnostics` for blocker explanations
    - `query` only for serialization
- `trader.py`
  - current role:
    - maker trading strategy and execution loop
  - target module:
    - not core kline query path
  - target placement:
    - maker subsystem or separate operator service
- `maker.py`
  - current role:
    - maker process entrypoint
  - target placement:
    - separate maker/operator service boundary
- `funder.py`
  - current role:
    - gas/top-up operational loop
  - target placement:
    - separate funding/operator service boundary

## Coverage Checklist

1. Every current HTTP endpoint is assigned to `query` or `diagnostics`
2. Every current background loop is assigned to `ingestion`, `projection`, `integration`, or an external operator service
3. No maker/funder/trader loop is left implicitly inside the new query-service core
4. Current websocket behavior is mapped to projection-driven event publishing

## Sources

- `service/kline/src/kline.py`
- `service/kline/src/maker_api.py`
- `service/kline/src/ticker.py`
- `service/kline/src/position_metrics.py`
- `service/kline/src/trader.py`
- `service/kline/src/maker.py`
- `service/kline/src/funder.py`
- `agents/context/kline-service-architecture.md`
- `agents/runbooks/kline-service-migration.md`
