# MicroMeme Product Plan

## Vision

MicroMeme aims to become the combined product stack for Linera:

- Pump.fun: simple meme launch and instant market bootstrap.
- Uniswap: credible swap, liquidity, routing, and pricing infrastructure.
- Minable Meme: mining-native meme issuance and participation as a first-class feature.

MicroMeme should cover the full meme asset lifecycle:

1. Create a token.
2. Bootstrap a market.
3. Trade it.
4. Add and manage liquidity.
5. Join mining.
6. Discover and monitor market activity.

## Time Convention

All effort estimates in this document use AI work time, not human calendar time.

- `0.5d` means about half a focused AI work day.
- `1d` means about one focused AI work day.
- `5d` means about five focused AI work days.

## Current Product Position

Today MicroMeme already has:

- meme creation,
- initial pool creation,
- swap UI,
- add/remove liquidity,
- K-line and transaction display,
- mining service and mineable meme support.

But it is still closer to:

- a basic AMM,
- a protocol-first meme launcher,
- and a mining-enabled experiment,

than to a complete Pump.fun + Uniswap + Minable Meme product.

## Product Gaps

### 1. Market Integrity

Current market behavior is not yet trustworthy enough:

- buy and sell execution are asymmetric,
- mining introduces block-gated execution delay,
- sell-side settlement can require more blocks than buy-side settlement,
- K-lines can become structurally distorted,
- maker behavior can become unstable.

This is the highest-priority product issue.

### 2. Routing and Trading UX

Current trading is still effectively direct-pool trading.

Missing:

- multi-hop routing,
- best-path selection,
- path-aware quote display,
- route explanation,
- exact-output trading flow.

### 3. Quote Quality

Current pricing is still too approximate at the product layer.

Missing:

- robust quote engine,
- fee-aware quote output,
- realistic execution preview,
- better slippage semantics,
- delay-aware trade review.

### 4. Launch UX

Current token launch is still too protocol-centric.

Missing:

- clear launch modes,
- creator presets,
- launch progress states,
- stronger discovery and trending loops,
- better creator trust and anti-rug surfaces.

### 5. Mining UX

Mining exists, but is not yet productized well enough.

Missing:

- mineable launch mode with clear presets,
- mining-aware market labels,
- miner analytics,
- mining dashboard,
- clear explanation of how mining affects market behavior.

### 6. LP Product Depth

Current LP functionality is usable but shallow.

Missing:

- fee visibility,
- LP earnings view,
- stronger position management UX,
- multiple fee tiers,
- eventually concentrated liquidity or equivalent higher-capital-efficiency model.

### 7. Power User Features

Missing:

- limit-style trading,
- DCA / TWAP style flows,
- pro execution detail screens,
- richer market analytics,
- oracle-grade market data surfaces.

## Strategic Product Layers

### Layer A: Meme Launch

Goal:

- Make MicroMeme the easiest way to launch a meme on Linera.

Key outcomes:

- low-friction creation,
- immediate market bootstrap,
- creator-oriented launch presets,
- stronger token discovery.

### Layer B: Exchange

Goal:

- Make MicroMeme a trustworthy meme trading venue.

Key outcomes:

- better execution,
- better quotes,
- better routing,
- stronger LP infrastructure.

### Layer C: Mining

Goal:

- Make mineable meme tokens a real product advantage.

Key outcomes:

- mineable launch flows,
- miner participation UX,
- mining-aware market presentation,
- mining as differentiated value rather than hidden complexity.

## Product Roadmap

### Phase 0: Fix Market Integrity

Estimated effort: `4d - 7d`

Goals:

- reduce execution asymmetry,
- reduce K-line distortion caused by settlement timing,
- stabilize maker behavior in mining and non-mining markets.

### Phase 1: Build Trustworthy Swap UX

Estimated effort: `5d - 8d`

Goals:

- improve quote quality,
- improve trade review,
- improve slippage and failure handling,
- make trade outcomes predictable enough for users to trust.

### Phase 2: Add Routing Intelligence

Estimated effort: `5d - 9d`

Goals:

- enable multi-hop routing,
- improve effective liquidity,
- make more pairs tradable,
- reduce fragmentation.

### Phase 3: Build a Real Pump.fun-Style Launch Product

Estimated effort: `6d - 10d`

Goals:

- define launch modes,
- simplify token creation,
- improve launch conversion,
- improve discovery and social momentum surfaces.

### Phase 4: Productize Mining

Estimated effort: `5d - 9d`

Goals:

- make mining understandable,
- expose miner and reward analytics,
- integrate mining into launch and market UX.

### Phase 5: Upgrade LP Product

Estimated effort: `8d - 14d`

Goals:

- fee visibility,
- LP earnings and analytics,
- multi-fee-tier support,
- position management improvements.

### Phase 6: Advanced Exchange Features

Estimated effort: `8d - 15d`

Goals:

- advanced trader tooling,
- stronger analytics,
- oracle and market data productization,
- intent-based or conditional trading research.

## Priority Order

### Must Do First

- execution symmetry,
- mining-aware market stabilization,
- quote engine,
- multi-hop routing,
- launch simplification.

### Should Do Next

- mining dashboard and UX,
- LP fee analytics,
- richer market data semantics.

### Can Follow Later

- concentrated liquidity,
- advanced order types,
- pro trader surfaces.

## Product Success Criteria

MicroMeme becomes a strong first product candidate when:

- token creation is simple,
- pool trading is credible,
- quotes are believable,
- mining no longer makes markets feel broken,
- K-lines reflect actual market behavior clearly enough,
- and the product clearly answers:
  - how to launch,
  - how to trade,
  - how to add liquidity,
  - how to mine,
  - and why MicroMeme is better than a plain meme launcher.

