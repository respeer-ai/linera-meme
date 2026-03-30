# MicroMeme Technical Roadmap

## Purpose

This document translates the product target into protocol and implementation work.

Target product:

- Pump.fun on Linera,
- Uniswap-like exchange infrastructure on Linera,
- mineable meme markets on Linera.

## Time Convention

All estimates use AI work time.

- `0.5d` = half a focused AI work day.
- `1d` = one focused AI work day.
- `5d` = five focused AI work days.

## Current Technical Deficits

### 1. Settlement Path Asymmetry

Current buy and sell flows are not operationally symmetric.

Observed consequences:

- sell-side trades can take more blocks than buy-side trades,
- mining amplifies this delay,
- maker gets directionally biased execution,
- K-lines reflect settlement artifacts instead of cleaner market behavior.

Required work:

- map full buy/sell message paths,
- reduce hop count differences where possible,
- define protocol-level timestamp semantics,
- ensure delayed settlement is visible to downstream consumers.

### 2. Mining-Gated Execution Semantics

Mining changes when operations and messages become executable.

Required work:

- define expected execution semantics under mining,
- document mining-height gating clearly,
- align maker logic with mining-aware settlement,
- prevent mining from making markets appear randomly broken.

### 3. Missing Quote Layer

Current swap UX relies too much on local estimation.

Required work:

- add a protocol-aligned quote module,
- support exact-input and exact-output style estimation,
- use real pool fee values,
- separate spot, quoted, and effective execution prices,
- expose route-aware quote APIs.

### 4. Missing Router Layer

Current swap logic is effectively direct-pool selection.

Required work:

- graph model for available pools,
- route search,
- best-path selection,
- path scoring,
- fallback through native-asset bridge paths,
- route explanation surfaces.

### 5. LP Infrastructure Is Too Basic

Current LP model is share-based and V2-like.

Required work:

- standardize fee accounting,
- expose LP earnings,
- support multiple fee tiers,
- prepare for concentrated liquidity research and migration path.

### 6. Market Data Semantics Are Incomplete

Current K-line service indexes trades, but not enough context.

Required work:

- annotate delayed settlement cases,
- distinguish maker-like flow from organic flow where possible,
- expose route-aware and mining-aware analytics,
- expose TWAP/oracle-friendly interfaces.

## Technical Roadmap

### Phase 0: Execution Semantics Audit and Repair

Estimated effort: `4d - 7d`

Deliverables:

- full buy vs sell settlement trace,
- mining vs non-mining execution trace,
- reduced directional hop asymmetry,
- explicit transaction timestamp definition,
- debug surfaces for in-flight and delayed fund requests.

Acceptance criteria:

- buy and sell latency distributions are materially closer,
- maker stalls caused by structural asymmetry are reduced,
- K-line anomalies are explainable from indexed state.

### Phase 1: Quote Infrastructure

Estimated effort: `5d - 8d`

Deliverables:

- quote service or quote module,
- exact-input estimate,
- exact-output estimate,
- fee-aware amount calculations,
- route-aware price impact calculation,
- UI-ready quote response structure.

Acceptance criteria:

- trade preview no longer depends on naive frontend multiplication,
- quoted output is materially closer to actual settled output.

### Phase 2: Routing Infrastructure

Estimated effort: `5d - 9d`

Deliverables:

- pool graph representation,
- multi-hop route search,
- best-path selection,
- path cost model,
- route explanation metadata.

Acceptance criteria:

- non-direct pairs can trade through valid paths,
- path selection improves effective execution quality.

### Phase 3: Launch-Mode Infrastructure

Estimated effort: `5d - 8d`

Deliverables:

- explicit launch-mode model,
- standard launch mode,
- mineable launch mode,
- liquidity-first launch mode,
- no-initial-liquidity or delayed-liquidity support where valid,
- clearer launch lifecycle states.

Acceptance criteria:

- launch logic is product-driven instead of scattered parameter behavior.

### Phase 4: Mining-Aware Market Infrastructure

Estimated effort: `5d - 9d`

Deliverables:

- mining-aware maker controls,
- mining-aware UI flags and APIs,
- mining reward and miner analytics APIs,
- market data overlays for mining-induced delays.

Acceptance criteria:

- mining markets are operationally explainable and diagnosable.

### Phase 5: Fee and LP Accounting Upgrade

Estimated effort: `6d - 10d`

Deliverables:

- live fee exposure to frontend,
- LP earnings surfaces,
- fee-tier-capable pool model planning or implementation,
- better LP accounting APIs.

Acceptance criteria:

- fee values are protocol-driven, not hardcoded in UI,
- LP outcomes become inspectable.

### Phase 6: Advanced AMM and Market Data Work

Estimated effort: `8d - 15d`

Deliverables:

- concentrated liquidity research and design,
- oracle/TWAP productization,
- advanced trader APIs,
- route-level and settlement-level analytics.

Acceptance criteria:

- protocol is positioned for a stronger Uniswap-class evolution path.

## Immediate Technical Queue

1. Audit and reduce buy/sell execution asymmetry.
2. Formalize mining-aware execution and timestamp semantics.
3. Implement quote infrastructure.
4. Implement route search and best-path selection.
5. Replace hardcoded frontend fee assumptions with live pool data.
6. Add delayed-settlement-aware market data semantics.

## Exit Criteria for Core Protocol Maturity

MicroMeme reaches a strong technical baseline when:

- mining and non-mining markets behave predictably,
- buy and sell execution no longer diverge structurally,
- quotes are protocol-aligned,
- routing is path-aware,
- market data reflects real execution behavior,
- and frontend trade UX is driven by protocol truth instead of approximation.

