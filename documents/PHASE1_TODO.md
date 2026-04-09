# MicroMeme Project Status and Task Board

## Purpose

This document is the single source of truth for:

- current project status,
- unfinished product and engineering work,
- execution priority,
- and the active task board.

Other documents in `documents/` remain useful as design references, background context, or historical records, but they are not authoritative for current status or task tracking.

## Source of Truth Rule

- Current project state must be updated here first.
- New unfinished work must be added here first.
- Status changes must be reflected here first.
- No other document should maintain a competing live task board.

## Current Project State

Review snapshot recorded on `2026-04-09`.

### Stable / Implemented

- meme creation flow exists,
- initial pool creation exists,
- swap UI exists,
- add/remove liquidity flow exists,
- K-line HTTP and WebSocket services are running,
- mining service and mineable meme support exist,
- K-line startup path has been heavily stabilized,
- K-line frontend cache recovery and IndexedDB compatibility cleanup are implemented,
- pre-aggregated candle storage is already in service,
- pair-aware and interval-aware WebSocket subscription is already implemented.

### Known Remaining Gaps

- strict financial K-line continuity is not fully complete yet:
  - backend still filters zero-volume candles,
  - backend still behaves like "trade-only buckets" instead of guaranteed continuous market buckets,
  - HTTP `/points` and frontend cache behavior are much improved, but final financial semantics are still an open item.
- token detail page does not exist yet.
- several frontend surfaces are visually present but not wired to real behavior yet.
- quote, routing, launch productization, mining productization, LP analytics, and advanced trader features are still incomplete.

## Product and Engineering Decisions Already Locked

### K-line Semantics

- K-line work must follow strict financial semantics.
- Forming-vs-closed candle semantics must be explicit.
- Volume semantics must be consistent across HTTP and WebSocket.
- Frontend must not silently drop valid candles.

### Testing Rule

- TDD is a hard constraint.
- Every functional change must land with complete regression coverage for the changed behavior.

### Token Detail Page Direction

- token detail page is required work.
- chain data remains the authoritative source for on-chain facts.
- AI / A2UI may be used only for off-chain enrichment and page composition:
  - official links extraction,
  - social summary,
  - project narrative summary,
  - activity summary,
  - risk or missing-information hints.
- AI must not fabricate financial data or replace deterministic on-chain data.
- recommended implementation shape:
  - define a structured `TokenProfile`,
  - keep chain-backed market data deterministic,
  - run AI enrichment into structured fields,
  - render one composed details page from both sources.

## Frontend Integration Findings

These are real unfinished frontend integration items:

- `Create Meme` metadata form maps multiple social/link inputs into `metadata.website` instead of distinct metadata fields.
- trending surface still renders placeholder captions and does not rank by live gainers, volume, or token age.
- pool APR / TVL / price-impact calculations still rely on incomplete assumptions such as hardcoded fee and native-pair-only TVL.
- pools tab shows an `Add liquidity` action button without a connected action.
- token detail page is missing entirely.
- token / pool / transaction search still needs a real search architecture and should be solved together with pagination / incremental loading instead of only local frontend filtering.

## Unified Task Board

Status convention:

- `TODO`: defined but not started
- `READY`: dependencies are clear and can start now
- `IN PROGRESS`: actively being executed
- `BLOCKED`: waiting on a prerequisite
- `DONE`: implemented and verified

Execution rules:

- this table is the only live task board,
- every row must define test expectations before implementation,
- a row can move to `DONE` only when related tests are green,
- design docs may describe the work, but status is tracked only here.

### Defects and Incomplete Core Behavior

Defects must be prioritized ahead of enhancement or expansion work.

| ID | Area | Task | Scope / Expected Output | Dependency | Required Test Coverage | Priority | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MM-01 | K-line Backend | Enforce strict financial candle continuity | Stop filtering zero-volume buckets, define continuous bucket semantics, and make `/points` consistent with strict financial chart expectations | None | Backend tests for zero-volume bucket retention, bucket continuity, and closed/forming semantics across `1min/5min/10min/1h` | D0 | DONE |
| MM-02 | K-line Backend | Align HTTP and WebSocket candle semantics completely | Verify identical OHLCV for closed buckets and explicit semantics for forming buckets across both transports | MM-01 | Backend + frontend regression tests for identical closed-bucket data across HTTP and WebSocket | D0 | DONE |
| MM-03 | Meme Creation | Fix metadata field wiring | Map website, twitter, telegram, discord and similar fields into distinct metadata keys | None | Form-state and payload regression tests for every metadata field | D1 | DONE |
| MM-04 | Discovery | Replace trending placeholders with real ranking | Drive trending by real gainers / volume / age logic instead of placeholder text | None | Ranking and rendering tests for live sorting and displayed metadata | D1 | DONE |
| MM-05 | Pools | Correct APR / TVL / price-impact semantics | Replace hardcoded and incomplete assumptions with protocol-driven calculations. Implemented scope: fixed protocol fee single source of truth, shared price-impact math, native-valued pool TVL / volume / APR, and `--` fallback when valuation is unavailable | None | Calculation regression tests and frontend display tests | D1 | DONE |
| MM-06 | Pools | Wire Add Liquidity action | Connect pools tab `Add liquidity` button to the actual liquidity flow | None | Navigation and action wiring tests | D1 | READY |
| MM-07 | Token Details | Build token detail page foundation | Create routed token detail page with deterministic chain-backed market modules | None | Frontend route/component tests and data-loading tests | D1 | READY |

### Enhancements and New Features

| ID | Area | Task | Scope / Expected Output | Dependency | Required Test Coverage | Priority | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MM-20 | Frontend Infra | Upgrade `@linera/client` to the latest version | Update the frontend dependency to the latest compatible release, adapt touched call sites if APIs changed, and verify build/runtime compatibility | None | Dependency upgrade regression tests, typecheck, build verification, and targeted integration coverage for touched Linera client flows | F1 | TODO |
| MM-08 | Discovery | Build real search with pagination-aware loading | Design token/pool/transaction search together with pagination / incremental loading so results are not limited to currently loaded frontend slices | None | Frontend + data-layer tests for search query state, pagination interaction, reset behavior, and partial-result loading semantics | F1 | TODO |
| MM-09 | Token Details | Add AI-assisted off-chain enrichment for token details | Define `TokenProfile`, enrich official links/social/narrative/risk hints via structured AI output, and render alongside chain data | MM-07 | Tests for profile parsing, source attribution, fallback behavior, and missing-field handling | F1 | TODO |
| MM-10 | Quote | Build quote infrastructure | Add deterministic quote module/service with fee-aware responses and UI-ready output | None | Quote calculation tests for exact-input semantics, fee handling, and response contract | F1 | TODO |
| MM-11 | Routing | Add route-aware execution and best-path selection | Support multi-hop routing, best-path search, and route explanation | MM-10 | Routing tests for path search, path scoring, fallback behavior, and route metadata | F1 | TODO |
| MM-12 | Trading UX | Add exact-output and advanced execution preview | Support exact-output flow, better slippage semantics, and clearer execution preview | MM-10 | Trade preview and failure-mode regression tests | F1 | TODO |
| MM-13 | Launch Product | Productize creator launch flows | Add launch presets, explicit launch modes, progress states, and discovery hooks | None | Frontend + backend tests for launch mode selection and lifecycle state transitions | F2 | TODO |
| MM-14 | Mining Product | Productize mining UX | Add mining dashboard, miner analytics, reward presentation, and mining-aware surfaces | None | Data pipeline and rendering tests for mining metrics and views | F2 | TODO |
| MM-15 | LP / AMM | Expose LP earnings and live fee visibility | Make fee values and LP outcomes inspectable in product surfaces | None | Backend API and frontend rendering tests for fee and LP metrics | F2 | TODO |
| MM-16 | LP / AMM | Research and plan fee tiers / concentrated liquidity | Produce a concrete design and migration plan for deeper AMM capability | None | Design validation artifacts and schema/interface contract tests where applicable | F3 | TODO |
| MM-17 | Advanced Market | Add advanced trader tooling | Add limit-style trading, DCA / TWAP style execution, richer analytics, and oracle-grade market data surfaces | MM-10, MM-11 | Strategy and data regression tests for each shipped tool | F3 | TODO |
| MM-18 | Meme Creation | Support emoji meme assets | Allow emoji-first meme identity and asset handling in creation, display, and discovery surfaces | None | Frontend and backend tests for emoji input, persistence, rendering, and sorting/filter compatibility | F2 | TODO |
| MM-19 | Meme Creation | Support AI image generation for meme launch | Let creators generate meme artwork with AI and use the output directly in the meme creation flow | None | Tests for generation request flow, asset persistence, fallback behavior, moderation/error handling, and form integration | F2 | TODO |

## Recommended Next Slice

If execution resumes immediately, the next recommended order is:

1. `MM-01` strict financial candle continuity
2. `MM-02` HTTP / WebSocket semantic alignment
3. `MM-03` metadata field wiring
4. `MM-05` pool metric semantics
5. `MM-06` add-liquidity action wiring
6. `MM-07` token detail page foundation
7. `MM-20` upgrade `@linera/client` to latest version
8. `MM-08` real search with pagination-aware loading

This sequence keeps current market semantics and core product completeness ahead of larger feature expansion.
