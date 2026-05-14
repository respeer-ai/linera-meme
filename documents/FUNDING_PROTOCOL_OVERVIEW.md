# Funding Protocol Overview

Status: Design Draft
Audience: Human reviewers

## Canonical Sources

The canonical implementation constraints live under `agents/primitives/funding/`:

- `architecture.md`
- `state-machines.md`
- `on-chain-data-model.md`
- `claim.md`
- `module-responsibilities.md`
- `security-invariants.md`
- `projection-and-product-reads.md`
- `open-issues.md`
- `current-delta.md`
- `implementation-plan.md`

This document is only a human-facing summary. Do not treat it as the task source or protocol truth.

## Summary

The funding protocol is designed to make AMM funding safe under asynchronous cross-chain execution. A target chain may delay or never execute a message, so every intermediate state must remain safe and observable without relying on timeout or generic retry semantics.

Only operations are user-reachable ABI. This includes direct frontend wallet submissions and user-authored contracts that call applications via `call_application`. Messages are internal contract-created effects and must be bound to persisted intents or claim delivery state.

The only user-facing funds-exit operation is `Claim`. Refund, retry, protocol-fee withdrawal, remote-liquidity withdrawal, excess withdrawal, and trading-yield withdrawal are claim-accounting meanings, not separate user operations.

## Design Shape

Long-lived economic state is aggregated:

- pool reserves
- total liquidity
- positions
- claim balances
- catalog status

Workflow intents exist only while a business action is not terminal. They protect cross-chain state transitions from forged, stale, delayed, wrong-source, or wrong-state effects. Linera core protocol provides once-only execution for accepted operations and messages; the application does not defend against exact duplicate execution of the same chain action. Once value clearly belongs to an owner, it should be credited to aggregated claim balances rather than stored as a long-lived per-event claim queue.

Claim balances are stored token-first and owner-second: `claim_balances[token].balances[owner]`. This keeps each token identity stored once at the pool-contract level. Connected-owner claim lists are product reads and should be served from parsed facts/projection APIs, not by scanning contract storage at UI read time.

Product data must come from parsed block facts and projections. Frontend claim lists, positions, TVL, APR inputs, transactions, candles, and pending/stalled workflow displays are projection-backed. Live query is limited to wallet identity, operation submission, and explicitly labeled live wallet balances.

## Main Flows

`CreatePool` remains a public `swap` operation only for the Add Liquidity missing-pair path. Its allowed meaning is create-with-initial-liquidity. Empty, shell-only, zero-liquidity, one-sided, and user virtual-liquidity pool creation must reject.

Existing-pool Add Liquidity and user-created initial liquidity both require two-leg pending state. Reserves and LP shares are finalized only after both token legs are funded.

Swap outputs and failed post-custody inputs are credited to claim balances. Remove Liquidity burns/decreases position and credits owed token amounts to claim balances. Protocol fee, remote liquidity, excess, and refunds use the same claim-balance exit model.

Native claim is synchronous on the pool chain. Meme token claim uses a delivery attempt: the claimed amount is frozen while the payout message is pending, and unavailable balance cannot be claimed again until success or explicit fail/bounce.

## Open Risks

Some states can remain in flight forever because the target chain may never execute the message:

- pool shell creation message never executes
- shell receipt never reaches swap
- one funding leg is funded while the other remains pending forever
- pool is finalized but activation receipt never reaches swap
- meme claim delivery remains pending forever

These are intentionally marked open. The safe first behavior is to keep them stalled, observable, and non-finalized where applicable. Do not add timeout-based refund, activation, retry, generic resume, or generic admin cancel without a state-specific design justified against Linera's core execution model.

## Iterative Delivery

Implementation is split into independently verifiable iterations:

1. Audit current contract paths and lock the executable baseline.
2. Lock the public operation surface.
3. Intent-bind user pool creation.
4. Add two-leg pending for existing Add Liquidity.
5. Reuse the two-leg closure for initial liquidity.
6. Move swap outputs/refunds into claim balances.
7. Move remove, excess, protocol fee, and remote liquidity into claim balances.
8. Implement `Claim` and delivery attempts.
9. Harden internal entry and application-caller boundaries.
10. Align projection facts and product reads.
11. Run the final cross-path regression suite.
