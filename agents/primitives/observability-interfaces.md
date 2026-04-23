# Observability Interfaces

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Canonical module-interface contract for Layer 1 ingestion, Layer 2 decoding and normalization, and Layer 3 market derivation.

## Facts

- This file defines in-process or service-local interfaces, not external public APIs
- First implementation remains Python-led
- Decoder execution may call a Rust helper, but orchestration boundaries stay here
- Canonical storage and semantic rules remain in:
  - `agents/primitives/observability-storage.md`
  - `agents/primitives/application-decoding.md`
  - `agents/primitives/normalized-event-model.md`
  - `agents/primitives/derived-market-state.md`

## Rules

- Do not let downstream layers read chain RPC directly when Layer 1 already persists the same fact
- Do not pass raw bytes directly from Layer 1 into Layer 3
- Do not couple registry refresh with block ingestion success
- Do not require synchronous end-to-end completion across all layers for one block commit
- Do not hide replay mode from downstream processors; every processor must know whether it is running incremental or catch-up work

## Flow

```mermaid
flowchart LR
    A[Chain client] --> B[Block ingestor]
    B --> C[Layer 1 raw store]
    C --> D[Decode scheduler]
    D --> E[Application registry]
    D --> F[Decoder registry]
    E --> G[Decoded payload store]
    F --> G
    C --> H[Normalizer]
    G --> H
    H --> I[Layer 2 event store]
    I --> J[Market deriver]
    J --> K[Layer 3 settled store]
    K --> L[Existing product queries]
```

## Interfaces

### Block Ingestor

- Responsibilities:
  - fetch confirmed block by `chain_id + height`
  - persist all Layer 1 rows for that block
  - advance `chain_cursors` atomically
- Input contract:
  - `chain_id`
  - `height`
  - optional mode:
    - `live`
    - `catch_up`
    - `replay`
- Output contract:
  - `block_hash`
  - `chain_id`
  - `height`
  - `ingest_status`
  - `raw_write_summary`
  - `cursor_advanced`
- Failure contract:
  - if any Layer 1 child write fails, commit must not happen
  - if a uniqueness conflict implies shape mismatch, emit ingestion anomaly and stop cursor advancement

### Decode Scheduler

- Responsibilities:
  - select Layer 1 rows with `application_id`
  - resolve registry entries
  - run decoder or record decode status
- Input contract:
  - raw row identity:
    - `operation_id` or `posted_message_id` or equivalent raw key
  - `application_id`
  - `payload_kind`
  - `raw_bytes`
  - `reprocess_reason`
- Output contract:
  - `decode_status`
  - `application_id`
  - `app_type`
  - `payload_kind`
  - `payload_type`
  - `decoded_payload_json`
  - `decode_error`
  - `decoder_version`
- Decode status values:
  - `decoded`
  - `unresolved_application`
  - `unimplemented_decoder`
  - `decode_failed`

### Application Registry Resolver

- Responsibilities:
  - map `application_id` to app metadata
  - allow later backfill or correction
- Input contract:
  - `application_id`
- Output contract:
  - `registry_status`
  - `app_type`
  - `chain_id`
  - `creator_chain_id`
  - `metadata_json`
  - `abi_version`
- Rules:
  - misses must be explicit
  - registry updates must not require raw re-ingestion

### Normalizer

- Responsibilities:
  - join Layer 1 facts and decode results
  - emit Layer 2 events with stable correlation keys
- Input contract:
  - raw object identity keys
  - decode result
  - optional app metadata
- Output contract:
  - `normalized_event_id`
  - `event_family`
  - `event_type`
  - `correlation_key`
  - `source_chain_id`
  - `target_chain_id`
  - `source_block_hash`
  - `target_block_hash`
  - `source_cert_hash`
  - `transaction_index`
  - `message_index`
  - `event_payload_json`
  - `normalization_status`
- Normalization status values:
  - `observed`
  - `rejected`
  - `decode_failed`
  - `derived`

### Market Deriver

- Responsibilities:
  - transform Layer 2 into Layer 3 settled outputs
  - materialize product-facing derived state
- Input contract:
  - normalized events by ordered cursor
  - derivation mode:
    - `incremental`
    - `rebuild`
- Output contract:
  - `settled_output_type`
  - `settled_output_id`
  - `source_event_key`
  - `derivation_status`
  - `product_projection_updates`
- Derivation status values:
  - `settled`
  - `ignored_non_settled`
  - `blocked_missing_context`
  - `inconsistent_source`

## Processing Cursors

### Layer 1 Cursor

- Key:
  - `chain_id`
- Meaning:
  - highest fully committed block in raw storage

### Decode Cursor

- Key:
  - decoder worker name plus raw-table partition
- Meaning:
  - highest raw identity fully evaluated for decode status

### Normalize Cursor

- Key:
  - normalizer worker name plus source partition
- Meaning:
  - highest raw or decode sequence fully materialized into Layer 2

### Derive Cursor

- Key:
  - derivation job plus market projection
- Meaning:
  - highest Layer 2 sequence fully reflected in Layer 3

## Replay Semantics

- Layer 1 replay:
  - re-fetch same block
  - rely on storage uniqueness
- Decode replay:
  - rerun decode after registry or decoder update
  - replace or supersede decode result for the same raw identity
- Normalize replay:
  - recompute events for one raw identity or one chain range
  - preserve stable correlation keys
- Derive replay:
  - rebuild one pool, one owner, or one global projection from Layer 2

## Validation

- A Layer 1 commit must succeed or fail as a whole block
- A decode retry must not require deleting Layer 1 rows
- A normalizer retry must reproduce the same correlation key
- A Layer 3 rebuild must be possible using Layer 2 only

## Sources

- `agents/primitives/observability-storage.md`
- `agents/primitives/application-decoding.md`
- `agents/primitives/normalized-event-model.md`
- `agents/primitives/derived-market-state.md`
- `agents/runbooks/observability-deliverables.md`
