# Funding State Machines

Type: Primitive
Audience: Coding assistants
Authority: High

## Rules

- A successful operation only proves the current transaction completed and outgoing messages were queued.
- Outgoing application messages should be tracked by default.
- `tracked + bouncing` is a one-hop reject receipt mechanism, not cross-chain atomic rollback.
- The reason to track messages is to let the sender chain observe destination-chain reject and converge sender-side workflow state safely.
- Receiving handlers must use `message_is_bouncing()` to distinguish normal delivery from a reject bounce.
- A non-bounced tracked message is not whole-workflow success.
- A target chain may delay message execution indefinitely or never execute the message.
- A permanently in-flight workflow is acceptable only if it remains safe, observable, and non-finalized.
- Linera core protocol executes an operation or accepted message once in chain history. Replay/catch-up does not cause application operations or messages to happen again as new protocol behavior.
- Application-level funding design must rely on that core reachability guarantee. If the exact same operation or message could be executed twice by the chain, application-level funds consistency would be impossible.
- Application state guards are still required for stale follow-ups, wrong source/caller, competing user operations, and distinct messages that target the same business workflow.
- Do not introduce a generic `Resume` operation. Any future recovery operation must be state-specific and justified against the core protocol execution model.

## User CreatePool With Initial Liquidity

Target path: user enters Add Liquidity for a missing pair. The frontend may submit `SwapOperation::CreatePool`; the product meaning is create-with-initial-liquidity.

This is not the meme-native initialization path. Meme-native initialization uses `SwapOperation::InitializeLiquidity` and may create a native pool with virtual native reference semantics. Public user `CreatePool` must not create virtual liquidity.

### Entry

Chain: user current chain.
Application: `swap`.
Account: user-authorized operation entry, either direct wallet signature or user contract `call_application`.
Operation: `SwapOperation::CreatePool { token0, token1, amount0, amount1, to }`.

Constraints:

- `amount0 > 0 && amount1 > 0`.
- No virtual liquidity.
- No shell-only or empty pool creation.
- Both tokens must be real, valid token identities before any pool chain is opened.
- Token identity validation happens fail-fast at this user-started trusted entry.
- Supported token kinds are native and meme tokens only.
- Native token identity is built in.
- Meme token identity is validated by calling the meme token application for creator-chain identity from this user-started path.
- Any other token kind is rejected.
- Pending pair contention uses first-funded-wins semantics.
- Active pair creation must not create another pool.

### PoolCreationIntent

Persistent chain: swap chain.
Created by: `swap` operation handler.
Consumed by: `swap` shell receipt handler and activation receipt handler.

Required fields:

- `intent_id`
- `owner_account`
- `to_account`
- `pair_key`
- `token0_identity`
- `token1_identity`
- `amount0`
- `amount1`
- `min0` / `min1` when applicable
- `status`
- `expected_pool_chain`
- `expected_pool_application`
- `created_at_event`
- `last_update_event`
- `failure_reason`

`intent_id` uniqueness:

- The application that stores the workflow intent state allocates the id from its own persistent local state before sending any workflow message.
- For user pool creation, the canonical `PoolCreationIntent` is stored in `swap` application state on the swap chain, so the `swap` application allocates the id there.
- The canonical id is `(swap_application_id, intent_seq)` or an equivalent typed value with the same uniqueness domain.
- `intent_seq` is a monotonic counter stored in `swap` application state and incremented once per newly accepted workflow intent.
- Do not derive uniqueness from token pair, owner, timestamp, message delivery order, or frontend-provided data.
- Internal messages and receipts carry `intent_id`; handlers load the intent by id and verify expected pair, owner, source chain, pool chain, pool application, and current status.
- The pool chain may store pool-local workflow state that references the same `intent_id`, but it does not allocate the canonical pool-creation id.
- Cross-chain storage is not shared. Consistency comes from message-carried ids plus local validation of source chain, authenticated caller/application, expected pool chain/application, pair, and status on the receiving chain.

States:

- `pending_shell`
- `shell_message_sent`
- `funding_pending`
- `finalizing`
- `active`
- `failed`
- `cleaned_up`

Open issue: if the pool-shell target chain never executes the create message, the intent may remain `shell_message_sent` forever. It must not become active in `swap` application state and must be visible as stalled. A future recovery or cancellation path is not part of the current design.

Rules:

- If multiple pending intents target the same pair, the first intent that reaches the required funded terminal state wins.
- Losing intents must transition to `failed` or `cleaned_up`.
- Any losing intent value already in custody must be credited to claim balances.
- A losing opened shell chain/application must not become a second active pool and must not be reusable by a later create attempt.
- Terminal truth lives in the intent state. Do not add a separate pool-created flag that can disagree with intent status.
- If cleanup is possible, the router/swap application may close a losing shell chain only when it is executing on that chain, the chain grants it `close_chain` permission, and shell cleanup is already complete. Linera `close_chain()` only marks the chain closed; it does not transfer remaining chain balance or application custody.

### Pool Shell

Persistent chain: pool child chain.
Created by: internal message from `swap`.
Consumed by: pool initial funding/finalization logic.

Pool-local state:

- `intent_id`
- pair identities
- `shell_created`
- finalized/economic-ready state from which tradability is derived; do not store a second independent `tradable` truth that can diverge from pool state

If the shell exists before original creator funding finalizes, another user may call `AddLiquidity` on the shell. That operation is allowed, but it must enter the same two-leg funding/finalization gate:

- It does not create another `PoolCreationIntent`; it creates only a pool-local `AddLiquidityIntent`.
- If it is the first workflow to finalize, it defines the initial reserves and wins pool creation.
- The activation receipt binds to the existing shell/pair and the single swap-side `PoolCreationIntent`.
- The winning owner and LP recipient are taken from the finalized funding workflow, not from the original shell creator.
- If the pool has already finalized by the time another workflow's funds arrive, that workflow is no longer initial funding. Its amounts must be handled as normal add liquidity against the current reserves.
- For normal add liquidity, a one-side-short case does not fail the whole workflow. The accepted liquidity amount is computed from the limiting side, and excess from the other side is credited to claim balances.
- No workflow may write reserves or mint LP shares until both required token legs are funded and the workflow is the valid finalization candidate for the current pool state.

Open issue: if the pool shell is created but the shell receipt never reaches the swap chain, `swap` application state remains pending while the shell exists. The shell has no finalized reserves and must not be exposed as active. A future reconciliation path is not part of the current design.

### Failed Shell Cleanup

Persistent chain: pool child chain.
Created by: losing or failed pool-creation workflow.
Consumed by: pool cleanup/finalization logic before optional chain close.

Rules:

- A failed shell is permanently non-economic: it must not become active, must not finalize reserves, and must not mint LP shares.
- Failed-shell `AddLiquidity` should reject before requesting funds whenever possible.
- If funds are nevertheless delivered to a failed shell, they are application/protocol custody on that shell, not LP reserve and not liquidity owned by the sender.
- User-owned value already custodied by a valid losing workflow is credited to claim balances before cleanup.
- Close is last. The shell chain may be closed only after cleanup resolves all application-level custody. Linera `close_chain()` only sets the chain closed and causes future incoming messages to be rejected; it does not transfer or refund remaining balance.

### PoolInitialLiquidityIntent

Persistent chain: pool chain.
Created by: pool when authorized by swap intent.
Consumed by: token funding callbacks and pool finalization logic.

Required fields:

- `intent_id`
- `owner_account`
- `to_account`
- `token0_identity`
- `token1_identity`
- `amount0`
- `amount1`
- `leg0_status`
- `leg1_status`
- `status`

States:

- `funding_pending`
- `partially_funded`
- `funded`
- `finalized`
- `failed`

Rules:

- Do not write reserves before both real token legs are funded.
- Do not mint LP share before both real token legs are funded.
- A funded leg whose opposite leg has an explicit fail/bounce is credited into claim balances.
- A funded leg whose opposite leg is only pending remains in custody and must be visible as stalled; there is no timeout refund.

Open issue: one funded leg and one forever-pending leg cannot be safely auto-refunded without a proof that the missing leg will not later execute.

### Activation

After both legs are funded, pool finalizes:

- `reserve0 += amount0`
- `reserve1 += amount1`
- mint LP position to `to_account`
- mark pool-side intent `finalized`
- emit activation receipt to swap

Swap consumes activation receipt and moves the pair to active in `swap` application state.

Open issue: if pool is finalized and LP is minted but activation receipt never reaches the swap chain, the pool has economic state while `swap` application state is not active. Do not recreate the pool or mint again. A future activation reconciliation path is not part of the current design.

## Meme Native Pool Initialization

Target path: create a meme token and initialize its native pool.

Rules:

- Meme existence is guaranteed by meme app creation.
- Swap must not call back into meme for validation from the `meme -> swap` initialization path.
- Verify authenticated caller, source chain, and initialization intent binding.
- Real meme initial liquidity and virtual native reference are distinct.
- Virtual native reference is not native reserve, TVL, claimable balance, or payable balance.
- Emit virtual position facts separately from normal add-liquidity facts.

## Existing AddLiquidity

Persistent chain: pool chain.
Intent: `AddLiquidityIntent`.

Required fields:

- `intent_id`
- `owner_account`
- `to_account`
- token identities
- expected amounts
- leg statuses
- status

Rules:

- Both legs must be funded before reserve update, LP mint, or settled add-liquidity fact.
- Funding callbacks must validate source, expected leg, and current workflow state.
- Explicit failed opposite leg moves already funded custody value to claim balances.
- Forever-pending opposite leg remains stalled; there is no timeout refund.

## Swap

Persistent chain: pool chain.
Intent: `SwapIntent`.

Rules:

- Input funding must be represented before economics finalize.
- Slippage or check failure after input custody credits input back to claim balances.
- Successful swap updates reserves and credits output to claim balances.
- Output direct payout is not the funds-closure boundary.
- Finalization must be reachable only from the expected workflow state.

## RemoveLiquidity

Persistent chain: pool chain.
Intent: `RemoveLiquidityIntent`.

Rules:

- Burn/decrease position and owed amount accounting must be one safe state transition.
- Owed token amounts are credited to claim balances.
- Direct payout is not required for remove completion.
- User may never claim; claim balances persist as economic state.

## Claim

The full claim state machine is defined in `agents/primitives/funding/claim.md`.

`Claim` is a target protocol addition. The current pool contract does not yet implement `PoolOperation::Claim`, claim balances, or claiming balances.
