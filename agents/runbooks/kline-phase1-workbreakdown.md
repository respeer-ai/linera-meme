# Kline Phase 1 Work Breakdown

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Canonical executable task breakdown for phase 1 of the kline rebuild.

## Facts

- This file decomposes `agents/runbooks/kline-phase1-plan.md` into concrete work packages
- Live status still belongs only in `agents/tasks/board.yaml`
- Work packages are ordered to preserve external API safety while building the new architecture

## Rules

- Do not start handler cutover before the corresponding read model exists
- Do not start projection cutover before the required storage and ingestion foundations exist
- Do not migrate lower-priority debug surfaces ahead of priority-1 product endpoints
- Do not treat package-skeleton work as done until dependency boundaries are enforceable in code review

## Work Packages

### `PKG-1` Skeleton

- Goal:
  - create phase-1 package structure and bootstrap boundaries
- Outputs:
  - `app/`
  - `integration/`
  - `storage/mysql/`
  - `ingestion/`
  - `projection/`
  - `query/`
  - `compatibility/`
- Acceptance:
  - new code can land into target packages without using legacy flat layout

### `PKG-2` Layer 1 Schema

- Goal:
  - implement `POS-031`
- Outputs:
  - raw schema migrations
  - operational schema migrations
  - rollout scripts or migration ordering
- Acceptance:
  - Layer 1 DDL is implementation-ready and migratable

### `PKG-3` Layer 1 Ingestion

- Goal:
  - implement `POS-032`
- Outputs:
  - block ingestion coordinator
  - cursor advancement
  - anomaly persistence
- Acceptance:
  - one chain can be replayed idempotently into Layer 1

### `PKG-4` Trade Projection

- Goal:
  - create settled trade projection backbone for transactions and candles
- Depends on:
  - `PKG-2`
  - `PKG-3`
  - later `POS-033` and `POS-034` outputs
- Outputs:
  - trade projection storage
  - trade read model support
- Acceptance:
  - transactions and candles can be sourced from stable trade projection

### `PKG-5` Position Projection

- Goal:
  - create position and pool-state read foundations for `/positions`
- Depends on:
  - `PKG-2`
  - `PKG-3`
  - later `POS-034` and `POS-035` outputs
- Outputs:
  - position basis projection
  - pool state projection
  - positions read model
- Acceptance:
  - `/positions` no longer needs raw-history replay in handler code

### `PKG-6` Priority-1 Handler Cutover

- Goal:
  - move priority-1 endpoints to thin handlers over new read models
- Endpoints:
  - `/points/...`
  - `/points/.../information`
  - `/transactions/...`
  - `/transactions/information`
  - `/positions`
- Outputs:
  - handler modules
  - serializer modules
  - compatibility adapters
- Acceptance:
  - priority-1 endpoints preserve public contract and stop relying on legacy correctness logic

### `PKG-7` Parity And Safety

- Goal:
  - add parity checking and rollback-safe cutover guards
- Outputs:
  - shadow comparison paths
  - diagnostics for migrated endpoints
  - rollback instructions
- Acceptance:
  - migrated endpoints can be validated against legacy outputs before full legacy removal

## Suggested Task Mapping

- `PKG-1`
  - package skeleton
  - bootstrap split
- `PKG-2`
  - `POS-031`
- `PKG-3`
  - `POS-032`
- `PKG-4`
  - parts of `POS-033` to `POS-035`
  - transactions/candles read model work
- `PKG-5`
  - parts of `POS-034` to `POS-035`
  - positions read model work
- `PKG-6`
  - first query cutover tasks
- `PKG-7`
  - parity checks and compatibility hardening

## Validation

- each phase-1 work package has a distinct deliverable
- each priority-1 endpoint maps to a work package
- no package combines schema, ingestion, projection, and handler cutover into one uncontrolled task

## Sources

- `agents/runbooks/kline-phase1-plan.md`
- `agents/primitives/kline-package-layout.md`
- `agents/primitives/kline-api-read-models.md`
- `agents/runbooks/observability-deliverables.md`
