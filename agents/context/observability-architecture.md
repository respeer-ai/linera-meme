# Observability Architecture

Type: Context
Audience: Coding assistants
Authority: High

## Purpose

Canonical architecture for the chain observability system that replaces `latestTransactions` as the primary truth source for `service/kline`.

## Facts

- Scope:
  - `service/kline` observability subsystem
  - future chain-ingestion worker(s)
  - MySQL persistence for raw facts, normalized events, and derived market data
- Parent service architecture:
  - `agents/context/kline-service-architecture.md`
- Primary external reference:
  - `linera-protocol/linera-explorer-new`
- `round` is not a primary identity dimension for blocks, bundles, or business events
- Chain progress is tracked by `chain_id + height`
- Cross-chain linkage is tracked with source-side certificate and transaction dimensions
- Kline semantics follow standard exchange semantics:
  - only settled trades enter candles
  - requests, pending actions, and rejects do not enter candles
- Real-time progression should be event-driven from chain notifications or equivalent subscription signals
- Catch-up is a compensating path, not a primary polling loop

## Semantics

- Layer 1 is raw chain fact storage
  - stores only chain facts
  - preserves raw bytes for user operations and messages
  - does not infer business success
- Layer 2 is normalized domain events
  - decodes known application payloads
  - correlates chain facts into business events
  - preserves explicit rejected and undecodable states
- Layer 3 is derived market state
  - powers `transactions`, `candles`, `positions`, `fees`, and diagnostics
  - only consumes finalized business events that satisfy product semantics

## Flow

```mermaid
flowchart LR
    A[Linera chains] --> B[Ingestion worker]
    B --> C[Layer 1 raw tables]
    C --> D[App registry]
    C --> E[Decoder registry]
    D --> F[Layer 2 normalized events]
    E --> F
    F --> G[Layer 3 derived tables]
    G --> H[Transactions API]
    G --> I[Kline API]
    G --> J[Positions API]
    C --> K[Diagnostics API]
    F --> K
    G --> K
```

## Implications

- Observability is not the whole kline architecture
- Query serving, diagnostics packaging, and non-observability read models belong to the broader `service/kline` architecture
- Do not derive `transactions`, `candles`, `positions`, or `fees` directly from `latestTransactions`
- Do not parse application payload bytes in Layer 1
- Do not use `round` as a cursor, dedup key, or event primary key
- Keep explorer-style object boundaries:
  - blocks
  - incoming bundles
  - posted messages
  - operations
  - outgoing messages
  - events
  - oracle responses
- Preserve both source-side and target-side dimensions for incoming bundles
- Do not make cron or periodic polling the primary ingestion driver
- Use catch-up only for:
  - service startup reconciliation
  - subscription reconnect reconciliation
  - explicit admin-triggered repair
  - detected lag or gap recovery
- Keep manual admin triggers available for diagnostics, but do not treat them as steady-state execution

## Checklist

1. Design Layer 1 schema first
2. Define cursor advancement and replay guarantees
3. Define application registry and decoder registry before Layer 2 implementation
4. Define `settled_trade` before Kline migration
5. Migrate product-facing tables only after Layer 1 and Layer 2 are stable

## Sources

- `https://github.com/linera-io/linera-protocol/tree/main/linera-explorer-new`
- `https://github.com/linera-io/linera-protocol/blob/main/linera-explorer-new/server-rust/src/db.rs`
- `https://github.com/linera-io/linera-protocol/blob/main/linera-explorer-new/server-rust/src/models.rs`
- `https://github.com/linera-io/linera-protocol/blob/main/linera-chain/src/manager.rs`
- `agents/tasks/board.yaml` (`POS-026`, `FUND-001`)
