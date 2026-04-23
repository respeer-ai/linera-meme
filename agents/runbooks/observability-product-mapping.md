# Observability Product Mapping

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Canonical mapping from existing `service/kline` product tables and query contracts to Layer 3 settled outputs.

## Facts

- Current physical tables in `service/kline/src/db.py` include:
  - `pools`
  - `transactions`
  - `candles`
- `positions` and `fees` are currently query-level derived outputs, not base storage tables
- Layer 3 may keep current product table names if their upstream source changes
- Compatibility is about preserving product contract shape, not preserving old ingestion logic
- The broader service may be rebuilt with new module and storage boundaries as long as current product APIs remain stable

## Rules

- Do not preserve old write paths if they still depend on `latestTransactions`
- Do not preserve the current `service/kline` internal package layout just because it exists today
- Do not force Layer 3 table names to match current names before parity is proven
- Do not let field names imply semantics stronger than the Layer 3 source actually provides
- Do not keep `positions` dependent on full raw transaction replay once Layer 3 is authoritative
- Do not keep protocol-wide `fees` derived from naive `volume * 0.003` after Layer 3 fee derivation exists

## Current Product Surface

### `pools`

- Current columns:
  - `pool_id`
  - `pool_application`
  - `token_0`
  - `token_1`
- Current meaning:
  - pool identity and token pair metadata

### `transactions`

- Current columns:
  - `pool_application`
  - `pool_id`
  - `transaction_id`
  - `transaction_type`
  - `from_account`
  - `amount_0_in`
  - `amount_0_out`
  - `amount_1_in`
  - `amount_1_out`
  - `liquidity`
  - `price`
  - `volume`
  - `quote_volume`
  - `direction`
  - `token_reversed`
  - `created_at`
- Current meaning:
  - mixed trade and liquidity history used by multiple query paths

### `candles`

- Current columns:
  - `pool_application`
  - `pool_id`
  - `token_reversed`
  - `interval_name`
  - `bucket_start_ms`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
  - `quote_volume`
  - `trade_count`
  - `first_trade_id`
  - `last_trade_id`
  - `first_trade_at_ms`
  - `last_trade_at_ms`
- Current meaning:
  - pre-aggregated candle buckets keyed by pool, direction, interval, and start time

### `positions`

- Current meaning:
  - query-time aggregation over transaction history plus pool state

### `fees`

- Current meaning:
  - protocol and position fee outputs derived from off-chain logic

## Layer 3 Mapping

### `pools`

- New upstream:
  - Layer 3 pool metadata and liquidity-state projection
- Required preserved fields:
  - `pool_id`
  - `pool_application`
  - `token_0`
  - `token_1`
- New derived fields expected later:
  - reserve snapshots
  - total supply snapshots
  - last settled trade time
  - last settled liquidity change time
- Compatibility rule:
  - `pools` may remain a physical table, but writes must come from Layer 3 projections or controlled metadata sync

### `transactions`

- New upstream:
  - `settled_trade`
  - optionally separate settled business projections for non-trade history if UI still needs them
- Field mapping:
  - `pool_application` <- `settled_trade.pool_application_id`
  - `pool_id` <- resolved pool metadata
  - `transaction_id` <- Layer 3 stable sequence inside one pool projection
  - `transaction_type` <- settled business type such as `Swap`
  - `from_account` <- settled actor identity if product contract still needs actor display
  - `amount_0_in/out`, `amount_1_in/out` <- settled trade amounts
  - `liquidity` <- null for pure trade rows unless explicit settled non-trade projections continue to use this table
  - `price` <- settled trade price
  - `volume` <- base-side trade volume under current `token_reversed`
  - `quote_volume` <- quote-side trade volume
  - `direction` <- Layer 3 side projection for current token ordering
  - `token_reversed` <- retained compatibility dimension
  - `created_at` <- `settled_trade.trade_time_ms`
- Compatibility rule:
  - if non-trade rows remain needed, they must come from explicit Layer 3 settled projections, not from raw history leakage

### `candles`

- New upstream:
  - `settled_trade`
- Field mapping:
  - `pool_application` <- `settled_trade.pool_application_id`
  - `pool_id` <- resolved pool metadata
  - `token_reversed` <- projection dimension
  - `interval_name` <- derivation bucket interval
  - `bucket_start_ms` <- canonical bucket start
  - `open/high/low/close` <- aggregation of settled trade price
  - `volume` <- aggregated base volume
  - `quote_volume` <- aggregated quote volume
  - `trade_count` <- count of settled trades in bucket
  - `first_trade_id` <- first Layer 3 trade sequence in bucket
  - `last_trade_id` <- last Layer 3 trade sequence in bucket
  - `first_trade_at_ms` <- first settled trade time in bucket
  - `last_trade_at_ms` <- last settled trade time in bucket
- Compatibility rule:
  - current candle key shape may remain unchanged
  - bucket mutation must be driven only by new settled trades

### `positions`

- New upstream:
  - `settled_liquidity_change`
  - Layer 3 fee and redeemable projections
- Mapping rule:
  - current API shape may remain
  - query implementation must stop scanning raw `transactions` as source of truth
  - per-owner position state should come from Layer 3 position basis plus current settled pool state
- Required explainability:
  - every displayed position delta must map to one or more `settled_liquidity_change` rows

### `fees`

- New upstream:
  - Layer 3 fee accrual and redeemable projections
- Mapping rule:
  - protocol-wide fees must come from settled trade and liquidity state, not `volume * 0.003`
  - position fees must come from Layer 3 position/accounting projections

## Migration Shapes

### Shadow Tables

- Recommended first pass:
  - `transactions_v2`
  - `candles_v2`
  - `position_state_v2`
  - `fee_state_v2`
  - optional `pool_state_v2`

### Final Cutover

- Allowed:
  - rename shadow tables into current names
  - switch readers to Layer 3-backed views
  - keep old table names with new writers
- Preferred:
  - preserve public query contract while replacing internals

## Query Compatibility

- `get_kline_information`:
  - must read from Layer 3-backed `transactions` or equivalent settled trade projection
- `get_kline` and `get_last_kline`:
  - must read Layer 3-backed `candles`
  - transaction fallback may remain only as a Layer 3 settled-trade fallback, not as raw-history fallback
- `get_positions`:
  - must read Layer 3 position projections
- protocol stats and pool stats:
  - must read Layer 3 pool and trade projections

## Validation

- Existing public response shapes remain stable during cutover
- A product row can be traced:
  - output row -> Layer 3 row(s) -> Layer 2 correlation key(s) -> Layer 1 raw fact(s)
- `transactions` no longer contains rows sourced only from `latestTransactions`
- `candles` no longer aggregates any non-settled input
- `positions` no longer requires raw history replay as correctness path

## Sources

- `service/kline/src/db.py`
- `agents/primitives/derived-market-state.md`
- `agents/primitives/observability-interfaces.md`
- `agents/runbooks/observability-migration.md`
