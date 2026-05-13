# Kline Service Rules

Type: Rules
Audience: Coding assistants
Authority: High

## Purpose

Local rules for `service/kline/` code, tests, and bug investigation.

## Facts

- Scope:
  - applies to `service/kline/`
- Primary Files:
  - `src/db.py`
  - `src/ticker.py`
  - `src/subscription.py`
  - `src/kline.py`
  - `src/request_trace.py`
  - `tests/db_test.py`
  - `tests/positions_api_test.py`
  - `tests/subscription_test.py`
- Role:
  - off-chain aggregation for transactions, klines, ticker, websocket push, positions
- Not Truth:
  - `service/kline` is not protocol truth
  - if contract transaction history is missing upstream, this service cannot reconstruct it faithfully

## Rules

- Do not patch chart or positions symptoms here before ruling out upstream contract or transaction-history issues
- Treat `transactions` rows as derived persisted inputs, not as authoritative protocol state
- When changing positions logic, verify consistency with `AddLiquidity`, `RemoveLiquidity`, `from_account`, and `liquidity` semantics
- When changing kline logic, preserve millisecond timestamp semantics
- When changing candle logic, preserve bucket key semantics:
  - `(pool_id, token_reversed, interval, bucket_start_ms)`
- When changing websocket logic, consider stale overwrite and cross-client consistency risks
- When changing API behavior, update tests in `tests/`
- Prefer narrow DB and API tests over broad manual validation
- For newly created or actively refactored Python modules in this package, keep each file at or below 1000 lines
- For newly created or actively refactored Python modules in this package, define only one top-level object per file
- Prefer object-oriented organization for new code; extract behavior out of legacy large files instead of adding new helper clusters there

## Checklist

- Root cause isolated as upstream-truth issue or local aggregation issue
- DB/API tests updated for changed behavior
- Kline point semantics preserved
- Positions semantics preserved
