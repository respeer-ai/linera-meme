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

Outgoing application messages should be tracked by default. Tracking is used so the sender chain can observe a destination-chain reject as a bounce and converge pending workflow state safely. It is not a cross-chain atomic commit guarantee.

Message tracking is a runtime default, not business-handler boilerplate. Handlers send through the project runtime abstraction; that abstraction attaches authentication and tracking.

The only user-facing funds-exit operation is `Claim`. Refund, retry, protocol-fee withdrawal, remote-liquidity withdrawal, excess withdrawal, and trading-yield withdrawal are claim-accounting meanings, not separate user operations.

## Design Shape

Long-lived economic state is aggregated:

- pool reserves
- total liquidity
- positions
- claim balances
- pair state in `swap` application state

Workflow intents exist only while a business action is not terminal. They protect cross-chain state transitions from forged, stale, delayed, wrong-source, or wrong-state effects. Linera core protocol provides once-only execution for accepted operations and messages; the application does not defend against exact duplicate execution of the same chain action. Once value clearly belongs to an owner, it should be credited to aggregated claim balances rather than stored as a long-lived per-event claim queue.

Intent ids are allocated by the application that stores the canonical workflow intent state. For user pool creation, the canonical `PoolCreationIntent` is stored in `swap` application state on the swap chain. Persist a monotonic sequence in `swap` application state and combine it with the swap application identity. Pool-chain state may reference that same id, but it does not allocate a second canonical id for the same pool creation. Cross-chain storage is not shared; consistency comes from message-carried ids plus local source/app/status checks on each receiving chain. Do not rely on token pair, owner, timestamp, delivery order, or frontend input for uniqueness.

Claim balances are stored token-first and owner-second: `claim_balances[token].balances[owner]`. Asynchronous meme-token claims move value into matching `claiming_balances[token].balances[owner]` while payout is in flight. This keeps each token identity stored once at the pool-contract level. Connected-owner claim lists are product reads and should be served from parsed facts/projection APIs, not by scanning contract storage at UI read time.

Product data must come from parsed block facts and projections. Frontend claim lists, positions, TVL, APR inputs, transactions, candles, and pending/stalled workflow displays are projection-backed. Live query is limited to wallet identity, operation submission, and explicitly labeled live wallet balances.

## Main Flows

`CreatePool` remains a public `swap` operation only for the Add Liquidity missing-pair path. Its allowed meaning is user create-with-real-initial-liquidity. Empty, shell-only, zero-liquidity, one-sided, and user virtual-liquidity pool creation must reject. Meme-native initialization is a separate `InitializeLiquidity` path.

The supported token set is currently native plus meme tokens only. Other token kinds are rejected until a concrete validation rule exists.

Pending pair contention uses first-funded-wins semantics. The first workflow that reaches the required funded terminal state becomes active in `swap` application state; losing workflows must fail safely, credit already-custodied user value to claim balances, and keep losing shell chains/applications permanently non-economic or cleaned up. Pool creation terminal truth must live in one intent state machine, not in a separate created flag.

After a pool shell exists, a wallet may be able to call that pool application directly. This is not the atomicity boundary. The shell must have no finalized reserves or LP supply until a funding workflow finalizes. A later direct `AddLiquidity` on the shell does not create a second `PoolCreationIntent`; it creates only a pool-local `AddLiquidityIntent`. If that workflow completes two-leg funding before the original creator, it defines the initial reserves and wins, while activating the single swap-side intent for the existing shell and pair. Later creator funding is treated as normal add liquidity against current reserves: the limiting side determines accepted liquidity, and excess from the other side is credited to claim balances. It must not become a second initial reserve. Linera supports closing the current chain from an authorized application, but close only marks the chain closed and does not move remaining balance or application custody. Therefore close is only allowed after cleanup has resolved all application-level custody; otherwise the shell remains permanently failed/non-economic.

Existing-pool Add Liquidity and user-created initial liquidity both require two-leg pending state. Reserves and LP shares are finalized only after both token legs are funded.

Swap outputs and failed post-custody inputs are credited to claim balances. Remove Liquidity burns/decreases position and credits owed token amounts to claim balances. Protocol fee, remote liquidity, excess, and refunds use the same claim-balance exit model.

Native claim is synchronous on the pool chain. Meme token claim uses aggregated `claiming_balances`: the claimed amount moves from available claim balance to claiming balance while payout is pending, and cannot be claimed again until success removes it or fail/bounce returns it.

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
4. Add claim accounting and the `Claim` funds-exit foundation.
5. Add two-leg pending for existing Add Liquidity.
6. Reuse the two-leg closure for initial liquidity.
7. Move swap outputs/refunds into claim balances.
8. Move remove, excess, protocol fee, and remote liquidity into claim balances.
9. Audit and close residual internal entry and application-caller boundaries. Earlier iterations still implement their own path-local authorization, source-chain, authenticated-caller, intent, token, leg, and state validation.
10. Align projection facts and product reads.
11. Run the final cross-path regression suite.
