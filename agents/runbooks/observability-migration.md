# Observability Migration

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Migration sequence for moving existing `service/kline` product tables and queries from `latestTransactions`-based ingestion to the layered observability system.

## Facts

- Existing product-facing tables remain valid outputs if their upstream source changes
- Layer 1, Layer 2, and Layer 3 must be introduced without corrupting current product semantics
- Kline semantics must remain standard exchange semantics throughout migration
- Live task status remains in `agents/tasks/board.yaml`

## Flow

1. Add Layer 1 tables without changing existing product writes
2. Populate Layer 1 from replay and live ingestion
3. Add Layer 2 normalized-event outputs without changing product reads
4. Add Layer 3 settled outputs in parallel with existing product tables
5. Shadow-compare Layer 3 outputs against current product tables
6. Switch product-facing writes and reads to Layer 3
7. Remove `latestTransactions` from truth-source paths

## Rules

- Do not switch Kline reads before `settled_trade` parity is proven
- Do not delete existing product tables during the first migration pass
- Do not let Layer 3 write directly into raw tables
- Do not mix old and new candle inputs in the same aggregation path
- Do not claim migration complete while `latestTransactions` still participates in correctness decisions

## Checklist

### Phase A: Parallel Introduction

1. Introduce Layer 1 schema
2. Introduce Layer 2 event tables
3. Introduce Layer 3 settled tables
4. Keep current product tables untouched

### Phase B: Shadow Population

1. Backfill Layer 1 from selected historical ranges
2. Generate Layer 2 normalized events from Layer 1
3. Generate Layer 3 settled outputs from Layer 2
4. Materialize shadow product outputs if needed:
   - `transactions_v2`
   - `candles_v2`
   - `positions_v2`
   - `fees_v2`

### Phase C: Parity Verification

1. Compare old and new transactions views
2. Compare old and new candle outputs
3. Compare old and new positions and fee outputs
4. Investigate differences by tracing back to Layer 1 facts

### Phase D: Cutover

1. Switch product-facing derivation to Layer 3
2. Switch diagnostics to query Layer 1/2/3 explicitly
3. Remove `latestTransactions` from correctness-critical paths
4. Keep old code only as temporary fallback if explicitly needed

## Product Mapping

### Existing Tables Or Views To Preserve As Outputs

- `transactions`
  - new upstream: `settled_trade` and any other explicitly finalized Layer 3 outputs
- `candles`
  - new upstream: `settled_trade`
- `positions`
  - new upstream: `settled_liquidity_change` plus finalized fee/redeemable derivations
- `pool`
  - new upstream: Layer 3 liquidity and market-state derivations
- `fees`
  - new upstream: finalized Layer 3 derivations

### New Tables To Introduce

- Layer 1:
  - `chain_cursors`
  - `raw_blocks`
  - `raw_incoming_bundles`
  - `raw_posted_messages`
  - `raw_operations`
  - `raw_outgoing_messages`
  - `raw_events`
  - `raw_oracle_responses`
- Layer 2:
  - normalized event tables or equivalent materialized storage
- Layer 3:
  - `settled_trade`
  - `settled_liquidity_change`
  - optionally shadow outputs before product cutover

## Validation

- Product views remain explainable from Layer 3 back to Layer 1 during shadow mode
- Candle parity checks use only settled trades
- Transactions parity checks do not silently treat rejects as settled history
- Positions and fee outputs do not depend on re-reading raw bytes after cutover

## Stop Conditions

- Product-facing paths no longer use `latestTransactions` as a truth source
- Layer 3 outputs are authoritative for `transactions`, `candles`, `positions`, and `fees`
- Differences between old and new outputs are either zero or explicitly explained

## Sources

- `agents/context/observability-architecture.md`
- `agents/primitives/derived-market-state.md`
- `agents/runbooks/observability-implementation.md`
- `agents/tasks/board.yaml` (`POS-031`, `POS-032`, `POS-033`, `POS-034`, `POS-035`)
