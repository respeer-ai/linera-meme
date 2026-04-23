# Observability Layer 1 Operations

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Canonical DDL-adjacent operational schema and write rules for Layer 1 ingestion.

## Facts

- `agents/primitives/observability-schema.md` defines the raw fact tables
- This file defines the supporting operational tables and transaction rules needed to implement `POS-031` and `POS-032`
- Layer 1 needs both:
  - chain progress state
  - anomaly visibility
- Layer 2 and Layer 3 processing cursors must not be mixed into `chain_cursors`

## Rules

- Do not use one generic cursor row for all layers
- Do not encode anomalies only in logs
- Do not advance any cursor after a failed block transaction
- Do not silently ignore uniqueness conflicts that imply different row content
- Do not store downstream decode or normalization state in Layer 1 raw tables

## Operational Tables

### `processing_cursors`

- Purpose:
  - generic cursor table for decode, normalize, and derive workers
- Required columns:
  - `cursor_name` `varchar(128)` not null
  - `cursor_scope` `varchar(64)` not null
  - `partition_key` `varchar(255)` not null
  - `last_sequence` `varchar(255)` null
  - `last_block_hash` `varchar(64)` null
  - `last_success_at` `datetime(6)` null
  - `last_attempt_at` `datetime(6)` null
  - `status` `varchar(32)` not null
  - `consecutive_failures` `int` not null default `0`
  - `last_error` `text` null
  - `updated_at` `datetime(6)` not null
- Primary key:
  - `(cursor_name, partition_key)`
- Recommended `cursor_scope` values:
  - `decode`
  - `normalize`
  - `derive`
- Notes:
  - `last_sequence` is an opaque per-processor checkpoint
  - Layer 1 ingestion itself still uses `chain_cursors`

### `ingestion_anomalies`

- Purpose:
  - persist structural conflicts and replay inconsistencies
- Required columns:
  - `anomaly_id` `bigint` not null auto_increment
  - `anomaly_type` `varchar(64)` not null
  - `severity` `varchar(16)` not null
  - `chain_id` `varchar(64)` null
  - `height` `bigint` null
  - `block_hash` `varchar(64)` null
  - `object_type` `varchar(64)` not null
  - `object_identity` `varchar(255)` not null
  - `expected_fingerprint` `varchar(128)` null
  - `observed_fingerprint` `varchar(128)` null
  - `details_json` `json` null
  - `first_seen_at` `datetime(6)` not null
  - `last_seen_at` `datetime(6)` not null
  - `occurrence_count` `int` not null default `1`
  - `status` `varchar(32)` not null
- Primary key:
  - `anomaly_id`
- Unique keys:
  - `uq_ingestion_anomaly_identity` on `(anomaly_type, object_type, object_identity)`
- Secondary indexes:
  - `idx_ingestion_anomalies_chain_height` on `(chain_id, height)`
  - `idx_ingestion_anomalies_status` on `(status, severity, last_seen_at desc)`
- Recommended `anomaly_type` values:
  - `block_hash_mismatch`
  - `raw_object_conflict`
  - `missing_parent_block`
  - `unexpected_gap`
  - `decode_input_missing`
- Recommended `status` values:
  - `open`
  - `acknowledged`
  - `resolved`

### `raw_block_ingest_runs`

- Purpose:
  - optional run-history table for debugging ingestion attempts
- Required columns:
  - `run_id` `bigint` not null auto_increment
  - `chain_id` `varchar(64)` not null
  - `height` `bigint` not null
  - `mode` `varchar(32)` not null
  - `status` `varchar(32)` not null
  - `block_hash` `varchar(64)` null
  - `started_at` `datetime(6)` not null
  - `finished_at` `datetime(6)` null
  - `error_text` `text` null
  - `summary_json` `json` null
- Primary key:
  - `run_id`
- Secondary indexes:
  - `idx_raw_block_ingest_runs_chain_height` on `(chain_id, height, started_at desc)`
  - `idx_raw_block_ingest_runs_status` on `(status, started_at desc)`
- Notes:
  - optional for first cut
  - useful for postmortem and lag debugging

## Block-Atomic Write Contract

### Required Transaction Order

1. lock or select `chain_cursors` row for target `chain_id`
2. validate requested `height` against cursor state
3. insert or verify `raw_blocks`
4. insert or verify `raw_incoming_bundles`
5. insert or verify `raw_posted_messages`
6. insert or verify `raw_operations`
7. insert or verify `raw_outgoing_messages`
8. insert or verify `raw_events`
9. insert or verify `raw_oracle_responses`
10. write any anomaly rows generated during validation
11. advance `chain_cursors`
12. commit

### Required Failure Behavior

- if any write after step 3 fails:
  - rollback the whole transaction
- if a uniqueness hit matches existing content:
  - treat as replay-safe no-op
- if a uniqueness hit conflicts with existing content:
  - write or upsert `ingestion_anomalies`
  - do not advance `chain_cursors`
  - fail the ingest attempt

## Content Fingerprints

- Purpose:
  - detect whether a uniqueness hit is a harmless replay or a conflicting duplicate
- Recommended first implementation:
  - deterministic hash over canonical serialized payload for each raw object
- Suggested storage:
  - keep fingerprint only in in-memory comparison at first, or
  - add nullable fingerprint columns later if conflict diagnostics need query speed
- Rule:
  - do not treat key collision alone as replay-safe without content comparison

## Cursor Semantics

### `chain_cursors`

- advances only on successful Layer 1 block commit
- one row per chain
- authoritative for next `height` fetch

### `processing_cursors`

- advances independently per downstream worker
- must be able to lag behind Layer 1 safely
- must support replay after decoder or normalization logic changes

## Validation

- conflicting `(chain_id, height)` with different block content creates an open anomaly
- replaying the same block updates no raw rows and creates no anomaly
- downstream workers can restart from `processing_cursors` without consulting chain RPC
- Layer 1 rollback leaves `chain_cursors` unchanged

## Sources

- `agents/primitives/observability-schema.md`
- `agents/primitives/observability-storage.md`
- `agents/primitives/observability-interfaces.md`
- `agents/runbooks/observability-deliverables.md`
