# Funding Current Implementation Delta

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Track known gaps between the current implementation and the target funding architecture.

## swap CreatePool

Known current behavior:

- `SwapOperation::CreatePool` exists as a public operation.
- The frontend Add Liquidity missing-pair path may submit it.
- The operation handler sends `SwapMessage::CreateUserPool` to the swap creator chain.
- Internal `SwapMessage::CreatePool` and `SwapMessage::UserPoolCreated` are part of current choreography.
- Meme-native initialization does not use public `CreatePool`; it uses `SwapOperation::InitializeLiquidity`, then `SwapMessage::InitializeLiquidity`, then the shared internal create-pool handler with `user_pool=false`.

Known gaps:

- Public `CreatePool` must be constrained to create-with-initial-liquidity.
- Empty, shell-only, one-sided, and virtual user pool creation must reject.
- The public `CreatePool` path must validate that both token identities are real before opening a pool chain.
- The current supported token set is native plus meme tokens only. Native is built in; meme tokens are validated from safe user-started paths by calling the meme token application for creator-chain identity. Every other token kind must reject until a concrete validation rule exists.
- Pending pair contention should use first-funded-wins semantics instead of permanent reject. Losing workflows must fail safely, credit already-custodied value to claim balances, and keep losing shell chains/applications non-tradable or cleaned up.
- Pool creation terminal truth must be unique and reliable in the intent state machine. A failed terminal workflow must not leave reusable old shell/application state.
- Internal create-pool messages must be intent-bound implementation steps.
- The current implementation does not yet implement first-funded-wins. It creates pool state on `PoolCreated` and then starts user initial liquidity through `UserPoolCreated -> PoolOperation::AddLiquidity`, without a canonical `PoolCreationIntent` terminal arbiter.
- If another user calls `AddLiquidity` on a pending shell, the target design must not create a second `PoolCreationIntent`. That operation creates only a pool-local `AddLiquidityIntent`; if it finalizes first, it activates the single swap-side `PoolCreationIntent` for the existing shell/pair and uses that finalized workflow's owner/recipient for LP ownership.

## CreateUserPool / UserPoolCreated

Known current behavior:

- `CreateUserPoolHandler` uses `message_signer_account()` to infer creator.
- `UserPoolCreatedHandler` directly calls pool `AddLiquidity`.
- `UserPoolCreatedHandler` calls `mark_user_pool_created(pool_application)` before calling pool `AddLiquidity`.
- `mark_user_pool_created` stores `processed_user_pool_creations[pool_application] = true` and skips later `UserPoolCreated` handling for the same pool application.

Known gaps:

- Owner, recipient, token, amount, and pair must come from persisted intent, not message signer or payload reconstruction.
- Shell receipt and user-pool-created handling must verify intent/source/app/chain.
- `mark_user_pool_created` is only a late narrow guard against repeated `UserPoolCreated` handling for the same pool application. The target protocol should make terminal intent status the single source of truth and ensure the flow itself allows only one valid pool-created transition per intent, rather than relying on a separate created flag or final duplicate guard.

## Message Tracking And Bouncing

Known current behavior:

- `base::HandlerOutcome` only stores destination and message.
- Contract adapters send ordinary messages from `HandlerOutcome`.
- `ContractRuntimeContext::send_message` is the central project abstraction used by handler outcome dispatch.
- The current Linera contract adapter attaches `.with_authentication()` there, but not `.with_tracking()`.
- No funding path currently handles `message_is_bouncing()` as a reject receipt.

Known gaps:

- Outgoing application messages should be tracked by default.
- Tracking should be added centrally in the runtime adapter's `send_message` implementation, not exposed as a business-handler-level message builder.
- Receiving handlers must detect bouncing messages and converge the relevant pending workflow state.
- This default tracking change is implemented in the user-pool-creation intent iteration before later funding and claim workflows depend on bounce handling.
- This follows the Linera SDK pattern used by `linera-protocol/examples/fungible/src/contract.rs`: send with `.with_tracking()` and inspect `message_is_bouncing()` on receive.

## Child Chain Cleanup

Known current behavior:

- Pool child-chain creation grants `close_chain` permission to the router/swap application through `ApplicationPermissions.close_chain`.
- Linera SDK exposes `ContractRuntime::close_chain()`, which closes the current chain when the application has that permission.

Known gaps:

- Losing or failed pool-creation shells must be made non-tradable or cleaned up under intent-state control.
- Cleanup must not be represented by a second terminal flag that can diverge from the create-pool intent status.
- Cleanup must resolve application-level custody before calling `close_chain()`. Linera `close_chain()` only marks the chain closed and does not move remaining balance or application custody.
- Failed shells must be permanently non-economic. Later funds delivered to a failed shell must not become reserves, LP shares, or sender-owned liquidity.

## AddLiquidity

Known gap:

- Add liquidity needs explicit two-leg pending/funded/finalized state before reserve update or LP mint.
- Current settled add-liquidity calculation already accepts liquidity based on the limiting side and directly transfers excess back. Target funding semantics keep the limiting-side calculation but route all excess/refund value through claim balances.

## Swap

Known gap:

- Swap output/refund should converge into claim balances instead of relying on direct payout as the only funds closure.

## RemoveLiquidity

Known gap:

- Remove output should converge into claim balances after burn/decrease, not rely on cross-chain direct payout as the only closure.

## Claim

Known gap:

- Target `Claim` operation/state is not yet implemented.
- Claim balances should be aggregated, not append-only per-event claim queues.
- Meme delivery needs aggregated `claiming_balances`, not per-claim delivery attempts.
- The current meme/pool payout path must be audited to confirm whether it can produce the success, fail, or bounce receipts required to close meme `Claim` delivery. If it cannot, the claim iteration must add the missing protocol messages instead of only changing pool claim state.
- Claim tests may seed balances through contract test fixtures or internal helpers. Do not add a production debug operation or public ABI solely for tests.

## Observability

Known gap:

- Projection must be updated as protocol facts change.
- Product read paths must derive claim balances, pending workflows, and stalled workflows from parsed facts.

## Iteration Mapping

- `FUND-005`: verify and expand this delta through code audit and characterization tests.
- `FUND-006`: lock public operation surface.
- `FUND-007`: intent-bind user pool creation.
- `FUND-008`: claim accounting and funds-exit foundation.
- `FUND-009`: add existing-pool two-leg liquidity state.
- `FUND-010`: converge initial liquidity through the two-leg closure.
- `FUND-011`: swap output to claim balances.
- `FUND-012`: remove/protocol-fee/remote-liquidity/create-pool-residual claim balances.
- `FUND-013`: internal boundary hardening.
- `FUND-014`: projection and product compatibility.
