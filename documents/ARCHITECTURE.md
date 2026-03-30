# MicroMeme Architecture

## Goal

MicroMeme is a Linera-native product stack that combines:

- meme launch,
- AMM trading and liquidity,
- mining-enabled meme issuance,
- and market data services.

This document describes the current system structure and the main runtime flows.

## System Overview

MicroMeme is split into protocol modules, services, and frontend modules.

### Protocol Modules

- `meme/`: meme token logic, token balances, mining state, mining rewards, and token-side transfer operations.
- `proxy/`: meme creation orchestration, miner registration, and creation-time coordination.
- `swap/`: pool registry and router-side state for available markets.
- `pool/`: per-pool execution logic for swap, add liquidity, remove liquidity, and transaction generation.
- `ams/`: application indexing and discovery support.
- `runtime/`, `abi/`, `base/`: shared runtime interfaces, types, and handler abstractions.

### Services

- `service/miner/`: mining worker that watches mineable meme chains and submits `mine` operations.
- `service/kline/`: trade indexing, K-line generation, ticker aggregation, and websocket push.

### Frontend

- `webui-v2/`: current primary UI for token creation, trading, liquidity, K-line display, and discovery.
- `webui/`: older UI code still present in the repository.

## Core Module Responsibilities

## `proxy/`

Primary role:

- coordinate creation of meme applications,
- manage operator and genesis miner flows,
- connect creation flow with swap and mining-related setup.

In product terms:

- this is the launch control layer.

## `meme/`

Primary role:

- hold meme token state,
- manage balances and transfers,
- manage mining state,
- validate and reward mining operations,
- expose token-side operations used by pools and other applications.

In product terms:

- this is both the token contract and the mining core.

## `swap/`

Primary role:

- track existing pools,
- expose pool discovery to the frontend and services,
- receive pool updates when transactions occur.

In product terms:

- this is the market registry and routing base layer.

## `pool/`

Primary role:

- execute swap,
- add and remove liquidity,
- manage pool reserves,
- record latest transactions,
- emit pool updates back to `swap/`.

In product terms:

- this is the per-market execution engine.

## `service/miner/`

Primary role:

- subscribe to mineable meme chains,
- fetch mining info,
- search nonces,
- submit `mine` operations when valid.

Important consequence:

- in mining-enabled markets, this service can affect when operations and messages become executable in practice.

## `service/kline/`

Primary role:

- read pool transactions,
- persist transactions and pool metadata,
- build K-lines and ticker stats,
- expose market data over HTTP and websocket.

Important consequence:

- this service reflects settled trades, not planned trades.
- any settlement asymmetry or mining-induced delay can change K-line shape.

## `webui-v2/`

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

pool -> service/kline -> charts / tickers / transactions
swap -> service/kline -> pool discovery and market indexing
```

## Main Runtime Flows

## 1. Meme Launch Flow

Typical path:

1. User initiates meme creation from `webui-v2`.
2. `proxy/` coordinates creation.
3. `meme/` application is instantiated with token and mining parameters.
4. `swap/` and `pool/` are involved if initial liquidity or pool creation is requested.
5. The new market becomes visible through swap state and market data services.

Participating modules:

- `webui-v2`
- `proxy`
- `meme`
- `swap`
- `pool`

## 2. Swap Flow

Typical path:

1. User submits a swap through `webui-v2`.
2. A `pool` operation is scheduled on the relevant chain.
3. Depending on asset type and chain location, funding messages may be required.
4. `pool/` updates reserves.
5. `pool/` creates a transaction record.
6. `swap/` receives updated pool state.
7. `service/kline/` indexes the resulting trade.

Participating modules:

- `webui-v2`
- `pool`
- `meme`
- `swap`
- `service/kline`

## 3. Mining Flow

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

## 4. K-line and Market Data Flow

Typical path:

1. `service/kline/` fetches pools from `swap/`.
2. For each pool it fetches latest transactions from `pool/`.
3. It persists normalized records to its database.
4. It computes K-line, ticker, protocol stats, and transaction feeds.
5. `webui-v2` consumes this over HTTP and websocket.

Participating modules:

- `swap`
- `pool`
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

### 4. Market Data Is Trade-Centric but Not Execution-Semantics-Aware

- delayed settlement, mining effects, and maker behavior are not yet modeled explicitly enough.

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

### 4. Improve Observability

- expose in-flight funding state,
- expose delayed settlement state,
- expose route and execution path metadata to services and UI.

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
service/kline/      Trade and K-line indexing service
webui-v2/           Current frontend
documents/          Product, technical, and architecture docs
```

## Near-Term Architecture Priorities

1. Fix buy/sell settlement asymmetry.
2. Define mining-aware execution semantics.
3. Add quote and routing layers above current pool registry.
4. Improve delayed-settlement observability.
5. Align frontend trade UX with protocol truth.

