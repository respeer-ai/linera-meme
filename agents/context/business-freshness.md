# Business Freshness

Type: Context
Audience: Coding assistants
Authority: High

## Purpose

Define event-driven business freshness status for product read paths backed by the observability pipeline.

## Facts

- Business freshness is observability state, not protocol truth.
- Business freshness checks read local service/kline state only by default.
- The status surface must explain whether `/points`, `/transactions`, and websocket market data are fresh relative to L1/L2/L3 pipeline watermarks.
- Freshness checks must not mutate business projections.
- Freshness checks must not trigger automatic replay, compensation, or recovery.
- Current design does not persist freshness status or history.
- Current design may keep an in-memory latest snapshot for debugging and future push integration.
- Future frontend status updates should use websocket/event push, not polling as the primary update mechanism.
- `GET /debug/business-freshness` is a debug/status read surface and may be used by a future frontend status page for initial load or manual inspection.

## Rules

- Do not add an independent watchdog loop for business freshness.
- Do not add a business freshness table until a concrete frontend or operations history requirement exists.
- Do not use frontend polling as the target realtime update model.
- Do not check live pool state or wallet state as the normal freshness truth source.
- Do not make `/points` or `/transactions` perform freshness repair work during product reads.
- Do not call normalization replay, market-derivation replay, or observability recovery from freshness checks.
- Integrate checks with existing event-driven completion points.
- Check failures must not fail ingestion, normalization, market derivation, or websocket market-data publication.

## Semantics

- L1 freshness:
  - source: `chain_cursors`
  - means local raw block ingestion has advanced for the chain.
- L2 freshness:
  - source: `processing_cursors` for normalization
  - means raw facts have been normalized into Layer 2 events.
- L3 freshness:
  - source: `processing_cursors` for `layer3_market_deriver`
  - means market projections have processed normalized market candidates.
- Product freshness:
  - source: projection-backed read models and settled projection tables
  - means `/transactions`, `/points`, and websocket payload builders can read projection data at the latest relevant L3 watermark.

## Status

- `fresh`: L1/L2/L3/product read watermarks are aligned for the checked scope.
- `upstream_idle`: local state has no newer upstream fact to prove product staleness.
- `l1_unavailable`: local L1 cursor state is missing or unreadable.
- `normalization_stale`: L1 has advanced but L2 cursor has not caught up.
- `market_derivation_stale`: L2 has advanced but L3 cursor has not caught up.
- `product_read_stale`: L3 settled facts exist but product read watermarks are behind.
- `unknown`: inputs are insufficient for a stronger status.

## Flow

1. Existing event-driven ingestion receives a chain notification or reconnect reconciliation.
2. Catch-up runs bounded ingestion for the affected chain.
3. Normalization and market derivation run through the existing post-ingest pipeline.
4. After an event-driven completion point succeeds or fails, request a freshness check for the relevant chain or pool scope.
5. Freshness service computes a snapshot from current local DB watermarks.
6. Freshness service updates the in-memory latest snapshot.
7. Future websocket integration may publish a `business_freshness` status event from the same snapshot update path.

## Event Hooks

- Hook after `ChainEventProcessor._process_chain_until_idle` stores the chain catch-up result.
- Hook after normalization completion through the post-ingest pipeline boundary.
- Hook after `MarketDerivationWorker.process_items` updates the L3 cursor and publishes market-data events.
- Hook debug endpoint requests by computing a fresh snapshot on demand.

## Debug API

- Add `GET /debug/business-freshness`.
- Accept optional filters:
  - `chain_id`
  - `pool_application`
- Return:
  - current computed snapshot
  - latest in-memory event-driven snapshot when present
  - status and reason codes
  - L1/L2/L3/product watermarks
- The endpoint must not persist results.
- The endpoint must not trigger replay or recovery.

## Future Push Contract

- Add websocket topic `business_freshness` only when frontend status page work starts.
- Push the same snapshot shape returned by the debug API.
- Use event-driven snapshot updates as the push trigger.
- Do not introduce a separate polling or watchdog subsystem for push.

## Implementation Tasks

- Canonical task: `POS-065`.
