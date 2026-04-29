# Kline Phase 1 Rollout

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Canonical operator-facing rollout and rollback procedure for `POS-041`.

## Facts

- Scope:
  - migrated priority-1 endpoints only
  - `/points/...`
  - `/points/.../information`
  - `/transactions/...`
  - `/transactions/information`
  - `/positions`
- Current rollout controls:
  - `KLINE_PRIORITY1_ROLLOUT_MODE=legacy|new`
  - `KLINE_PRIORITY1_PARITY=0|1`
- Current operator status surface:
  - `GET /debug/priority1-rollout`
- Current persisted mismatch source:
  - `diagnostics.source=phase1_parity`
  - `diagnostics.event_type=priority1_mismatch`

## Rules

- Do not switch migrated endpoints to `new` mode in production without parity enabled first
- Do not remove the legacy path until rollout status stays clean for a sustained observation window
- Do not treat fallback and rollback as implementation detail; they are part of the public operational contract of phase 1
- Do not add endpoint-specific ad hoc rollback logic; use the shared rollout controls

## Rollout States

### `legacy`

- Meaning:
  - migrated handlers still call the legacy path for response production
- Use when:
  - bootstrapping parity in a new environment
  - active mismatch investigation is ongoing

### `new`

- Meaning:
  - migrated handlers return the new read-model path
- Use when:
  - parity is enabled
  - mismatch rate is acceptable or zero for the target window

## Rollout Procedure

1. Enable parity:
   - set `KLINE_PRIORITY1_PARITY=1`
   - keep `KLINE_PRIORITY1_ROLLOUT_MODE=legacy`
2. Observe:
   - query `GET /debug/priority1-rollout`
   - inspect recent mismatch payloads in `recent_mismatches`
3. Switch serving mode:
   - set `KLINE_PRIORITY1_ROLLOUT_MODE=new`
   - keep parity enabled
4. Continue observation:
   - verify `recent_mismatch_count` remains acceptable
   - inspect mismatch payloads before changing code or removing legacy fallback

## Rollback Procedure

1. Set `KLINE_PRIORITY1_ROLLOUT_MODE=legacy`
2. Keep `KLINE_PRIORITY1_PARITY=1`
3. Confirm:
   - `GET /debug/priority1-rollout` reports `legacy_mode_enabled=true`
4. Investigate:
   - use `recent_mismatches`
   - inspect `GET /diagnostics?source=phase1_parity`
5. Resume `new` mode only after the mismatch cause is explicit

## Acceptance

- Operators have one shared endpoint for rollout visibility
- Rollback uses one shared environment switch
- Mismatch evidence remains queryable after rollback
- No priority-1 endpoint needs a bespoke rollback path

## Sources

- `agents/runbooks/kline-phase1-workbreakdown.md`
- `agents/runbooks/kline-phase1-checklists.md`
- `agents/context/kline-service-architecture.md`
