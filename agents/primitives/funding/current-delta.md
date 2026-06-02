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
- Public `CreatePool` must not require frontend-supplied creator-chain identity. User-started `CreatePool` validates meme token identity from authoritative chain facts before opening a pool chain. The only carried creator-chain-id field is `SwapOperation::InitializeLiquidity.token_0_creator_chain_id` for the synchronous `meme -> call_application(swap.InitializeLiquidity)` exception; swap messages and `PoolParameters` must not carry token creator-chain-id fields.
- The current supported token set is native plus meme tokens only. Native is built in; meme tokens are validated from safe user-started paths by calling the meme token application for creator-chain identity. Every other token kind must reject until a concrete validation rule exists.
- Pool creation terminal truth must be unique and reliable in the message-driven state machine. A failed terminal workflow must not leave reusable old shell/application state.
- Internal create-pool messages must validate immutable carried facts and authoritative chain facts at each hop.
- The current implementation creates pool state on `PoolCreated` and then starts user initial liquidity through `UserPoolCreated -> PoolOperation::AddLiquidity`. That user path is retained; the first successful AddLiquidity completion writes the initial reserve/share facts for the zero-reserve user-created pool.
- Direct ordinary `AddLiquidity` on a pool without finalized reserve/share facts must not gain meme initialization authority or virtual-liquidity semantics. No additional persisted create-pool or add-liquidity intent is introduced for user CreatePool first funding.

## CreateUserPool / UserPoolCreated

Known current behavior:

- `CreateUserPoolHandler` uses `message_signer_account()` to infer creator.
- `UserPoolCreatedHandler` directly calls pool `AddLiquidity`.

Known gaps:

- Token, amount, pair, recipient, and origin must be validated from authoritative chain facts plus immutable carried message facts. Account facts must be defined per hop: use `message_signer_account()` when the message signer is the exact required business fact, and carry account facts only when the current hop cannot derive the required fact from chain state.
- Shell receipt and user-pool-created handling must verify immutable carried facts plus source/app/chain.
- `mark_user_pool_created` was only a late narrow guard against repeated `UserPoolCreated` handling for the same pool application. The target protocol removes this auxiliary marker and relies on message legality plus pool-side funding facts instead.

## Message Tracking And Bouncing

Known current behavior:

- `base::HandlerOutcome` only stores destination and message.
- Contract adapters send ordinary messages from `HandlerOutcome`.
- `ContractRuntimeContext::send_message` is the central project abstraction used by handler outcome dispatch.
- The current Linera contract adapter attaches `.with_authentication()` there and attaches `.with_tracking()` only when the explicit `tracking` flag is true.
- No funding path currently handles `message_is_bouncing()` as a reject receipt.

Known gaps:

- Receiving handlers must detect bouncing messages and converge the relevant pending workflow state.
- Tracked paths follow the Linera SDK pattern used by `linera-protocol/examples/fungible/src/contract.rs`: send with `.with_tracking()` and inspect `message_is_bouncing()` on receive.

## Child Chain Cleanup

Known current behavior:

- Pool child-chain creation grants `close_chain` permission to the router/swap application through `ApplicationPermissions.close_chain`.
- Linera SDK exposes `ContractRuntime::close_chain()`, which closes the current chain when the application has that permission.

Known gaps:

- Losing or failed pool-creation shells must be made non-tradable or cleaned up under the reviewed message-driven workflow control.
- Cleanup must not be represented by a second terminal flag that can diverge from the reviewed create-pool workflow truth.
- Cleanup must resolve application-level custody before calling `close_chain()`. Linera `close_chain()` only marks the chain closed and does not move remaining balance or application custody.
- Failed shells must be permanently non-economic. Later funds delivered to a failed shell must not become reserves, LP shares, or sender-owned liquidity.

## AddLiquidity

Implemented in `FUND-009`:

- AddLiquidity no longer creates, reads, or updates persisted `FundRequest` state.
- AddLiquidity carries funding-request facts through `FundRequestExt`.
- AddLiquidity funding uses `RequestFundExt { prev, request, next }` and `FundResultExt { prev, request, next, result }`; it does not introduce `AddLiquidityContext`, `AddLiquidityLeg`, or ABI-visible `Token0` / `Token1` names.
- `counterparty_amount_out_min` is the message-carried counterpart min field.
- `counterparty_amount_in` is optional so the same request shape can later represent single-input Swap funding without another ABI change.
- `FundResultExt` proves source through Linera authenticated message facts: the origin chain is the request token creator chain, the caller is the current pool application replica on that chain, and the signer is the request owner.
- AddLiquidity tracks two-leg funding with message-carried `prev/request/next` facts before reserve update or LP mint, without adding `AddLiquidityIntent`.
- Partial funding failures, final AddLiquidity calculation failures after custody, and accepted-liquidity excess/refunds credit claim balances.
- Successful fungible custody is moved from the origin-chain pool app replica to the pool creator-chain pool app with `TransferFromApplicationWithReceipt` before final AddLiquidity settlement.

Remaining legacy scope:

- Persisted `FundRequest` remains only for paths not migrated in `FUND-009`, currently Swap. InitializeLiquidity main path already uses direct parameter passing and is not a reason to retain persisted `FundRequest` for AddLiquidity.

## Swap

Known gap:

- Swap output/refund must converge into claim balances instead of relying on direct payout as the only funds closure.

## RemoveLiquidity

Known gap:

- Remove output must converge into claim balances after burn/decrease, not rely on cross-chain direct payout as the only closure.

## Claim

Implemented foundation:

- `FUND-008` added aggregated claim balances, aggregated meme `claiming_balances`, target `Claim` operation, native synchronous claim semantics, meme asynchronous claim delivery, success/fail receipts, and bounce handling for the claim transfer request.

Known gap:

- Funding paths after `FUND-008` must start crediting owed value into claim balances.
- Projection must expose claimable, claiming, and abnormal rejected-settlement facts for product reads.

## Observability

Known gap:

- Projection must be updated as protocol facts change.
- Product read paths must derive claim balances, pending workflows, and stalled workflows from parsed facts.

## Iteration Mapping

- `FUND-005`: verify and expand this delta through code audit and characterization tests.
- `FUND-006`: lock public operation surface.
- `FUND-007`: split pool app creation from finalized reserve/share facts.
- `FUND-008`: claim accounting and funds-exit foundation.
- `FUND-009`: migrate AddLiquidity away from `FundRequest` and add existing-pool two-leg liquidity claim closure.
- `FUND-010`: pool visibility split.
- `FUND-011`: swap output to claim balances.
- `FUND-012`: remove/protocol-fee/remote-liquidity/create-pool-residual claim balances.
- `FUND-013`: internal boundary hardening.
- `FUND-014`: projection and product compatibility.
