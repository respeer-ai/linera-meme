# Funding Module Responsibilities

Type: Primitive
Audience: Coding assistants
Authority: High

## swap

Responsibilities:

- Own pair/pool registry state inside `swap` application state.
- Own `PoolCreationIntent`.
- Accept user `SwapOperation::CreatePool` only as create-with-initial-liquidity.
- Track pending, failed, and active pair states.
- Consume pool shell and activation receipts.

Non-responsibilities:

- Do not own final pool reserve accounting.
- Do not infer LP owner, token identity, or amount from later messages once an intent exists.

## pool

Responsibilities:

- Own reserves, LP accounting, positions, claim balances, and claiming balances.
- Own `PoolInitialLiquidityIntent`, `AddLiquidityIntent`, `SwapIntent`, and `RemoveLiquidityIntent`.
- Finalize reserve and LP state only after required inputs are funded.
- Credit claim balances for owed output, refund, excess, protocol fee, and remote liquidity.
- Execute `Claim`.

Non-responsibilities:

- Derive tradability from finalized pool state. Do not expose pending or failed shell pools as tradable.
- Do not direct-payout as the only funds-closure mechanism for asynchronous paths.

## meme

Responsibilities:

- Own meme token balances and transfer semantics.
- Provide creator-chain identity only for the confirmed synchronous `meme -> call_application(swap.InitializeLiquidity)` exception. The carried field is `SwapOperation::InitializeLiquidity.token_0_creator_chain_id`; it exists because swap cannot query the meme app during the same call frame without a Linera reentrant-call rejection. Do not propagate this field into swap messages or `PoolParameters`.
- `FUND-005` must audit the current payout/transfer callback support.
- `FUND-008` must add any missing claim delivery success/fail/bounce messages required by the `Claim` state machine before meme token `Claim` is considered implemented.

Non-responsibilities:

- Do not define swap/pool economic finality.
- Do not require swap to call back into meme from `meme -> swap` initialization paths.

## proxy

Responsibilities:

- Coordinate product-facing create meme flows.
- Preserve protocol facts needed for meme native pool initialization.

Non-responsibilities:

- Do not become protocol truth for pool accounting.

## frontend

Responsibilities:

- Submit operations.
- Read product data from projection/API.
- Organize multiple user claims when needed.

Non-responsibilities:

- Do not invent protocol state.
- Do not derive claim lists from live chain query.
- Do not rely on frontend-only checks for security.

## observability

Responsibilities:

- Parse block facts.
- Derive product projections for pools, tokens, positions, claim balances, pending/stalled workflows, transactions, candles, TVL, and APR inputs.
- Provide paginated product and diagnostic APIs.

Non-responsibilities:

- Do not consume or mutate protocol state.
- Do not use live query as product accounting truth.
