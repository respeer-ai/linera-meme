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

## Checklist

- For chart discrepancies across clients, compare:
  - backend `/points` responses
  - local cache merge behavior
  - live update overwrite behavior
  - upstream transaction completeness
