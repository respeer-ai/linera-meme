# Funding Implementation Plan

Type: Primitive
Audience: Coding assistants
Authority: High

## Execution Rule

Implement funding consistency through progressive, independently verifiable iterations. Do not batch unrelated paths and defer correctness to a final end-to-end pass.

Each iteration that introduces or changes an operation, message, callback, or receipt must include the path-local authorization, source-chain, authenticated-caller, intent, token, leg, and state validation required by that path. `FUND-013` is a final cross-path hardening sweep; it is not a license to defer required safety checks from earlier iterations.

## Iterations

### FUND-005 Iteration 0: Contract-path audit and executable baseline

Purpose: establish the executable baseline and exact implementation delta.

Required review gates:

1. Scope freeze
   - Output:
     - in-scope paths
     - out-of-scope paths
     - exact files/modules/contracts/frontend/debug surfaces included in the audit
   - Rule:
     - do not start the audit table before this gate is reviewed and accepted

2. Current implementation audit table
   - Output:
     - current path audit table covering file, handler, operation/message/callback/receipt, current state reads/writes, idempotency handling, reject/failure handling, and current economic side effects
   - Rule:
     - describe current behavior only; do not silently rewrite current behavior into target design language

3. Target validation matrix
   - Output:
     - target validation matrix covering source/auth/app/intent/leg/token/owner/amount/state validation, allowed transition, failure behavior, and required tests
   - Rule:
     - do not start implementation iterations after `FUND-005` before this gate is reviewed and accepted

4. Transition tables and unresolved-risk closure
   - Output:
     - handler-level transition tables required for later iterations, especially the message-driven create-pool and first-funding paths
     - explicit classification of stale receipt, wrong-state receipt, duplicate-safe no-op idempotency, abort, reject, and bounce handling
     - audited conclusion on whether current meme/pool payout can emit the success/fail/bounce receipts required for `Claim`
     - classification of open issues into:
       - accepted non-blocking risk
       - must-resolve-before-implementation ambiguity
   - Rule:
     - no later funding iteration may rely on implicit state-machine interpretation outside these reviewed tables

5. Characterization baseline and implementation handoff
   - Output:
     - focused characterization tests to lock current behavior where needed
     - explicit mapping from current unsafe behavior to the follow-up funding iteration that closes it
     - executable entry criteria for `FUND-006`
   - Rule:
     - `FUND-005` is complete only after this gate is reviewed and accepted

Minimal changes:

- Audit `pool`, `swap`, `meme`, `proxy`, frontend, and observability paths.
- Map operations, messages, state transitions, and tests.
- Produce a current implementation path audit table covering file, handler, operation/message, current state reads/writes, and current economic side effects.
- Produce a target path validation matrix covering operation/message/callback/receipt, required source/auth/app/intent/leg/token/owner/amount/state checks, allowed state transition, failure behavior, and required tests.
- Verify whether the current meme/pool payout path can produce the success, fail, or bounce receipts required to close meme `Claim` delivery.
- Add characterization tests only where current behavior must be locked.

Validation:

- Relevant contract tests compile and run under the project memory-limit rule.
- Current happy paths are locked before behavior changes.
- The audit table and validation matrix are committed before `FUND-006` implementation begins.
- No protocol behavior changes except test-only characterization.
- Execute `FUND-005` through the five review gates above. Do not batch the full iteration into one assistant delivery.

### FUND-006 Iteration 1: Lock public operation surface

Purpose: enforce user-reachable operation semantics.

Minimal changes:

- Treat direct wallet signing and user-contract `call_application` as user-reachable.
- Constrain public `CreatePool` to create-with-initial-liquidity.
- Reject empty, shell-only, one-sided, and virtual user pool creation.
- Accept only native and meme token identities; reject every other token kind until a concrete validation rule exists.
- Do not expose meme creator-chain identity as public `CreatePool` input. Validate user-started `CreatePool` token identity from authoritative chain facts. The only carried creator-chain-id field is `SwapOperation::InitializeLiquidity.token_0_creator_chain_id` for the synchronous `meme -> call_application(swap.InitializeLiquidity)` exception; do not propagate that field into swap messages or `PoolParameters`.

Validation:

- Invalid `CreatePool` forms reject without opening pool chain or active pair state in `swap` application state.
- Current valid Add Liquidity missing-pair path remains supported.

### FUND-007 Iteration 2: Split pool application creation from explicit initialization

Purpose: split pool application creation from first pool economic initialization while preserving distinct meme-initialization and user-CreatePool funding paths.

Minimal changes:

- The user-chain `SwapOperation::CreatePool` entry validates public input and sends the first internal continuation only; it does not create persisted create-pool workflow state. User CreatePool keeps the existing `UserPoolCreated -> PoolOperation::AddLiquidity` continuation and must not reuse meme-initialization bootstrap authority. Do not route user CreatePool through pool-side `InitializeLiquidity`.

- Define every account fact per hop. Use runtime chain facts such as `authenticated_account()` and `message_signer_account()` when they are the exact business fact required by that hop. Store or explicitly carry an account fact only when the current hop cannot derive the required business fact from chain state.
- `origin` means the initial operation account that started the workflow. Carry `origin` explicitly only on later messages that need the initial workflow starter for pool `creator`, `fee_to`, or share-owner semantics.
- Any explicitly carried fact must include a code comment explaining why the current hop cannot use chain facts, where the fact was previously verified, and how the current hop checks it against intent or chain state.
- Attach `.with_tracking()` by default in `ContractRuntimeContext::send_message` before funding or claim workflows depend on bounce handling.
- Bind every remaining `CreateUserPool`, internal `CreatePool`, `PoolCreated`, and `UserPoolCreated` message to the approved immutable carried facts plus authoritative chain-fact checks. Removing or merging old messages is allowed only as a refactor; any message that remains must validate the reviewed facts explicitly.
- Materialize a handler-level message transition table before code changes in this iteration. The table must specify which handler consumes each continuation, which immutable facts are checked from message payload, which chain facts are used directly at each hop, and which account facts are explicitly carried because the current hop cannot derive the required business fact from runtime chain state.
- Treat meme initialization as an internal-only bootstrap discriminator. It may authorize virtual-liquidity bootstrap semantics, but it must not be user-selectable input and must not be inferred from frontend payload. Path selection is explicit from the prior operation/message. `UserPoolCreated` starts the existing AddLiquidity flow for user-funded first liquidity; no user-pool-specific funding ABI is added and no pool-side `InitializeLiquidity` is added to the user CreatePool path.

Validation:

- Wrong app, chain, signer, pair, immutable-fact, and competing receipt tests pass for the reviewed continuations.
- Pool-shell reject/bounce does not activate pair state.
- Tests prove each continuation validates the carried immutable create-pool facts such as `token_0`, `token_1`, `amount_0`, `amount_1`, `to`, and `origin`.
- Tests prove the happy path still does not activate pool state too early.

### FUND-008 Iteration 3: Claim accounting and funds-exit foundation

Purpose: introduce the single funds-exit model before any workflow starts crediting owed value to it.

Minimal changes:

- Add claim-balance storage and accounting helpers.
- Add target `Claim` operation ABI.
- Implement native synchronous claim semantics.
- Implement meme `claiming_balances` state for asynchronous delivery.
- Keep refund, retry, protocol fee, remote liquidity, and excess as claim-balance meanings, not separate user operations.
- Use test fixtures or internal test helpers to seed claim balances for `Claim` tests; do not add a production debug operation or public ABI for this.
- Define concrete meme claim success/fail/bounce message enum variants and payload fields before implementation. The payload must include every field needed to validate source, authenticated caller, token, owner, amount, and claiming-balance state.

Validation:

- Claim-balance storage uses token-first, owner-second shape.
- Tests prove token claim balances update without duplicating token identity per owner.
- Native claim succeeds or leaves balance unchanged on abort.
- Meme claiming balance keeps the in-flight amount unavailable for another claim.
- Meme claim success/fail/bounce callbacks validate source, authenticated caller, token, owner, amount, and claiming-balance state.
- Tests prove malformed or stale meme claim callbacks cannot decrease `claiming_balances` or increase `claim_balances`.
- Success decreases claiming balance; fail/bounce moves the amount back to available claim balance.
- Pending forever remains safe and observable.

### FUND-009 Iteration 4: Existing-pool AddLiquidity two-leg pending

Purpose: make existing finalized-pool add liquidity safe using the established claim exit.

Minimal changes:

- Do not add `AddLiquidityIntent`.
- Track both legs before reserve update and LP mint.
- Credit explicit failed partial funding to claim balances.
- Preserve the limiting-side add-liquidity calculation and credit accepted-liquidity excess/refunds to claim balances instead of direct payout.
- Define concrete slippage fields and failure behavior before implementation. Existing-pool add liquidity must specify which min-amount fields are mandatory, how limiting-side accepted amounts are checked, and whether a post-custody slippage failure credits already-custodied funds to claim balances.

Validation:

- Partial funding failure leaves no reserve update or LP mint.
- Partial funding failure credits the already-custodied value to claim balances exactly once.
- Accepted-liquidity excess/refund is credited to claim balances exactly once.
- Wrong leg/source and wrong workflow state are rejected.
- Funding callbacks validate source, authenticated caller, token, owner, amount, leg, and pending intent before mutating custody, reserve, LP, or claim state.
- Credited values can exit through `Claim`.
- Happy path remains successful.

### FUND-010 Iteration 5: Pool visibility split

Purpose: make product visibility depend on finalized pool-side economic facts instead of app creation receipts.

Minimal changes:

- Treat finalized pool-side reserve/share facts as the product visibility boundary.
- Product/read-model rule: a protocol-existing pool without finalized reserve/share facts, including a zero-reserve shell, is not frontend-visible and is not a tradable/displayed market.

Validation:

- Product-visible pool lists exclude pools without finalized reserve/share facts.
- Zero-reserve shells are excluded from product-visible pool lists.

### FUND-011 Iteration 6: Swap output claim balances

Purpose: make swap outputs and refunds use claim balances.

Minimal changes:

- Do not add `SwapIntent`.
- Credit successful output to the claim balance for the output token and owner.
- Credit failed post-custody input to the claim balance for the input token and owner.

Validation:

- Slippage failure after input custody creates claim balance refund.
- Success creates output claim balance in the expected workflow state.
- Swap funding and finalization callbacks validate source, authenticated caller, token, owner, amount, intent, and current status before mutating reserves or claim balances.
- Credited values can exit through `Claim`.

### FUND-012 Iteration 7: Remove, protocol fee, remote-liquidity, and create-pool residual claim balances

Purpose: unify non-swap owed value into claim balances.

Minimal changes:

- Credit remove owed amounts to claim balances.
- Credit create-pool losing/residual refunds not already handled by AddLiquidity closure to claim balances.
- Credit protocol fee and remote-liquidity withdrawals through claim balances.

Validation:

- Burn/decrease cannot lose owed value.
- Remove/create-pool-residual/protocol-fee accounting is reachable only from expected workflow states.
- Remove, protocol-fee, remote-liquidity, and residual-refund callbacks validate source, authenticated caller, owner, token, amount, intent, and current status before mutating positions or claim balances.
- Credited values can exit through `Claim`.

### FUND-013 Iteration 8: Internal entry and application-caller hardening sweep

Purpose: audit and close residual unsafe internal/public boundaries after every earlier path has implemented its own required validation.

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

- Emit or preserve facts for intents, legs, claim balances, claiming balances, pool lifecycle, positions, reserves, and virtual positions.
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
- claim pending/fail/claiming-balance behavior
- activation stalled
- virtual liquidity
- projection consistency
