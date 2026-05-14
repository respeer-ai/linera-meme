# Funding Implementation Plan

Type: Primitive
Audience: Coding assistants
Authority: High

## Execution Rule

Implement funding consistency through progressive, independently verifiable iterations. Do not batch unrelated paths and defer correctness to a final end-to-end pass.

## Iterations

### FUND-005 Iteration 0: Contract-path audit and executable baseline

Purpose: establish the executable baseline and exact implementation delta.

Minimal changes:

- Audit `pool`, `swap`, `meme`, `proxy`, frontend, and observability paths.
- Map operations, messages, state transitions, and tests.
- Add characterization tests only where current behavior must be locked.

Validation:

- Relevant contract tests compile and run under the project memory-limit rule.
- Current happy paths are locked before behavior changes.
- No protocol behavior changes except test-only characterization.

### FUND-006 Iteration 1: Lock public operation surface

Purpose: enforce user-reachable operation semantics.

Minimal changes:

- Treat direct wallet signing and user-contract `call_application` as user-reachable.
- Constrain public `CreatePool` to create-with-initial-liquidity.
- Reject empty, shell-only, one-sided, and virtual user pool creation.

Validation:

- Invalid `CreatePool` forms reject without opening pool chain or active catalog state.
- Current valid Add Liquidity missing-pair path remains supported.

### FUND-007 Iteration 2: Intent-bind user pool creation

Purpose: remove unsafe owner/payload reconstruction.

Minimal changes:

- Introduce `PoolCreationIntent`.
- Collapse or strictly bind `CreateUserPool`, internal `CreatePool`, and `UserPoolCreated`.
- Stop deriving owner/recipient/token/amount from message signer after intent creation.

Validation:

- Wrong app, chain, signer, pair, stale intent, and competing receipt tests pass.
- Pending shell does not become active.

### FUND-008 Iteration 3: Existing-pool AddLiquidity two-leg pending

Purpose: make existing active-pool add liquidity safe.

Minimal changes:

- Add `AddLiquidityIntent`.
- Track both legs before reserve update and LP mint.
- Credit explicit failed partial funding to claim balances.

Validation:

- Partial funding failure leaves no reserve update or LP mint.
- Wrong leg/source and wrong workflow state are rejected.
- Happy path remains successful.

### FUND-009 Iteration 4: Initial-liquidity convergence

Purpose: route user pool creation initial liquidity through the same two-leg closure.

Minimal changes:

- Add `PoolInitialLiquidityIntent`.
- Finalize pool reserve/LP only after both real legs are funded.
- Activate swap catalog only after valid activation receipt.

Validation:

- Initial downstream failure does not active/mint/finalize incorrectly.
- Successful path activates only after required state transitions.

### FUND-010 Iteration 5: Swap output claim balances

Purpose: make swap outputs and refunds use claim balances.

Minimal changes:

- Add or reuse `SwapIntent`.
- Credit successful output to the claim balance for the output token and owner.
- Credit failed post-custody input to the claim balance for the input token and owner.

Validation:

- Slippage failure after input custody creates claim balance refund.
- Success creates output claim balance in the expected workflow state.

### FUND-011 Iteration 6: Remove, excess, protocol fee, and remote-liquidity claim balances

Purpose: unify non-swap owed value into claim balances.

Minimal changes:

- Credit remove owed amounts to claim balances.
- Credit add-liquidity excess/refunds to claim balances.
- Credit protocol fee and remote-liquidity withdrawals through claim balances.

Validation:

- Burn/decrease cannot lose owed value.
- Remove/excess/refund/protocol-fee accounting is reachable only from expected workflow states.

### FUND-012 Iteration 7: Claim operation and delivery attempts

Purpose: implement the single user funds-exit operation.

Minimal changes:

- Add `Claim` operation.
- Implement native synchronous claim semantics.
- Implement meme pending delivery attempt state.

Validation:

- Native claim succeeds or leaves balance unchanged on abort.
- Meme pending delivery keeps the frozen amount unavailable for another claim.
- Fail/bounce restores available balance.
- Pending forever remains safe and observable.

### FUND-013 Iteration 8: Internal entry and application-caller hardening

Purpose: close unsafe internal/public boundaries.

Minimal changes:

- Reject direct user access to internal operations.
- Validate authenticated caller, source chain, expected app, expected leg, and pending intent.
- Ensure user-contract `call_application` cannot bypass operation constraints.

Validation:

- Forged callbacks and direct internal calls reject.
- Valid meme initialization, funding callbacks, and claim callbacks still work.

### FUND-014 Iteration 9: Projection facts and product compatibility

Purpose: align product reads with protocol facts.

Minimal changes:

- Emit or preserve facts for intents, legs, claim balances, delivery attempts, pool lifecycle, positions, reserves, and virtual positions.
- Update observability projections and product APIs.

Validation:

- Claim lists, positions, TVL, APR inputs, transactions, and diagnostics come from projection.
- No live query is required for product accounting truth.

### FUND-004 Final regression suite

Purpose: cross-path regression after independent iterations pass.

Validation:

- create pool partial failure
- add liquidity partial failure
- swap output/refund
- remove owed
- claim pending/fail/frozen-balance behavior
- activation stalled
- virtual liquidity
- projection consistency
