# Observability Implementation

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Execution order for implementing the explorer-style observability system that becomes the truth source for `service/kline`.

## Facts

- Live task status remains in `agents/tasks/board.yaml`
- This runbook defines implementation order and stop conditions only
- Canonical architecture is `agents/context/observability-architecture.md`
- Canonical storage model is `agents/primitives/observability-storage.md`
- Canonical market-data semantics is `agents/primitives/market-data-semantics.md`

## Flow

1. Finalize Layer 1 raw schema and cursor rules
2. Implement Layer 1 ingestion and replay
3. Validate Layer 1 on selected production-like chains
4. Add application registry and decoder registry
5. Implement Layer 2 normalized event generation
6. Define `settled_trade` and `settled_liquidity_change`
7. Implement Layer 3 derived tables
8. Re-point `transactions`, `candles`, `positions`, and diagnostics to Layer 3
9. Degrade or remove `latestTransactions` as a truth source

## Checklist

### Phase 1

1. Define raw tables and unique keys
2. Define `chain_cursors`
3. Define replay and conflict rules
4. Confirm `round` is excluded from primary identity and cursor logic

### Phase 2

1. Implement block-by-block raw ingestion
2. Make writes block-atomic
3. Make replay idempotent
4. Add diagnostics for cursor lag and ingestion anomalies

### Phase 3

1. Define `application_registry`
2. Define `decoder_registry`
3. Implement decode success and decode failure outputs
4. Preserve undecodable payloads as raw facts

### Phase 4

1. Define normalized event schemas
2. Define correlation keys
3. Define `settled_trade`
4. Define `settled_liquidity_change`

### Phase 5

1. Materialize derived product tables
2. Switch Kline to `settled_trade`
3. Switch positions and fees to finalized Layer 3 events
4. Keep diagnostics queryable across Layers 1, 2, and 3

## Validation

- Layer 1 replay leaves storage unchanged on duplicate ingestion
- `Reject` remains visible as a normal raw fact
- Decode failures do not block raw ingestion
- Candles change only from `settled_trade`
- Transactions view can be explained from Layer 3 back to Layer 1

## Stop Conditions

- Raw ingestion is replay-safe
- Normalized events are generated for target app types
- Kline no longer depends on `latestTransactions`
- Product views can be explained end-to-end from chain facts

## Sources

- `agents/context/observability-architecture.md`
- `agents/primitives/observability-storage.md`
- `agents/primitives/market-data-semantics.md`
- `agents/tasks/board.yaml` (`POS-026`)
