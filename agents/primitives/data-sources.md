# Data Source Semantics

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Canonical truth hierarchy and off-chain data-source rules.

## Facts

- Affected Modules:
  - `service/kline/`
  - `webui-v2/`
  - `pool/`
- Read Before:
  - debugging chart discrepancies
  - deciding whether a bug is upstream or frontend
  - reasoning about `service/kline` correctness
- Chain contracts are protocol truth
- Recorded contract transaction history is the source for derived off-chain views
- `service/kline` is an off-chain aggregation layer built from recorded chain activity
- Frontend should consume APIs and wallet state, not invent protocol state
- Missing pool transactions must be debugged upstream before blaming `service/kline` or frontend
- `service/kline` reflects settled trades, not planned trades
- Kline shape can be distorted by delayed settlement, missing transaction persistence, or stale overwrite bugs
- Positions accuracy depends on liquidity transactions landing in the recorded history with correct actor identity
- Candle storage uses milliseconds
- Candle key is `(pool_id, token_reversed, interval, bucket_start_ms)`
- Replaying a trade with `transaction_id <= last_trade_id` for the bucket must be a no-op
- Candle bucket assignment uses contract transaction time from parsed chain facts, not parser wall-clock time
- Candle `is_final=true` means the bucket is complete relative to parsed chain facts
- Candle finality must be derived from a projection watermark, not local wall-clock time
- Pool market watermark is the maximum known event time for a pool market from:
  - latest `settled_trades.trade_time_ms` for the pool application
  - latest parsed `raw_blocks.timestamp_ms` for the pool chain
- If no newer parsed trade or block exists, the pool market watermark does not advance
- Empty finalized candles may only be generated up to the pool market watermark
- Realtime candle-finalized events may only be emitted when the pool market watermark crosses a bucket boundary

## Checklist

- For chart discrepancies across clients, compare:
  - backend `/points` responses
  - local cache merge behavior
  - live update overwrite behavior
  - upstream transaction completeness
