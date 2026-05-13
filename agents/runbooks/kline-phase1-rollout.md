# Kline Phase 1 Cutover State

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Canonical status note for `POS-041` after the phase-1 priority-1 cutover moved to a single-path architecture.

## Facts

- Scope:
  - migrated priority-1 endpoints only
  - `/points/...`
  - `/points/.../information`
  - `/transactions/...`
  - `/transactions/information`
  - `/positions`
- Current architecture state:
  - migrated priority-1 endpoints are single-path
  - response-shape compatibility is now a conceptual boundary, not necessarily a dedicated runtime module
  - runtime rollout switches, parity toggles, and rollback surfaces described in older docs are obsolete

## Rules

- Do not reintroduce legacy/new runtime mode switches for already migrated priority-1 endpoints
- Do not reintroduce parity-only runtime paths for already migrated priority-1 endpoints
- Do not treat compatibility adapters as permission to resurrect legacy correctness logic
- Do not add endpoint-specific ad hoc rollback logic to undo the single-path cutover

## Current State

- Priority-1 migrated endpoints should be treated as permanently cut over to the new read-model path.
- Safety now comes from targeted tests, projection contracts, and explicit assistant-facing docs, not from runtime dual-path execution.
- Any future correctness investigation should compare persisted inputs, projection outputs, and read-model behavior directly; it should not revive legacy-serving mode.

## Acceptance

- Documentation no longer instructs obsolete rollout-mode or parity controls
- Priority-1 cutover state is described in a way that matches the codebase
- Compatibility remains limited to external response shape preservation

## Sources

- `agents/runbooks/kline-phase1-workbreakdown.md`
- `agents/runbooks/kline-phase1-checklists.md`
- `agents/context/kline-service-architecture.md`
