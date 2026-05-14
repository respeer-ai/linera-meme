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

Known gaps:

- Public `CreatePool` must be constrained to create-with-initial-liquidity.
- Empty, shell-only, one-sided, and virtual user pool creation must reject.
- Internal create-pool messages must be intent-bound implementation steps.

## CreateUserPool / UserPoolCreated

Known current behavior:

- `CreateUserPoolHandler` uses `message_signer_account()` to infer creator.
- `UserPoolCreatedHandler` directly calls pool `AddLiquidity`.

Known gaps:

- Owner, recipient, token, amount, and pair must come from persisted intent, not message signer or payload reconstruction.
- Shell receipt and user-pool-created handling must verify intent/source/app/chain.

## AddLiquidity

Known gap:

- Add liquidity needs explicit two-leg pending/funded/finalized state before reserve update or LP mint.

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
- Meme delivery needs pending attempt state.

## Observability

Known gap:

- Projection must be updated as protocol facts change.
- Product read paths must derive claim balances, pending workflows, and stalled workflows from parsed facts.

## Iteration Mapping

- `FUND-005`: verify and expand this delta through code audit and characterization tests.
- `FUND-006`: lock public operation surface.
- `FUND-007`: intent-bind user pool creation.
- `FUND-008`: add existing-pool two-leg liquidity state.
- `FUND-009`: converge initial liquidity through the two-leg closure.
- `FUND-010`: swap output to claim balances.
- `FUND-011`: remove/excess/protocol-fee/remote-liquidity claim balances.
- `FUND-012`: claim operation and delivery attempts.
- `FUND-013`: internal boundary hardening.
- `FUND-014`: projection and product compatibility.
