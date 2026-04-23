# Kline Phase 1 Plan

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Canonical first implementation phase for rebuilding `service/kline` under the new architecture while preserving current API behavior.

## Facts

- Phase 1 is not the whole migration
- Phase 1 should create the new architectural skeleton and move the highest-risk correctness paths first
- Observability and read-model foundations are phase-1 concerns
- Full maker or funder separation may continue after phase 1

## Rules

- Do not try to migrate every endpoint in the first code change
- Do not move low-value debug surfaces ahead of correctness-critical data paths
- Do not keep adding features to the legacy monolith while phase-1 replacement modules exist
- Do not remove legacy paths until their phase-1 replacements have parity checks

## Phase 1 Goals

1. Create the new package skeleton under `service/kline/src/`
2. Establish Layer 1 ingestion and cursor foundations
3. Establish projection-backed read models for the most correctness-critical product surfaces
4. Move the first query handlers onto thin handler/read-model/serializer boundaries
5. Isolate compatibility shape-preservation in explicit modules

## Phase 1 New Modules

### Must Exist In Phase 1

- `app/bootstrap.py`
- `app/config.py`
- `integration/chain_client.py`
- `storage/mysql/connection.py`
- `storage/mysql/raw_repo.py`
- `storage/mysql/projection_repo.py`
- `ingestion/coordinator.py`
- `ingestion/cursors.py`
- `ingestion/anomalies.py`
- `projection/trades/`
- `projection/candles/`
- `projection/positions/`
- `projection/pools/`
- `query/handlers/kline.py`
- `query/handlers/transactions.py`
- `query/handlers/positions.py`
- `query/serializers/kline.py`
- `query/serializers/transactions.py`
- `query/serializers/positions.py`
- `query/read_models/candles.py`
- `query/read_models/transactions.py`
- `query/read_models/positions.py`
- `compatibility/legacy_response_shapes.py`

### May Stay Legacy In Phase 1

- maker wallet debug aggregation
- stall diagnosis APIs
- protocol stats refinements
- pool stats refinements
- websocket event refactor if it blocks core correctness migration

## Phase 1 Endpoint Priority

### Priority 1

- `/points/...`
- `/points/.../information`
- `/transactions/...`
- `/transactions/information`
- `/positions`

Reason:
- these are product-critical
- these depend on replacing `latestTransactions` correctness assumptions

### Priority 2

- `/position-metrics`
- `/ticker/interval/{interval}`
- `/poolstats/interval/{interval}`
- `/protocol/stats`

Reason:
- important, but should build on the first projection-backed foundations

### Priority 3

- `/diagnostics`
- `/transactions/audit/*`
- `/debug/pool`
- `/debug/traces`
- maker/wallet debug endpoints

Reason:
- operationally valuable
- lower priority than getting core product queries onto stable models

## Phase 1 Legacy Retention

### Keep Behind `compatibility`

- existing response envelopes
- legacy field names
- any temporary route aliases
- temporary adapter glue where new read models must still emit old JSON shapes

### Keep Temporarily In Legacy Modules

- non-critical debug aggregation that has no clean target model yet
- maker-specific operator surfaces not on the critical path for product correctness

### Remove From Legacy Immediately When Replaced

- handler-owned correctness logic for priority-1 endpoints
- direct dependence on `latestTransactions` for priority-1 data paths
- ad hoc transaction replay inside priority-1 handlers

## Phase 1 Validation

### Structural

- new package directories exist
- new handlers do not import legacy monolith helpers directly except through explicit bridge modules
- compatibility code is isolated

### Correctness

- priority-1 endpoints have projection-backed read models
- handler logic for priority-1 endpoints is thin
- `latestTransactions` is no longer the correctness source for priority-1 endpoints

### Safety

- public API shapes remain unchanged for migrated endpoints
- legacy fallback remains available for non-migrated endpoints
- diagnostics exist for parity checking between legacy and new paths

## Handoff To Phase 2

- phase 2 should migrate:
  - `position-metrics`
  - stats endpoints
  - websocket publishing
  - diagnostics endpoint families
  - remaining maker/operator diagnostics

## Sources

- `agents/context/kline-service-architecture.md`
- `agents/runbooks/kline-service-migration.md`
- `agents/runbooks/kline-capability-mapping.md`
- `agents/primitives/kline-package-layout.md`
- `agents/primitives/kline-api-read-models.md`
