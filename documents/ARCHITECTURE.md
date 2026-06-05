# MicroMeme Architecture

> Audience: humans
>
> For assistant-specific rules, facts, and live task tracking, see `agents/`.

## Goal

MicroMeme is a Linera-native product stack that combines:

- meme launch,
- AMM trading and liquidity,
- mining-enabled meme issuance,
- and market data services.

This document describes the current system structure and the main runtime flows. Canonical assistant-facing constraints live under `agents/`; this human document must not override `agents/primitives/` or `agents/tasks/board.yaml`.

## System Overview

MicroMeme is split into protocol modules, services, and frontend modules.

### Protocol Modules

- `meme/`: meme token logic, token balances, mining state, mining rewards, and token-side transfer operations.
- `proxy/`: meme creation orchestration, miner registration, and creation-time coordination.
- `swap/`: pool registry and router-side state for available markets.
- `pool/`: per-pool AMM execution, reserves, liquidity, positions, transaction facts, and target funding/claim accounting.
- `ams/`: application indexing and discovery support.
- `runtime/`, `abi/`, `base/`: shared runtime interfaces, types, and handler abstractions.

### Services

- `service/miner/`: mining worker that watches mineable meme chains and submits `mine` operations.
- `service/kline/`: block-based observability, normalized events, derived market data, positions, candles, transactions, stats, diagnostics, and websocket push.

### Frontend

- `webui-v2/`: current primary UI for token creation, trading, liquidity, K-line display, and discovery.
- `webui/`: older UI code still present in the repository.

## Core Module Responsibilities

### `proxy/`

Primary role:

- coordinate creation of meme applications,
- manage operator and genesis miner flows,
- connect creation flow with swap and mining-related setup.

In product terms:

- this is the launch control layer.

### `meme/`

Primary role:

- hold meme token state,
- manage balances and transfers,
- manage mining state,
- validate and reward mining operations,
- expose token-side operations used by pools and other applications.

In product terms:

- this is both the token contract and the mining core.

### `swap/`

Primary role:

- track existing pools,
- expose pool discovery to the frontend and services,
- receive pool updates when transactions occur.

In product terms:

- this is the market registry and routing base layer.

### `pool/`

Primary role:

- execute swap,
- add and remove liquidity,
- manage pool reserves,
- emit protocol facts consumed by observability,
- participate in target funding and claim accounting.

In product terms:

- this is the per-market execution engine.

### `service/miner/`

Primary role:

- subscribe to mineable meme chains,
- fetch mining info,
- search nonces,
- submit `mine` operations when valid.

Important consequence:

- in mining-enabled markets, this service can affect when operations and messages become executable in practice.

### `service/kline/`

Primary role:

- ingest parsed chain facts,
- derive normalized events and market-data projections,
- build K-lines, transactions, positions, stats, and diagnostics,
- expose projection-backed market data over HTTP and websocket.

Important consequence:

- this service reflects parsed chain facts and derived product projections, not planned trades or frontend state.
- any settlement asymmetry, stalled workflow, or mining-induced delay must be modeled from facts before entering product read models.

### `webui-v2/`

Primary role:

- creator UX,
- swap UX,
- LP UX,
- market discovery and charts,
- market and protocol stats.

Important consequence:

- current frontend still approximates parts of quote and execution behavior locally.

## Current High-Level Architecture

```text
Creator / Trader / Miner
        |
        v
    webui-v2
        |
        v
   GraphQL / wallet calls
        |
        +--------------------+
        |                    |
        v                    v
      proxy                swap
        |                    |
        v                    v
      meme <----------->    pool
        ^
        |
   service/miner

Linera chain facts -> service/kline -> charts / tickers / transactions / positions / diagnostics
swap/pool/meme facts -> service/kline -> pool discovery and market indexing
```

## Main Runtime Flows

### 1. Meme Launch Flow

Typical path:

1. User initiates meme creation from `webui-v2`.
2. `proxy/` coordinates creation.
3. `meme/` application is instantiated with token and mining parameters.
4. `swap/` and `pool/` are involved if initial liquidity or pool creation is requested.
5. The new market becomes visible through parsed facts and projection-backed product APIs.

Participating modules:

- `webui-v2`
- `proxy`
- `meme`
- `swap`
- `pool`

### 2. Swap Flow

Typical path:

1. User submits a swap through `webui-v2`.
2. A `pool` operation is scheduled on the relevant chain.
3. Depending on asset type and chain location, funding messages may be required.
4. `pool/` updates reserves.
5. `pool/` emits protocol facts for settled trade/accounting state.
6. `swap/` receives valid pool updates where required by catalog semantics.
7. `service/kline/` derives transactions, candles, and stats from parsed facts.

Participating modules:

- `webui-v2`
- `pool`
- `meme`
- `swap`
- `service/kline`

### 3. Mining Flow

Typical path:

1. `service/miner/` watches mineable meme chains.
2. It fetches mining info from `meme/`.
3. It searches for a valid nonce.
4. It submits `MemeOperation::Mine`.
5. `meme/` validates the nonce and applies mining reward state updates.

Participating modules:

- `service/miner`
- `meme`

Important product effect:

- mining affects execution timing and can influence trade settlement behavior and market data shape.

### 4. K-line and Market Data Flow

Typical path:

1. `service/kline/` ingests parsed chain facts.
2. It normalizes application events.
3. It derives Layer 3 market-data read models.
4. It computes K-line, transactions, positions, TVL, APR inputs, protocol stats, and diagnostics.
5. `webui-v2` consumes projection-backed HTTP APIs and websocket invalidation/update signals.

Participating modules:

- Linera chain facts
- `swap`
- `pool`
- `meme`
- `service/kline`
- `webui-v2`

## Architectural Strengths

- Clear separation between token, pool, router, and market data responsibilities.
- Mining is not bolted on externally; it is integrated into token behavior.
- K-line indexing is separated from contract execution.
- Product stack already spans launch, exchange, mining, and data.

## Current Architectural Weaknesses

### 1. Settlement Semantics Are Too Complex for Product Expectations

- buy and sell paths are not symmetric,
- mining affects execution timing,
- delayed settlement leaks directly into market behavior.

### 2. Router Layer Is Still Thin

- `swap/` is a registry and update layer more than a full route engine.
- path search and quote logic are still missing.

### 3. Frontend Still Owns Too Much Quote Logic

- parts of price and swap estimation are still local UI logic,
- which weakens execution trust.

### 4. Funding Consistency Is Still Being Hardened

- asynchronous cross-chain funding can remain pending indefinitely,
- output/refund/protocol-fee delivery is being converged into a unified claim model,
- stalled workflows must remain safe and observable.

## Recommended Architectural Direction

### 1. Strengthen the Exchange Core

- introduce quote infrastructure,
- introduce route infrastructure,
- reduce directional settlement asymmetry.

### 2. Make Mining an Explicit Cross-Cutting Layer

- mining-aware maker,
- mining-aware quote semantics,
- mining-aware market data,
- mining-aware UI labels and warnings.

### 3. Separate Product Truth from UI Approximation

- move execution-critical quote logic behind protocol-aligned services or APIs,
- reduce frontend-only math for trade outcomes.

### 4. Preserve Observability As Product Data Platform

- expose pending and stalled funding state,
- expose claim balances and delivery attempts,
- keep product reads projection-backed instead of live-query reconstructed.

## Repository Map

```text
abi/                Shared types and GraphQL-visible contract ABI
base/               Shared handler abstractions
runtime/            Runtime interfaces used by contracts
proxy/              Meme creation and miner coordination
meme/               Token and mining contract
swap/               Pool registry and router-side state
pool/               Pool execution logic
service/miner/      Mining worker service
service/kline/      Observability and market-data projection service
webui-v2/           Current frontend
documents/          Product, technical, and architecture docs
```

## Near-Term Architecture Priorities

1. Complete funding consistency design and progressive implementation.
2. Keep observability as the complete parsed-fact data platform.
3. Maintain accurate positions, fees, TVL, volume, transactions, and candles from projections.
4. Harden public operation and internal message boundaries.
5. Keep frontend product state aligned with projection-backed APIs.
