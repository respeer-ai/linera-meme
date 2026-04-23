# Kline API Read Models

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Canonical mapping from existing kline APIs to target read models, serializers, and compatibility adapters.

## Facts

- Public API compatibility is the primary external constraint during rebuild
- Handlers should become thin transport adapters over stable read models
- Read models are fed by projections or diagnostics stores, not by ad hoc handler logic

## Rules

- Do not let handlers own correctness-critical business logic
- Do not let serializers fetch remote data
- Do not let compatibility adapters invent new semantics; they only preserve shape and naming
- Do not let one read model serve unrelated endpoint families if it couples their lifecycle

## Query API Contracts

### Kline Endpoints

- Endpoints:
  - `/points/...`
  - `/points/.../information`
- Handler package:
  - `query.handlers.kline`
- Read model:
  - `query.read_models.candles`
- Projection source:
  - `projection.candles`
- Serializer:
  - `query.serializers.kline`
- Compatibility adapter:
  - preserve existing point fields, interval semantics, and token ordering fields

### Transactions Endpoints

- Endpoints:
  - `/transactions/...`
  - `/transactions/information`
- Handler package:
  - `query.handlers.transactions`
- Read model:
  - `query.read_models.transactions`
- Projection source:
  - `projection.trades`
  - optional settled non-trade history projection if retained
- Serializer:
  - `query.serializers.transactions`
- Compatibility adapter:
  - preserve current response shape and `transaction_id` semantics exposed to clients

### Positions Endpoints

- Endpoints:
  - `/positions`
- Handler package:
  - `query.handlers.positions`
- Read model:
  - `query.read_models.positions`
- Projection source:
  - `projection.positions`
  - `projection.pools`
- Serializer:
  - `query.serializers.positions`
- Compatibility adapter:
  - preserve current fields such as `opened_at`, `status`, `current_liquidity`, token labels, and owner binding

### Position Metrics Endpoints

- Endpoints:
  - `/position-metrics`
- Handler package:
  - `query.handlers.position_metrics`
- Read model:
  - `query.read_models.position_metrics`
- Projection source:
  - `projection.positions`
  - `projection.fees`
  - `projection.pools`
- Diagnostics source:
  - blocker/exactness explanation model
- Serializer:
  - `query.serializers.position_metrics`
- Compatibility adapter:
  - preserve current blocker, exactness, and warning fields

### Ticker Endpoints

- Endpoints:
  - `/ticker/interval/{interval}`
- Handler package:
  - `query.handlers.ticker`
- Read model:
  - `query.read_models.ticker`
- Projection source:
  - `projection.stats`
  - `projection.trades`
- Serializer:
  - `query.serializers.ticker`

### Pool Stats Endpoints

- Endpoints:
  - `/poolstats/interval/{interval}`
- Handler package:
  - `query.handlers.pool_stats`
- Read model:
  - `query.read_models.pool_stats`
- Projection source:
  - `projection.stats`
  - `projection.pools`
- Serializer:
  - `query.serializers.pool_stats`

### Protocol Stats Endpoints

- Endpoints:
  - `/protocol/stats`
- Handler package:
  - `query.handlers.protocol_stats`
- Read model:
  - `query.read_models.protocol_stats`
- Projection source:
  - `projection.stats`
  - `projection.pools`
  - `projection.fees`
- Serializer:
  - `query.serializers.protocol_stats`

### Realtime Endpoint

- Endpoints:
  - `/ws`
- Handler package:
  - `query.handlers.websocket`
- Event source:
  - `realtime.publisher`
- Read model trigger:
  - projection delta stream
- Compatibility adapter:
  - preserve current subscribed payload families until frontend contract is intentionally revised

## Diagnostics API Contracts

### Transaction Audit Endpoints

- Endpoints:
  - `/transactions/audit/recent`
  - `/transactions/audit/replay`
- Handler package:
  - `diagnostics.handlers.transaction_audit`
- Read model:
  - `diagnostics.read_models.transaction_audit`
- Inspector:
  - `diagnostics.inspectors.replay_inspector`
- Serializer:
  - `diagnostics.serializers.transaction_audit`

### Diagnostic Event Endpoints

- Endpoints:
  - `/diagnostics`
- Handler package:
  - `diagnostics.handlers.events`
- Read model:
  - `diagnostics.read_models.events`
- Serializer:
  - `diagnostics.serializers.events`

### Debug Trace Endpoints

- Endpoints:
  - `/debug/traces`
- Handler package:
  - `diagnostics.handlers.traces`
- Read model:
  - `diagnostics.read_models.traces`
- Serializer:
  - `diagnostics.serializers.traces`

### Pool Debug Bundle Endpoints

- Endpoints:
  - `/debug/pool`
- Handler package:
  - `diagnostics.handlers.pool_debug`
- Read model:
  - `diagnostics.read_models.pool_debug_bundle`
- Serializer:
  - `diagnostics.serializers.pool_debug`

### Maker/Wallet Diagnostic Endpoints

- Endpoints:
  - `/events/...`
  - `/debug/wallets`
  - `/debug/wallets/{index}/metrics`
  - `/debug/wallets/{index}/balances`
  - `/debug/wallets/{index}/block`
  - `/debug/wallets/{index}/pending-messages`
  - `/debug/pools/stall`
  - `/debug/health`
- Handler package:
  - `diagnostics.handlers.maker_ops`
- Read models:
  - `diagnostics.read_models.maker_events`
  - `diagnostics.read_models.wallets`
  - `diagnostics.read_models.pool_stalls`
  - `diagnostics.read_models.health`
- Integration adapters:
  - `integration.wallet_client`
  - `integration.metrics_client`
- Serializer:
  - `diagnostics.serializers.maker_ops`

## Compatibility Strategy

### `compatibility.legacy_response_shapes`

- Owns:
  - current JSON field names
  - nullability compatibility
  - legacy envelope shapes
- Must not own:
  - DB queries
  - projection math
  - remote fetching

### `compatibility.endpoint_aliases`

- Owns:
  - preserving old route names if new internal handler names differ
- Must not own:
  - business logic

## Validation

- Every current endpoint is backed by exactly one primary read model
- Every handler delegates serialization to a serializer module
- Compatibility logic is isolated from projections and persistence
- Removing a compatibility adapter should only change external shape, not core correctness

## Sources

- `agents/primitives/kline-package-layout.md`
- `agents/runbooks/kline-capability-mapping.md`
- `agents/runbooks/observability-product-mapping.md`
