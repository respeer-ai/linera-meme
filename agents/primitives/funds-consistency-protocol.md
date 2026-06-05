# Funds Consistency Protocol

Type: Primitive
Audience: Coding assistants
Authority: High

## Superseded

This document is superseded by the funding primitive set under `agents/primitives/funding/`.

Canonical references:

- `agents/primitives/funding/architecture.md`
- `agents/primitives/funding/state-machines.md`
- `agents/primitives/funding/on-chain-data-model.md`
- `agents/primitives/funding/claim.md`
- `agents/primitives/funding/module-responsibilities.md`
- `agents/primitives/funding/security-invariants.md`
- `agents/primitives/funding/projection-and-product-reads.md`
- `agents/primitives/funding/open-issues.md`
- `agents/primitives/funding/current-delta.md`
- `agents/primitives/funding/implementation-plan.md`

Do not extend this legacy document. Update the funding primitive set instead.

## Purpose

Define the target protocol for cross-chain AMM funds consistency before changing `pool/`, `swap/`, `meme/`, or `proxy/`.

## Scope

- Applies to `pool/`, `swap/`, `meme/`, and protocol-facing `proxy/` paths.
- Covers create meme native pool, user add-liquidity pool creation, existing-pool add liquidity, swap, remove liquidity, claim, and privileged/internal entry boundaries.
- Does not introduce per-operation temp chains for the current AMM.
- Does not define product projection schemas except where projection must consume explicit protocol facts.
- Target protocol changes include ABI/product-surface changes:
  - user-created pools are entered from the Add Liquidity product flow
  - current `SwapOperation::CreatePool` is allowed as the user-facing ABI only when it means create-with-initial-liquidity
  - `CreatePool` must never mean empty-pool or shell-only creation
  - claimable delivery requires a new pool claim operation/state surface
- legacy `CreateUserPool` and `UserPoolCreated` message choreography should be collapsed or strictly bound to the pool-creation intent

## Global Rules

- Chain contracts are protocol truth.
- Product-facing data must come from parsed block facts and projections, not live chain queries.
- A successful operation only proves the current transaction completed and outgoing messages were queued.
- A non-bounced tracked message is not whole-workflow success.
- `tracked + bouncing` is a one-hop reject receipt mechanism, not cross-chain atomic rollback.
- Native `transfer` failure in Wasm execution is not a recoverable business response.
- Grant refunds from bouncing messages are execution-resource refunds, not business-asset refunds.
- Do not finalize reserve, total supply, LP share, or settled market facts before required inputs are locked.
- Do not record successful add liquidity before LP share is minted.
- Do not record successful swap as fully delivered if output delivery is still pending.
- Do not burn LP share unless withdrawal value is either claimable or already delivered through a proven path.
- Do not silently drop downstream `MemeResponse::Fail`.
- Do not use temp chains to mask missing pending, claim, or refund state.
- Do not expose user product paths that bypass intent, identity, funding, or claim state.
- Do not treat virtual liquidity as deposited reserve, TVL, claimable native balance, or payable balance.
- Do not classify `transaction_id` gaps as a funds-consistency error by themselves.
- Treat funds inconsistency as a rejected/downstream-failed workflow that still leaves finalized reserve, total supply, LP share, settled transaction, or asset custody side effects.
- `PoolChainCreated` or pool shell creation is not product-level pool creation.
- `PoolCreated` must mean token identities are validated, pool app/chain are bound to a pending intent, and the pool protocol object exists.
- `PoolCreated` still does not imply tradable/economic readiness.
- `Active` is the only status that allows swap/add/remove routing and product economic exposure.

## Identity And State

- `intent_id`
  - Stable id for one user business action.
  - Created by the app that owns the workflow state.
  - Included in all follow-up messages.
- `leg_id`
  - Stable id for one funded asset leg.
  - Swap has one input leg.
  - Add liquidity has two input legs.
- `claim_id`
  - Stable id for one claimable output, withdrawal, excess, or refund.
  - Derived from `intent_id`, token identity, owner account, and direction.
- `verified_token_identity`
  - Result of token validation at trusted path entry.
  - Must be carried through intent state and follow-up messages.
  - Must not be reconstructed from user payload later.
- `pending`
  - Workflow exists but required remote effect is not complete.
- `funding_pending`
  - One or more input legs have been requested but not confirmed.
- `funded`
  - Required input asset has moved into protocol custody.
- `finalized`
  - Reserve, total supply, LP share, and settled fact have been committed.
- `claimable`
  - User-owned asset is available for retryable delivery.
- `claimed`
  - Claimable asset was successfully consumed by a claim.
- `failed`
  - Intent cannot continue and has no finalized state.
- `refund_ready`
  - User-owned input or excess is available as claimable refund.

## Token Validation

- Token existence and identity must be validated fail-fast at the earliest trusted entry of a path.
- Validation is not repeated in every internal handler.
- Existing active pool operations use the registered pool token identities and must not call token apps again.
- Native token validation is built in.
- Meme token validation uses `call_application(token_app, CreatorChainId)`.
- `call_application(token_app, CreatorChainId)` can execute on any chain; the constraint is safe call-stack context, not chain location.
- `call_application(token_app, CreatorChainId)` is allowed only on user-started `user -> swap` or equivalent trusted entry paths.
- Do not call token app for validation from `meme -> swap InitializeLiquidity`; use authenticated caller, source chain, and swap-side initialization route binding.
- Do not call token app from token funding callbacks, claim callbacks, or message handlers entered by token apps; use pending records and expected source/leg binding.
- If other token classes are introduced, they need an equivalent validation operation before they can enter pool creation.

## Message Tracking

- Use tracked messages for critical one-hop messages whose target-chain rejection must update source-chain pending state.
- Handle bouncing messages by inspecting `message_is_bouncing()`.
- A bounced message must update only the pending state for the source hop it represents.
- A bounced message must not roll back later hops that may already have succeeded.
- A non-bounced tracked message is not whole-workflow success.
- Create-pool shell messages should be tracked so source pending intent can become failed if child-chain creation rejects.
- Funding request messages should be tracked so funding pending state can become failed or refund-ready when the funding hop rejects.
- Pool activation/update messages should be tracked or otherwise explicitly acknowledged so catalog pending/active state cannot silently diverge.
- Claim delivery messages should leave the claimable record intact if the delivery hop rejects.

## Create Meme Native Pool

Target path: initialize a meme/native pool while creating a meme. Meme existence is guaranteed by meme app creation itself; swap must not call back into meme for validation on this path, to avoid application reentrancy.

1. User wallet chain
   Application: `meme`.
   Account: user signer.
   Action: submit meme creation operation with meme metadata, real initial token liquidity, virtual native reference, and target swap app.
   Transmission: user operation enters the `meme` contract.
   Constraint: virtual native reference is only a pricing reference; it is not native deposit, reserve, TVL, or claimable balance.
   Risk and mitigation: treating virtual native as real reserve corrupts positions, TVL, and claimable balances. The swap-side initialization route stores `native_amount` plus `virtual_initial_liquidity`, and implementation helper APIs must distinguish real native custody amount from virtual native reference amount before reserve, TVL, claim, and payable-balance code can read the value.

2. meme operation handler
   Chain: user wallet chain or meme creation chain.
   Application: `meme`.
   Account: user signer.
   Action:
   - Create meme app/state.
   - Commit meme state, balances, mining state, metadata, and allowance facts.
   - Send initialization message to swap creator/root chain.
   Transmission: `meme -> swap` message carrying meme token app id, creator chain id, adjusted fungible amount, native amount, virtual native flag, and creator/fee receiver. The meme app does not enforce route uniqueness; the swap-side route enforces at most one initialization route for each meme token app.
   Constraint: swap must be able to bind the message to the meme app authenticated caller.
   Risk and mitigation: if swap trusts only payload-claimed token id, a malicious app can forge initialization. The swap handler must verify `authenticated_caller_id == token_app` and verify source chain matches token creator chain.

3. swap initialize-liquidity operation/message entry
   Chain: swap creator/root chain.
   Application: `swap`.
   Account: not a direct user signer; the source must be meme app authenticated caller.
   Action:
   - Reject directly user-reachable `SwapOperation::InitializeLiquidity`.
   - Allocate a swap-side `route_id` after accepting `SwapMessage::InitializeLiquidity`.
   - Verify authenticated caller, source chain, and meme creator chain.
   - Create swap-side initialization route with status `accepted`, then `pool_shell_sent`, not active.
   - Open pool child chain.
   Transmission: `swap -> pool child chain` tracked message that creates the pool app/shell.
   Bounce handling: if child-chain creation rejects, transition initialization route to failed; do not write active pool catalog and do not write finalized reserve.
   Constraint: do not `call_application(meme, CreatorChainId)` here because the call stack is already `meme -> swap`; calling back into meme introduces application reentrancy risk.
   Risk and mitigation: if initialization failure still writes a successful catalog record, users see a non-tradable pool. Catalog may write pending only, not active.

4. pool child chain create
   Chain: new pool child chain.
   Application: `pool`.
   Account: swap app / system-created app context.
   Action:
   - Create pool app.
   - Initialize pool state: token0/token1, registered app ids, virtual reference, and fee config.
   - Do not write finalized reserve.
   Transmission: `pool child -> swap root` `PoolChainCreated` or equivalent shell receipt carrying pool app id, `route_id`, and pool chain id.
   Constraint: pool shell receipt only means child chain/app shell creation completed; it is not product-level `PoolCreated` and does not mean tradable.
   Risk and mitigation: a shell receipt verified only by child chain can be forged or misbound; swap must match the route's expected pool chain, expected token identity, and expected pool app.

5. swap receives pool shell receipt
   Chain: swap creator/root chain.
   Application: `swap`.
   Account: pool app authenticated caller / expected child chain.
   Action:
   - Match pending initialization route.
   - Write catalog status = shell_created or initializing, not active.
   - Allocate and persist an opaque `funding_correlation_id` for this meme funding segment.
   - Execute `call_application(token0, MemeOperation::InitializeLiquidity { funding_correlation_id, to: expected_pool_account, amount: adjusted_fungible_amount })`.
   - Move the route to `meme_funding_sent` only after the meme operation accepts the request and queues `MemeMessage::InitializeLiquidity`.
   Transmission: `swap -> meme` operation call, then `meme operation -> meme creator chain` `MemeMessage::InitializeLiquidity { funding_correlation_id, caller, to, amount }`.
   Bounce handling: if `MemeMessage::InitializeLiquidity` rejects or bounces, transition initialization route to `stalled_funding`; do not write `PoolCreated` product fact, `pool_funded`, or active.
   Constraint: accepted `MemeOperation::InitializeLiquidity` is not custody proof. Current implementation discards the call result and has no funding success/fail receipt; target protocol must add an explicit funding receipt before swap may move the route to `pool_funded`.
   Risk and mitigation: if swap treats the operation call as funding success, the route can become funded while meme tokens never entered pool custody. The funding path must bind `funding_correlation_id + expected token + expected source app + expected pool account + amount`. The correlation id is opaque to meme and has no meme-side business meaning.

6. meme funding receipt
   Chain: meme creator chain, then swap creator/root chain.
   Application: `meme`, then `swap`.
   Account: expected swap application caller / expected meme token application.
   Action:
   - Execute meme `transfer_from(caller, application_creation_account, expected_pool_account, adjusted_fungible_amount)`.
   - Execute `call_application(swap, SwapOperation::InitializeLiquidityFunded { funding_correlation_id, meme_application, pool_application, token0_identity, amount })` on the meme creator chain.
   - Swap operation on the token0 meme creator chain queues `SwapMessage::InitializeLiquidityFunded { funding_correlation_id, meme_application, pool_application, token0_identity, amount }` to the swap creator chain.
   - Swap creator-chain message handler first requires source chain equals the token0 meme creator chain and authenticated caller application equals the swap application.
   - Swap creator-chain message handler then resolves `funding_correlation_id` to exactly one pending route and accepts the funding receipt only after matching pool account, token identity, and amount.
   - Move initialization route from `meme_funding_sent` to `pool_funded`.
   Transmission: meme handler calls swap operation on the meme creator chain; swap operation sends swap funding receipt message to the swap creator chain.
   Bounce handling: if the funding receipt rejects or bounces, swap route remains `stalled_funding`; recovery must prove custody before crediting claim or retrying receipt.
   Constraint: `pool_funded` is only written from the accepted funding receipt or an equivalent custody proof, never from `PoolCreated` and never from accepted `MemeOperation::InitializeLiquidity` alone.
   Risk and mitigation: without this receipt, swap cannot distinguish transferred funds from pending or failed meme funding.

7. pool finalizes initial liquidity
   Chain: pool child chain.
   Application: `pool`.
   Account: pool app state.
   Action:
   - Write real reserve only after real meme token leg is funded and contract route state is `pool_funded`.
   - Write virtual reference as pricing reference; do not write native reserve.
   - Emit explicit initial virtual position fact with owner = creator/protocol fee receiver.
   - Do not create native claimable.
   - Emit pool-side finalized liquidity and transaction facts.
   - Call `SwapOperation::UpdatePool` through `call_application`; if the call fails, the current pool-chain transaction aborts and does not commit the transaction fact for the failed call.
   Transmission: pool-chain `call_application` queues `SwapMessage::UpdatePool` carrying finalized pool state hash, version, and `route_id`.
   Bounce handling: if `SwapMessage::UpdatePool` rejects or bounces, pool keeps finalized state but swap catalog remains non-active; recovery must replay/ack update, not recreate pool.
   Constraint: `PoolCreated` is still not tradable; only accepted `SwapMessage::UpdatePool` makes the pool Active.
   Risk and mitigation: virtual initial position must not use normal add-liquidity semantics, or it creates closed-position noise or two-sided pooled tokens. It must be an independent virtual position fact.

8. swap accepts pool update
   Chain: swap creator/root chain.
   Application: `swap`.
   Account: expected pool app.
   Action:
   - Match pending initialization route.
   - Accept `SwapMessage::UpdatePool`, verify custody and liquidity facts, write router pool truth, and move catalog status from pending to active.
   - Allow swap/add/remove routing only after active.
   Transmission: do not return fake user-side success; frontend/observability must decide tradability from active catalog and parsed facts.
   Risk and mitigation: if frontend allows trading on a pending pool, users route into an uninitialized pool. Product APIs must treat only active pools as tradable/economic pools.

## User CreatePool With Initial Liquidity

Target path: the user submits initial two-sided liquidity from the Add Liquidity product page. When the pair does not exist, the current frontend directly calls `SwapOperation::CreatePool`. The protocol meaning is not "create an empty pool"; it is create pool with initial liquidity. User-created pools must have real two-sided initial liquidity and must not use virtual liquidity.

1. User wallet chain
   Application: `swap`.
   Account: user signer.
   Action: current ABI entry is `SwapOperation::CreatePool { token0, token1, amount0, amount1, to }`; it must be interpreted as create-with-initial-liquidity.
   Transmission: user operation enters `swap`.
   Constraint: when the pair does not exist, `amount0 > 0 && amount1 > 0`; virtual liquidity is not allowed.
   Risk and mitigation: if `CreatePool` can create an empty or shell-only pool, it creates pool squatting and empty shells. `CreatePool` must immediately create a pending initial-liquidity intent, not only a pool shell.

2. swap operation handler
   Chain: user's current chain.
   Application: `swap`.
   Account: user signer.
   Action:
   - Check catalog.
   - Active pool: route to existing add liquidity.
   - Pending/Failed: reject.
   - Missing pair: run token validation and enter create-with-initial-liquidity.
   validation：
   - native: built in.
   - meme: `call_application(token_app, CreatorChainId)`.
   - other token classes: require equivalent validation operation, otherwise reject.
   Transmission: `call_application` executes inside the current user call stack.
   Constraint: this is an allowed token-app call path because the call stack is `user -> swap`, not `token -> swap`.
   Risk and mitigation: token existence must fail fast at the start; do not open the pool chain first and discover later that the meme does not exist.

3. swap creates pool intent
   Chain: swap chain.
   Application: `swap`.
   Account: user signer as intent owner / initial LP owner.
   Action:
   - Generate `intent_id`.
   - Persist verified token identities, amounts, slippage, owner account, and expected pair.
   - Write catalog pending, not active.
   - Open pool child chain.
   Transmission: `swap -> pool child` tracked create message.
   Bounce handling: if child-chain creation rejects, transition pending intent -> failed; if open-chain fee or fee budget was locked, create explicit refund/claimable path.
   Constraint: duplicate pool creation for the same pair in pending/failed state must reject or idempotently return the original intent.
   Risk and mitigation: without pending intent, later shell receipt / activation messages cannot be authenticated or bound; every follow-up message must match this intent.

4. pool child chain create
   Chain: pool child chain.
   Application: `pool`.
   Account: swap app context.
   Action:
   - Create pool app.
   - Initialize pair metadata and fee config.
   - Do not finalize reserve.
   Transmission: `pool -> swap` shell receipt, e.g. `PoolChainCreated(intent_id, pool_app, pool_chain)`.
   Constraint: shell receipt is not product-level `PoolCreated` and is not active fact.
   Risk and mitigation: message handler must verify source chain/app against pending intent; otherwise a malicious pool can register itself in catalog.

5. swap starts initial add liquidity
   Chain: swap/root or user wallet chain, depending on target routing implementation.
   Application: `swap`.
   Account: original user account read from create-with-initial-liquidity pending intent.
   Action:
   - Match pending intent.
   - Send initial add-liquidity message to pool app.
   Transmission: `swap -> pool` message carrying `intent_id`, owner account, amount0/amount1, min0/min1, and verified token identities.
   Constraint: if `CreateUserPool/UserPoolCreated` remains as internal messages, they can only be follow-up steps of the pending intent; do not reconstruct owner from payload or message signer.
   Risk and mitigation: current `CreateUserPool` uses `message_signer_account()` as creator. Safer target semantics: after user entry creates pending intent, every later owner/creator/to/amount value is read from the intent.

6. pool funds both legs
   Chain: pool child chain.
   Application: `pool`.
   Account: owner account from intent.
   Action:
   - Create add-liquidity intent.
   - Create two `leg_id`s.
   - Request token0/token1 funding.
   Transmission: `pool -> token app` request fund messages.
   Bounce handling: if funding request rejects, corresponding leg -> failed; the other already-funded leg must become claimable refund.
   Constraint: funding callback must not call token app validation; it only matches pending leg.
   Risk and mitigation: `FundSuccess/FundFail` keyed only by transfer id is insufficient; it must match expected token/source/caller/amount/intent.

7. pool handles funding result
   Chain: pool child chain.
   Application: `pool`.
   Account: pool app state.
   Action:
   - Both legs funded: calculate actual deposit, mint LP, write reserve, write settled add-liquidity fact, notify swap active.
   - One leg succeeds and the other fails: successful leg becomes claimable refund, failed leg records failed; do not write reserve, do not mint LP, do not write success fact.
   - Excess amount becomes claimable excess.
   Transmission: `pool -> swap` activation/update message only after finalized.
   Constraint: do not retry the missing leg; user starts a new operation.
   Risk and mitigation: cross-chain leg completion retry makes user funds and slippage semantics complex. Converging failed workflows into claimable refund is clearer and auditable.

8. swap activates catalog
   Chain: swap root/catalog chain.
   Application: `swap`.
   Account: expected pool app.
   Action: transition pending pair to active and record pool app/chain/version.
   Transmission: pool finalized message.
   Bounce handling: activation reject does not roll back finalized pool; recovery path is replay/ack activation.
   Constraint: only pool finalized add liquidity can make the pool active.
   Risk and mitigation: if shell-created pool becomes active, trades can enter an unfunded pool. Active must depend on post-finalization fact.

## Existing Pool AddLiquidity

Target path: pair is already active; user adds real liquidity to an existing pool.

1. User wallet chain
   Application: `swap` or direct `pool` router.
   Account: user signer.
   Action: add liquidity operation.
   Transmission: user operation routes to active pool.
   Constraint: active pool already has verified token identities; do not validate again.
   Risk and mitigation: repeated validation introduces unnecessary reentrancy and state drift; use catalog/pool registered identities.

2. pool operation handler
   Chain: pool child chain.
   Application: `pool`.
   Account: user owner account.
   Action:
   - Create add-liquidity intent.
   - Create two funding legs.
   - Request both legs' funds.
   Transmission: `pool -> token app` request fund messages.
   Bounce handling: if funding request rejects, corresponding leg failed; already-funded leg -> claimable refund.
   Constraint: do not mutate reserve or mint LP before both legs are funded.
   Risk and mitigation: when one leg succeeds and the other fails, the successful leg must become claimable refund and must not remain stuck in pool custody.

3. pool finalization
   Chain: pool child chain.
   Application: `pool`.
   Account: pool app state.
   Action:
   - Calculate LP share after both legs are funded.
   - Update reserve/total_supply.
   - Write settled add-liquidity fact.
   - Write excess as claimable.
   Transmission: `pool -> swap` internal pool update event/message.
   Bounce handling: pool update reject does not roll back finalized pool state; update must be replayable/idempotent.
   Constraint: duplicate success/finalize is idempotent; it must not double-count or double-mint.
   Risk and mitigation: every update-pool message must come from registered pool app and must not be forgeable by user operation.

## Swap

Target path: user swaps assets in an active pool. Output and refund both go through claimable; direct payout is not the sole funds-closure mechanism.

1. User wallet chain
   Application: `pool` through swap router.
   Account: user signer.
   Action: `PoolOperation::Swap { input_token, input_amount, min_output, to }`.
   Transmission: user operation routes to active pool.
   Constraint: pool must be active; tokens are read from pool state.
   Risk and mitigation: pending/failed pool rejects; shell pool must not be tradable.

2. pool requests input funding
   Chain: pool child chain.
   Application: `pool`.
   Account: user owner/source account.
   Action:
   - Create swap intent.
   - Create input `leg_id`.
   - Request input token funding.
   Transmission: `pool -> token app` funding request carrying intent/leg/expected source/amount.
   Bounce handling: if funding request rejects, intent -> failed/refund_ready according to custody state; do not write reserve and do not write transaction.
   Constraint: do not execute pricing, write reserve, or write transaction before input is funded.
   Risk and mitigation: writing transaction before funding leaves fake trades on failure.

3. pool handles input funding
   Chain: pool child chain.
   Application: `pool`.
   Account: pool app state.
   Action:
   - funding fail: intent failed/refund_ready; do not write reserve.
   - funding success: enter executable.
   Transmission: token funding callback message.
   Constraint: callback matches pending leg; do not trust free-form transfer id.
   Risk and mitigation: malicious or misrouted success must not increase reserve.

4. pool executes swap
   Chain: pool child chain.
   Application: `pool`.
   Account: pool app state.
   Action:
   - Check slippage/invariant.
   - Check failure: input becomes claimable refund; do not write reserve or settled swap.
   - Check success: update reserve, write settled swap fact, create output claimable.
   Transmission: notify swap/read side after settled fact.
   Constraint: output is not assumed delivered directly; claimable is the protocol delivery boundary.
   Risk and mitigation: direct payout failure cannot roll back committed reserve, so output must be claimable or delivered through a provably successful path.

5. pool emits pool update
   Chain: pool child chain -> swap root/catalog chain.
   Application: `pool -> swap`.
   Account: registered pool app.
   Action: send reserve/version/settled transaction update.
   Transmission: internal message.
   Bounce handling: update reject does not roll back finalized swap; update must be replayable/idempotent.
   Constraint: `SwapOperation::UpdatePool` must not be a user-forgeable entry.
   Risk and mitigation: user-callable update pool can forge price, reserve, and transaction; handler must only accept registered pool app source or remove the user operation surface.

## RemoveLiquidity

Target path: user removes LP. After burn, token0/token1 withdrawals become claimable and are not directly paid out.

1. User wallet chain
   Application: `pool` through swap router.
   Account: LP owner signer.
   Action: `PoolOperation::RemoveLiquidity { liquidity, min0, min1, to }`.
   Transmission: user operation routes to active pool.
   Constraint: validate owner LP share and min outputs.
   Risk and mitigation: do not burn before validation succeeds.

2. pool finalizes removal
   Chain: pool child chain.
   Application: `pool`.
   Account: pool app state.
   Action:
   - Create remove intent.
   - Burn LP share.
   - Update reserve.
   - Write settled remove-liquidity fact.
   - Create token0/token1 claimable withdrawal.
   Transmission: pool update message.
   Bounce handling: pool update reject does not roll back burn/reserve; update must be replayable/idempotent.
   Constraint: remove uniformly goes through claim; do not direct payout.
   Risk and mitigation: direct payout failure after burn loses user value; claimable withdrawal is the only safe convergence point.

3. duplicate/replay handling
   Chain: pool child chain.
   Application: `pool`.
   Account: pool app state.
   Action: repeated finalize or duplicate message returns existing result/claimable only.
   Transmission: idempotency by `intent_id`.
   Constraint: no double burn and no double claim.

## Claim

Target path: user actively claims swap output, remove withdrawal, add-liquidity refund, or excess. The chain does not provide `claim_all`; frontend organizes multiple claims. Current ABI does not yet provide claim operation/state; target protocol must add it.

1. Frontend reads claimables
   Application: product API / projection.
   Account: current wallet account.
   Action: display claimable records; UI may aggregate display, but on-chain details remain independent.
   Transmission: API read only.
   Constraint: one claimable is one on-chain accounting detail.
   Risk and mitigation: UI aggregation must not delete on-chain accounting details. Multiple claims cost more gas, but detailed accounting is better for audit and failure retry.

2. User submits claim
   Chain: pool child chain.
   Application: `pool`.
   Account: claim owner signer.
   Action: target ABI `PoolOperation::Claim { claim_id }`.
   Transmission: user operation.
   Constraint: validate owner, status, token, amount, and source intent.
   Risk and mitigation: arbitrary accounts must not be able to claim; frontend hiding is not protection.

3. pool executes delivery
   Chain: pool child chain.
   Application: `pool`.
   Account: pool app state.
   Action:
   - Success: mark claimed.
   - Recoverable failure: keep claimable and record bounded last_attempt metadata.
   - Duplicate claim: return claimed/existing status and do not pay again.
   Transmission: token/native transfer or token app message.
   Bounce handling: delivery message reject leaves claim claimable and records bounded failure metadata.
   Constraint: diagnostic/attempt metadata must have quota or TTL.
   Risk and mitigation: debug/attempt tables must not grow without bounds; non-business data must shed itself before it can harm business paths.

## Admin And Internal Entry Boundaries

- `SwapOperation::InitializeLiquidity`
  - Direct user calls must reject.
  - Accept only meme app authenticated caller + creator chain proof + pending initialization context.
- `SwapOperation::CreatePool`
  - Allowed as current user pool creation ABI.
  - Must mean create-with-initial-liquidity only.
  - Must reject zero-sided, one-sided, virtual, empty, or shell-only user pool creation.
  - Must create pending initial-liquidity intent and bind owner, tokens, amounts, slippage/deadline, and expected pool chain/app.
- `SwapOperation::UpdatePool`
  - User-forged calls are not allowed.
  - Accept only registered pool app/source chain/version.
- `SwapMessage::PoolCreated`
  - Must match pending pool intent.
  - Checking only `is_pool_chain` is insufficient.
- `PoolChainCreated` or shell receipt
  - Can only advance pending_shell -> shell_created/initializing.
  - Must not write product-level `PoolCreated` fact.
  - Must not make pool active/tradable.
- `SwapMessage::UserPoolCreated`
  - Is not a directly user-reachable path.
  - Must be deleted, collapsed, or kept only as an internal compatibility path bound to pending intent owner, amounts, and tokens.
  - Must not infer LP owner from message signer.
- `PoolMessage::FundSuccess` / `PoolMessage::FundFail`
  - Must match `intent_id + leg_id + expected token + expected source + expected amount`.
  - Must not update funds state by transfer id only.
- `PoolMessage::NewTransaction`
  - Is not a forgeable external fact entry.
  - Settled transaction must come from finalized pool execution.
- `PoolMessage::SetFeeTo` / `PoolMessage::SetFeeToSetter`
  - Must verify admin/operator intent.
  - Must not trust message payload operator only.
- `MemeOperation::TransferFromApplication` / `MemeOperation::InitializeLiquidity`
  - Must be driven by authorized app call or pending initialization/funding intent.
  - Message handler must check caller/source/pending record.
- `PoolMessage::RequestFund`
  - Token side must verify request source/authorization.
  - Pool side must verify expected source before accepting result.

## Temp Chain Decision

- Current AMM swap, add-liquidity, and remove-liquidity flows do not use per-operation temp chains.
- Rationale:
  - temp chains do not provide cross-chain atomicity
  - temp chains add open-chain fees for every operation
  - temp chains increase gas/funder coverage risk
  - temp chains require listener import and cleanup
  - temp chains add close-chain and permission-management complexity
  - temp chains move, but do not remove, the need for pending and claim state
- Future exception:
  - explicit escrow or isolation products may introduce temp chains after separate design review.

## Implementation Review Targets

- `meme/src/contract_inner/instantiation_handler.rs`
- `meme/src/contract_inner/handlers/message/liquidity_funded.rs`
- `swap/src/contract_inner/handlers/operation/initialize_liquidity.rs`
- `swap/src/contract_inner/handlers/message/initialize_liquidity.rs`
- `swap/src/contract_inner/handlers/create_pool.rs`
- `swap/src/contract_inner/handlers/message/create_pool.rs`
- `swap/src/contract_inner/handlers/message/pool_created.rs`
- `swap/src/contract_inner/handlers/operation/create_pool.rs`
- `swap/src/contract_inner/handlers/message/create_user_pool.rs`
- `swap/src/contract_inner/handlers/message/user_pool_created.rs`
- `swap/src/contract_inner/handlers/operation/update_pool.rs`
- `swap/src/contract_inner/handlers/message/update_pool.rs`
- `pool/src/contract_inner/handlers/operation/add_liquidity.rs`
- `pool/src/contract_inner/handlers/message/fund_success.rs`
- `pool/src/contract_inner/handlers/message/fund_fail.rs`
- `pool/src/contract_inner/handlers/message/add_liquidity.rs`
- `pool/src/contract_inner/handlers/operation/swap.rs`
- `pool/src/contract_inner/handlers/message/swap.rs`
- `pool/src/contract_inner/handlers/operation/remove_liquidity.rs`
- `pool/src/contract_inner/handlers/message/remove_liquidity.rs`
- `pool/src/contract_inner/handlers/message/new_transaction.rs`
- `pool/src/contract_inner/handlers/refund.rs`
- `pool/src/contract_inner/handlers/request_meme_fund.rs`
- `pool/src/contract_inner/handlers/transfer_meme_from_application.rs`
- `abi/src/swap/router.rs`
- `abi/src/swap/pool/mod.rs`
- `abi/src/meme.rs`

## Test Requirements

- Create meme native pool does not become active until pool child creation, real initial funding, and activation complete.
- Meme initial virtual liquidity creates virtual position fact without native reserve/TVL/claimable.
- User `CreatePool` with initial liquidity creates pool only after token validation succeeds.
- User `CreatePool` with initial liquidity rejects pending/failed duplicate pair.
- User-created pool requires real two-sided initial liquidity.
- Add-liquidity first leg success and second leg fail leaves no LP share and creates refund claimable.
- Add-liquidity duplicate success does not double-count funded amount.
- Add-liquidity duplicate finalization does not double-mint.
- Swap input funding failure leaves no reserve update and no settled swap.
- Swap slippage failure after input funding creates refund claimable and no settled swap.
- Swap success creates output claimable and settled swap fact exactly once.
- Remove-liquidity burn creates withdrawal claimables and cannot double burn.
- Duplicate claim does not double-pay.
- `PoolCreated` message that does not match pending intent is rejected.
- `FundSuccess/FundFail` with wrong token/source/amount/intent is rejected.
- User-called `UpdatePool`, `InitializeLiquidity`, and product-level `CreatePool` are rejected or unreachable.
- Admin fee messages require authorized operator proof.
