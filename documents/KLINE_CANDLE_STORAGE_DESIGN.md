# K-line Candle Storage Design

## Purpose

This document defines the pre-aggregated candle storage contract for the backend K-line service.

The goal is to stop rebuilding candles from raw `transactions` rows on every `/points` read and move toward incremental candle maintenance on ingest.

## Canonical Time Unit

All candle storage timestamps use `milliseconds`.

Rules:

- transaction ingest keeps using source `createdAt` in milliseconds,
- candle bucket boundaries are stored as `bucket_start_ms`,
- HTTP `/points` and WebSocket payload timestamps remain milliseconds,
- no mixed second/millisecond semantics are allowed in candle storage.

## Candle Key

Each candle row is uniquely identified by:

- `pool_id`
- `token_reversed`
- `interval`
- `bucket_start_ms`

This key defines one financial bucket for one pool direction and one interval.

## Proposed Table Shape

Suggested table name: `candles`

Suggested columns:

- `pool_id INT UNSIGNED`
- `token_reversed TINYINT`
- `interval VARCHAR(16)`
- `bucket_start_ms BIGINT UNSIGNED`
- `open DECIMAL(30, 18)`
- `high DECIMAL(30, 18)`
- `low DECIMAL(30, 18)`
- `close DECIMAL(30, 18)`
- `volume DECIMAL(30, 18)`
- `trade_count INT UNSIGNED`
- `first_trade_id INT UNSIGNED`
- `last_trade_id INT UNSIGNED`
- `first_trade_at_ms BIGINT UNSIGNED`
- `last_trade_at_ms BIGINT UNSIGNED`

Primary key:

- `(pool_id, token_reversed, interval, bucket_start_ms)`

Useful secondary read index:

- `(pool_id, token_reversed, interval, bucket_start_ms)`

In practice the primary key already serves the main `/points` read path.

## Bucket Alignment

Intervals map to bucket sizes:

- `1min` -> `60_000`
- `5min` -> `300_000`
- `10min` -> `600_000`
- `15min` -> `900_000`
- `1h` -> `3_600_000`
- `4h` -> `14_400_000`
- `1D` -> `86_400_000`
- `1W` -> `604_800_000`
- `1ME` -> `2_592_000_000`

Bucket start rule:

- `bucket_start_ms = created_at_ms // interval_ms * interval_ms`

## Update Semantics

For the first trade in a bucket:

- `open = high = low = close = trade.price`
- `volume = trade.volume`
- `trade_count = 1`
- `first_trade_id = last_trade_id = trade.transaction_id`
- `first_trade_at_ms = last_trade_at_ms = trade.created_at_ms`

For a later trade in the same bucket:

- `open` stays unchanged
- `high = max(high, trade.price)`
- `low = min(low, trade.price)`
- `close = trade.price`
- `volume += trade.volume`
- `trade_count += 1`
- `last_trade_id = trade.transaction_id`
- `last_trade_at_ms = trade.created_at_ms`

## Idempotency Contract

Current design contract for `KSO-18`:

- ingest is append-oriented per pool and direction,
- replaying a trade with `transaction_id <= last_trade_id` for the bucket must be a no-op,
- duplicate delivery must not change OHLCV,
- later trades in the same bucket are authoritative for `close`.

This keeps the ingest path simple and safe for retry/replay handling.

## Scope Boundary

This document only defines the candle storage contract.

Not included yet:

- backfill/migration from raw transactions into candles,
- switching `/points` reads to candle storage,
- strict closed-vs-forming candle semantics,
- pair-aware WebSocket narrowing.

Those belong to:

- `KSO-18`
- `KSO-19`
- `KSO-20`
- `KSO-23`
