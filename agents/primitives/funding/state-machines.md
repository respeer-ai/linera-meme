# Funding State Machines

Type: Primitive
Audience: Coding assistants
Authority: High

## Rules

- A successful operation only proves the current transaction completed and outgoing messages were queued.
- A non-bounced tracked message is not whole-workflow success.
- `tracked + bouncing` is a one-hop reject receipt mechanism, not cross-chain atomic rollback.
- A target chain may delay message execution indefinitely or never execute the message.
- A permanently in-flight workflow is acceptable only if it remains safe, observable, and non-finalized.
- Linera core protocol executes an operation or accepted message once in chain history. Replay/catch-up does not cause application operations or messages to happen again as new protocol behavior.
- Application-level funding design must rely on that core reachability guarantee. If the exact same operation or message could be executed twice by the chain, application-level funds consistency would be impossible.
- Application state guards are still required for stale follow-ups, wrong source/caller, competing user operations, and distinct messages that target the same business workflow.
- Do not introduce a generic `Resume` operation. Any future recovery operation must be state-specific and justified against the core protocol execution model.

## User CreatePool With Initial Liquidity

Target path: user enters Add Liquidity for a missing pair. The frontend may submit `SwapOperation::CreatePool`; the product meaning is create-with-initial-liquidity.

### Entry

Chain: user current chain.
Application: `swap`.
Account: user-authorized operation entry, either direct wallet signature or user contract `call_application`.
Operation: `SwapOperation::CreatePool { token0, token1, amount0, amount1, to }`.

Constraints:

- `amount0 > 0 && amount1 > 0`.
- No virtual liquidity.
- No shell-only or empty pool creation.
- Token identity validation happens fail-fast at this user-started trusted entry.
- Existing pending or active pair rejects or returns the existing business state.

### PoolCreationIntent

Persistent chain: swap/catalog chain.
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

States:

- `pending_shell`
- `shell_message_sent`
- `funding_pending`
- `finalizing`
- `active`
- `failed`

Open issue: if the pool-shell target chain never executes the create message, the intent may remain `shell_message_sent` forever. It must not become active and must be visible as stalled. A future recovery or cancellation path is not part of the current design.

### Pool Shell

Persistent chain: pool child chain.
Created by: internal message from `swap`.
Consumed by: pool initial funding/finalization logic.

Pool-local state:

- `intent_id`
- pair identities
- `shell_created`

Open issue: if the pool shell is created but the shell receipt never reaches swap, swap catalog remains pending while the shell exists. The shell is not tradable and must not be exposed as active. A future reconciliation path is not part of the current design.

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

Swap consumes activation receipt and moves catalog pair to `Active`.

Open issue: if pool is finalized and LP is minted but activation receipt never reaches swap, the pool has economic state while catalog is not active. Do not recreate the pool or mint again. A future activation reconciliation path is not part of the current design.

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
