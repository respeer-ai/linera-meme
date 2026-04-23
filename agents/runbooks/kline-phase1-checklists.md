# Kline Phase 1 Checklists

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Canonical implementation checklists for `POS-036` through `POS-041`.

## Facts

- This file turns phase-1 work packages into per-task execution checklists
- Live status remains only in `agents/tasks/board.yaml`
- These checklists are implementation-facing, not architecture-facing

## Rules

- Do not mark a task complete unless all required checklist items are satisfied or an explicit blocker is recorded
- Do not skip compatibility checks for migrated endpoints
- Do not let a handler-cutover task finish while still depending on legacy correctness logic
- Do not merge unrelated checklist items across tasks just because they touch the same files

## `POS-036` Checklist

- Create target package directories required by phase 1:
  - `app/`
  - `integration/`
  - `storage/mysql/`
  - `ingestion/`
  - `projection/`
  - `query/handlers/`
  - `query/read_models/`
  - `query/serializers/`
  - `compatibility/`
- Add minimal bootstrap entrypoints in the new package layout
- Add placeholder module boundaries or interfaces where needed
- Ensure new code paths can import through new package areas without touching legacy flat modules
- Ensure no new business logic lands in legacy monolithic helpers after the skeleton exists

## `POS-037` Checklist

- Define projection-backed storage contract for:
  - trades
  - candles
- Implement `query.read_models.transactions`
- Implement `query.read_models.candles`
- Ensure read models consume projection-backed state, not handler-time replay
- Ensure read models support current filter dimensions used by:
  - `/transactions/...`
  - `/transactions/information`
  - `/points/...`
  - `/points/.../information`
- Add serializer inputs needed by priority-1 endpoints
- Add targeted tests for read-model query behavior

## `POS-038` Checklist

- Define projection-backed storage contract for:
  - position basis
  - pool state needed by `/positions`
- Implement `query.read_models.positions`
- Ensure `/positions` fields remain derivable without handler-time history replay
- Preserve current owner/status filtering semantics
- Preserve current response fields required by frontend
- Add targeted tests for:
  - owner filtering
  - status filtering
  - stable ordering

## `POS-039` Checklist

- Implement `query.handlers.kline`
- Implement `query.handlers.transactions`
- Implement `query.serializers.kline`
- Implement `query.serializers.transactions`
- Add compatibility adapters for legacy response shape where needed
- Switch `/points/...` and `/points/.../information` to the new handler/read-model path
- Switch `/transactions/...` and `/transactions/information` to the new handler/read-model path
- Remove handler-owned correctness logic from migrated endpoints
- Ensure migrated endpoints do not fetch remote data directly
- Add targeted endpoint tests for migrated handlers

## `POS-040` Checklist

- Implement `query.handlers.positions`
- Implement `query.serializers.positions`
- Switch `/positions` to the new handler/read-model path
- Preserve current response envelope and field names
- Remove legacy correctness-critical aggregation from the `/positions` handler path
- Add targeted endpoint tests for:
  - valid owner
  - status filtering
  - invalid status handling

## `POS-041` Checklist

- Add parity comparison path for migrated endpoints
- Add diagnostics or shadow-compare output for mismatches
- Define rollback switch or rollback procedure for migrated handlers
- Ensure legacy fallback remains callable for non-migrated endpoints
- Add operator-visible signal when new and legacy outputs diverge
- Document cutover safety conditions before removing legacy code

## Validation

- Every migrated endpoint has:
  - one read model
  - one handler
  - one serializer path
  - compatibility coverage if needed
- Every phase-1 task has explicit acceptance evidence
- No migrated endpoint still depends on `latestTransactions` as correctness source

## Sources

- `agents/runbooks/kline-phase1-plan.md`
- `agents/runbooks/kline-phase1-workbreakdown.md`
- `agents/primitives/kline-package-layout.md`
- `agents/primitives/kline-api-read-models.md`
