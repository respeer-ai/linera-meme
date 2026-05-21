# Funding State Machines

Type: Primitive
Audience: Coding assistants
Authority: High

## Rules

- A successful operation only proves the current transaction completed and outgoing messages were queued.
- Outgoing application messages must be tracked by default.
- `tracked + bouncing` is a one-hop reject receipt mechanism, not cross-chain atomic rollback.
- The reason to track messages is to let the sender chain observe destination-chain reject and converge sender-side workflow state safely.
- Receiving handlers must use `message_is_bouncing()` to distinguish normal delivery from a reject bounce.
- A non-bounced tracked message is not whole-workflow success.
- A target chain may delay message execution indefinitely or never execute the message.
- A permanently in-flight workflow is acceptable only if it remains safe, observable, and non-finalized.
- Linera core protocol executes an operation or accepted message once in chain history. Replay/catch-up does not cause application operations or messages to happen again as new protocol behavior.
- Application-level funding design must rely on that core reachability guarantee. If the exact same operation or message could be executed twice by the chain, application-level funds consistency would be impossible.
- Application state guards are still required for stale follow-ups, wrong source/caller, competing user operations, and distinct messages that target the same business workflow.
- Do not introduce a generic `Resume` operation. Any later recovery operation must be state-specific and justified against the core protocol execution model.

## User CreatePool With Initial Liquidity

Target path: user enters Add Liquidity for a missing pair. The frontend may submit `SwapOperation::CreatePool`; the product meaning is create-with-initial-liquidity.

This is not the meme-native initialization path. Meme-native initialization uses `SwapOperation::InitializeLiquidity` and may include virtual native reference semantics. Public user `CreatePool` must not create virtual liquidity.

### Entry

Chain: user current chain.
Application: `swap`.
Account: user-authorized operation entry, either direct wallet signature or user contract `call_application`.
Operation: `SwapOperation::CreatePool { token0, token1, amount0, amount1, to }`.
Public input does not include token creator-chain identity.

Constraints:

- `amount0 > 0 && amount1 > 0`.
- Validation at this entry may use only facts available on the user current chain or through safe user-started application calls on that same chain.
- Active-pair truth lives on the swap creator-chain replica and must not be inferred from the user-chain `swap` replica.
- No virtual liquidity.
- No shell-only or empty pool creation.
- Both tokens must be real, valid token identities before any pool chain is opened.
- Token identity validation happens fail-fast at this user-started trusted entry.
- Supported token kinds are native and meme tokens only.
- Native token identity is built in.
- Meme token identity is validated by calling the meme token application for creator-chain identity from this user-started path.
- Token creator-chain identity is never frontend-supplied input. User-started `CreatePool` validates meme token identity from authoritative chain facts before opening a pool chain. The only carried creator-chain-id field is `SwapOperation::InitializeLiquidity.token_0_creator_chain_id` for the synchronous `meme -> call_application(swap.InitializeLiquidity)` exception; swap messages and `PoolParameters` must not carry token creator-chain-id fields.
- Any other token kind is rejected.
- Active pair creation must not create another pool.

### Pool Application Creation

Persistent chain: swap-controlled create path and pool child chain.

Purpose:

- create the pool child chain
- create the pool application
- establish a protocol object that can receive real funding

Rules:

- Pool application creation does not finalize reserve, LP share supply, or active-pool usability.
- Pool application creation does not by itself make the pool usable for ordinary swap or remove-liquidity flows.
- `PoolCreated` is an app-created receipt only.
- The target design does not persist a create-pool intent object for this phase.

### FinalizeInitialization

Persistent chain: pool chain.

Purpose:

- finalize the first accepted real funding of an uninitialized pool
- write the initial reserve/share economic state
- make the pool usable for ordinary paths

Rules:

- Pool instantiate creates only base state and leaves the pool uninitialized.
- `FinalizeInitialization` is the only boundary that may:
  - write initial reserve state
  - write initial LP/share supply
  - update `k_last` for initialized economics
  - set the pool-side `initialized` fact
- If required real funding has not yet entered the pool application, `FinalizeInitialization` must reject.
- If initialization fails before finalization, only real assets that actually entered protocol control may become claimable. Virtual value never becomes claimable.

Flow:

1. Validate public create-pool input on the user-reachable swap operation entry.
2. Create the pool child chain and pool application.
3. Leave the new pool uninitialized at instantiate time.
4. Kick off the first real two-sided funding path into the pool application.
5. When the required first funding has entered the pool application, execute `FinalizeInitialization`.
6. Only after `FinalizeInitialization` is complete is the pool usable for ordinary swap, remove-liquidity, and existing-pool add-liquidity flows.

## Meme Native Pool Initialization

Target path: create a meme token and initialize its first pool.

Flow:

1. Meme-side initialization prepares meme initial-liquidity allowance for swap.
2. When virtual initial liquidity is disabled, native initial-liquidity value is also transferred into swap control before swap initialization starts.
3. Swap creates the pool child chain and pool application.
4. Pool instantiate leaves the pool uninitialized and does not write final reserve/share economics.
5. Real assets are transferred from swap / meme into the pool application.
6. `FinalizeInitialization` writes final initialized reserve/share state.
7. Only after `FinalizeInitialization` is complete is the pool usable for ordinary paths.

Rules:

- Meme-side real token value is always real funding.
- Virtual initial liquidity is an economic-model parameter only.
- Virtual value is never claimable, withdrawable, or removable.
- `PoolCreated` is app-created only and is not the final initialization boundary.

## Existing AddLiquidity

Persistent chain: pool chain.

Rules:

- Ordinary existing-pool add liquidity requires `initialized == true`.
- If `initialized == false`, the first accepted two-sided real funding path is not ordinary add liquidity; it must converge through `FinalizeInitialization`.
- Both legs must be funded before reserve update, LP mint, or settled add-liquidity fact for an initialized pool.
- Funding callbacks must validate source, expected leg, and current allowed path.
- Explicit failed opposite leg moves already funded real value to claim balances.
- If both legs are funded but the accepted-liquidity calculation rejects finalization, the funded real value is credited to claim balances.
- Forever-pending opposite leg remains stalled; there is no timeout refund.

## Swap

Persistent chain: pool chain.

Rules:

- Ordinary swap requires `initialized == true`.
- Input funding must be represented before economics finalize.
- Slippage or check failure after input custody credits input back to claim balances.
- Successful swap updates reserves and credits output to claim balances.
- Output direct payout is not the funds-closure boundary.
- The target design does not persist a swap intent object.

## RemoveLiquidity

Persistent chain: pool chain.

Rules:

- Ordinary remove liquidity requires `initialized == true`.
- Burn, reserve decrease, and owed-value calculation happen before user funds exit.
- Owed output value is credited to claim balances instead of being treated as protocol completion only after direct remote payout.
- The target design does not persist a remove-liquidity intent object.
