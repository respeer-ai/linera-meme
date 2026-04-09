# Phase 1 TODO Parking Lot

## Purpose

This document captures important work that should not enter the current Phase 1 execution-stability track.

Phase 1 remains strictly focused on:

- stabilizing current trading behavior,
- clarifying execution semantics,
- reducing buy/sell asymmetry,
- making K-line behavior explainable,
- and validating maker stability.

Everything below is intentionally deferred.

## Frontend Integration Review Notes

Review snapshot recorded on `2026-04-09`.

These items are implemented visually in the frontend but are not fully wired to real product behavior yet:

- `Create Meme` metadata form maps multiple social/link inputs into `metadata.website` instead of distinct metadata fields.
- token/pool/transaction search UI emits input events but does not filter any list data yet.
- trending surface still renders placeholder captions and does not rank by live gainers, volume, or token age.
- pool APR / TVL / price-impact calculations still rely on incomplete assumptions such as hardcoded fee and native-pair-only TVL.
- pools tab shows an `Add liquidity` action button without a connected action.

These findings are documented here so they do not get lost while K-line and trading-stability work remains the active priority.

## Trading Infrastructure TODO

- Quote infrastructure
- Route-aware quote responses
- Exact-output trading flow
- Advanced slippage and execution preview
- Best-path selection
- Multi-hop routing

## Launch Product TODO

- Creator launch presets
- Clear launch modes
- Launch progress states
- Discovery and trending surfaces
- Creator trust and anti-rug surfaces

## Mining Product TODO

- Mining dashboard
- Miner analytics
- Mining reward presentation
- Mining-first launch UX

## LP and AMM TODO

- LP earnings visibility
- Live fee visibility
- Fee-tier design
- Concentrated liquidity research

## Advanced Market TODO

- Pro trader tools
- Limit-style trading
- DCA / TWAP-style execution
- Oracle-grade or TWAP market data
- Advanced analytics

## Rule

If a task does not directly improve current trading stability or current trading explainability, it stays in this document until Phase 1 is complete.
