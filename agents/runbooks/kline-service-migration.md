# Kline Service Migration

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Canonical migration path from the current monolithic `service/kline` package to the target modular kline service architecture.

## Facts

- This runbook covers the whole kline service package
- Observability migration is one workstream inside this runbook
- Public API compatibility remains the primary external constraint
- Internal storage and module layout may be replaced entirely

## Rules

- Do not refactor the package around observability alone and forget positions, stats, diagnostics, or debug surfaces
- Do not let temporary debug helpers define long-term core boundaries
- Do not keep correctness-critical business logic inside API handlers once projections exist
- Do not mix migration sequencing with live task status; status remains in `agents/tasks/board.yaml`

## Current Responsibilities To Rehome

- chain-derived transactions history
- candle generation and kline queries
- positions list and position metrics
- pool metadata and pool stats
- protocol stats and fee summaries
- diagnostics and history gap inspection
- maker or wallet or pool debug exports currently exposed through kline-adjacent paths

## Target Service Slices

### Slice 1: Raw Ingestion

- destination:
  - `ingestion`
- inputs:
  - chain RPC or subscriptions
- outputs:
  - Layer 1 raw facts
  - ingestion cursors
  - anomalies

### Slice 2: Event Normalization

- destination:
  - `registry`
  - `normalizer`
- outputs:
  - decode results
  - normalized domain events

### Slice 3: Projections

- destination:
  - `projection`
- outputs:
  - settled trades
  - candle buckets
  - pool state
  - position basis
  - fee state
  - stats inputs

### Slice 4: Query API

- destination:
  - `query`
- outputs:
  - API responses matching current contracts

### Slice 5: Diagnostics

- destination:
  - `diagnostics`
- outputs:
  - lag reports
  - anomaly exports
  - decode failure inspection
  - parity and stall debug views

## Migration Order

1. Define target module map and ownership boundaries
2. Build observability ingestion and projection pipeline
3. Materialize read models for transactions, candles, positions, pool state, and fees
4. Move API handlers to read only those models
5. Move diagnostics and debug endpoints to dedicated diagnostic models
6. Remove monolithic correctness logic from legacy handler paths

## Query Compatibility Rules

- `/points`, `/kline`, `/transactions`, `/positions`, `/position-metrics`, stats endpoints, and useful debug endpoints must keep stable external contracts unless explicitly revised
- Internal call graph may change completely
- Stable API compatibility does not imply stable internal tables or helper functions

## Validation

- Every existing externally used endpoint is mapped to one target module and one target read model
- No correctness-critical endpoint depends on raw-history replay inside handler code after migration
- Diagnostics endpoints remain available through dedicated models
- Monolith removal does not reduce operational visibility

## Sources

- `agents/context/kline-service-architecture.md`
- `agents/context/current-capabilities.md`
- `agents/context/observability-architecture.md`
- `agents/runbooks/observability-migration.md`
- `agents/runbooks/observability-product-mapping.md`
