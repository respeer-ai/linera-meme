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
- Keep `ContractRuntimeContext::send_message` authenticated by default and require each outgoing message to pass an explicit `tracking` flag. Enable tracking only for paths whose receiving handler implements `message_is_bouncing()` handling and tests.
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
- Success decreases claiming balance.
- Transfer failure before payout, or bounced `TransferFromApplicationWithReceipt` before payout, restores available claim balance.
- A rejected completed `TransferFromApplicationReceipt` is an observability-only abnormal settlement state: it does not restore claimable balance, does not retry, and leaves the amount locked in claiming balance.
- Pending forever remains safe and observable.

### FUND-009 Iteration 4: Existing-pool AddLiquidity two-leg pending

Purpose: make existing finalized-pool add liquidity safe using the established claim exit.

Minimal changes:

- Do not add `AddLiquidityIntent`.
- Migrate AddLiquidity away from persisted `FundRequest`: AddLiquidity must not create, read, or update persistent `FundRequest` state.
- Keep the funding-request concept as message-carried `FundRequest`, not as pool state. `FundRequest` carries `from`, `token`, `amount_in`, `amount_out_min`, `counterparty_token`, `counterparty_amount_in`, `counterparty_amount_out_min`, `to`, `block_timestamp`, and `fund_type`.
- AddLiquidity uses `RequestFund { prev, request, next }` and `FundResult { prev, request, next, result }` as the non-persistent replacement for `RequestFund/FundSuccess/FundFail { transfer_id }`.
- `prev` is the already-custodied previous funding request, `request` is the current leg, and `next` is the next funding request to start after the current request succeeds. A failed current result credits `prev` when present and does not continue `next`.
- Do not add `AddLiquidityContext`, `AddLiquidityLeg`, or ABI fields named after pool-internal token positions such as `Token0` or `Token1`.
- `FundResult` must be accepted only when it is authenticated from the expected token creator chain and from the current pool application replica on that chain. The handler must validate `message_origin_chain_id`, `message_caller_account`, and `message_signer_account` before using the result.
- `FundRequest` is now the canonical message-carried funding fact; it is not persisted in pool state.
- Track both AddLiquidity funding requests with message-carried facts before reserve update and LP mint.
- Credit explicit failed partial funding to claim balances.
- Preserve the limiting-side add-liquidity calculation and credit accepted-liquidity excess/refunds to claim balances instead of direct payout.
- Define concrete slippage fields and failure behavior before implementation. Existing-pool add liquidity must specify which min-amount fields are mandatory, how limiting-side accepted amounts are checked, and whether a post-custody slippage failure credits already-custodied funds to claim balances.

Atomic implementation steps:

- A1: Update funding docs and task routing with the `FundRequest` design.
- A2: Add ABI types and messages: `FundType`, `FundRequest`, `RequestFund`, and `FundResult`; keep legacy `RequestFund`, `FundSuccess`, and `FundFail`.
- A3: Add handler skeletons for `RequestFund` and `FundResult` and register them in `HandlerFactory` without changing AddLiquidity behavior.
- A4: Move `PoolOperation::AddLiquidity` to the `FundRequest` happy path, including `TransferToCaller`, source validation, successor continuation, and final `PoolMessage::AddLiquidity`; do not add claim credit in this step.
- A5: Remove AddLiquidity handling from the legacy persisted-`FundRequest` result path while leaving that path for Swap and other unmigrated workflows.
- A6.0: Change the message envelope from successor-only to `prev/request/next`.
- A6.1: Credit `prev` on failed `FundResult` for AddLiquidity.
- A6.2: Credit both legs on final AddLiquidity calculation failure after custody.
- A6.3: Credit accepted-liquidity excess/refund to claim balances instead of direct payout.
- A6.4: Refactor AddLiquidity settlement handler and reduce known reject paths.
- A6.5: Move successful fungible custody from the origin-chain pool app replica to the pool creator-chain pool app using `TransferFromApplicationWithReceipt`; do not finalize AddLiquidity before custody receipts complete.
- A6.6: Add the pool-side custody receipt continuation that either credits failed custody or triggers final `PoolMessage::AddLiquidity` only after all required custody transfers complete.
- A7: Add and run focused tests, then run the full memory-limited `cargo test -j 1`.

Validation:

- Partial funding failure leaves no reserve update or LP mint.
- Partial funding failure credits the already-custodied value to claim balances exactly once.
- Accepted-liquidity excess/refund is credited to claim balances exactly once.
- Wrong source, wrong token, wrong request facts, wrong successor facts, and wrong workflow state are rejected.
- Funding result handlers validate source chain, authenticated caller application, message signer, token, owner, amount, request facts, and successor facts before mutating custody, reserve, LP, or claim state.
- Remove and protocol-fee credited values can exit through `Claim`; duplicate CreatePool open-chain budget exits by direct native refund in the duplicate handler.
- Happy path remains successful.

### FUND-010 Iteration 5: Pool visibility split

Purpose: make product visibility depend on finalized pool-side economic facts instead of app creation receipts.

Minimal changes:

- Do not change `swap.pools` service query into an observability or product-visible-only API. It remains the swap contract service view over protocol pool catalog state.
- A pool may exist in protocol catalog after pool application creation and before finalized reserve/share facts exist.
- Treat finalized pool-side reserve/share facts as the product visibility boundary.
- Product/read-model rule: a protocol-existing pool without finalized reserve/share facts, including a zero-reserve shell, is not frontend-visible and is not a tradable/displayed market.
- Keep `AddLiquidity` available for user CreatePool first funding; do not reject it merely because the pool is not finalized.
- Keep normal `Swap` and `RemoveLiquidity` rejected by pool-side finalized-facts guards.

Validation:

- Product-visible pool lists exclude pools without finalized reserve/share facts.
- Zero-reserve shells are excluded from product-visible pool lists.
- `swap.pools` remains protocol catalog and can expose unfinalized pool entries with null reserves.
- Normal `Swap` and `RemoveLiquidity` reject on unfinalized pools.
- User CreatePool first funding through `UserPoolCreated -> PoolOperation::AddLiquidity` remains supported.

### FUND-011 Iteration 6: Swap message-carried funding and claim settlement

Purpose: migrate Swap away from persisted funding state, make swap output/refund settlement use claim balances, and promote the message-carried funding ABI to the canonical funding protocol.

Minimal changes:

- Do not add `SwapIntent`.
- Migrate meme-input Swap from persisted `FundRequest` state to message-carried funding facts.
- Keep native-input Swap direct funding to the pool creator-chain pool application account, then settle through `PoolMessage::Swap`.
- Remove the legacy persisted funding protocol after Swap no longer uses it: old `FundRequest`, `FundStatus`, `RequestFund`, `FundSuccess`, `FundFail`, `fund_requests` state/query/interface methods, and legacy handlers.
- The message-carried funding protocol uses canonical names: `FundRequest`, `RequestFund`, and `FundResult`
- The final canonical `FundRequest` is a message-carried fact only. It must not include persisted-state fields such as `id`, `status`, `error`, `prev_request`, or `next_request`.
- Credit successful swap output to the claim balance for the output token and owner.
- Credit failed post-custody swap input to the claim balance for the input token and owner.
- Do not use `RefundHandler` as the final swap refund path after custody. Swap refund closure uses claim balances.

Swap flow:

- Meme input:
  - `PoolOperation::Swap`
  - `PoolMessage::RequestFund { prev: None, request, next: None }`
  - token creator-chain `TransferToCaller`
  - `PoolMessage::FundResult { result }`
  - on success, move meme custody from the origin-chain pool application replica to the pool creator-chain pool application
  - pool creator-chain `PoolMessage::Swap`
  - reserve/transaction update
  - output claim-balance credit
- Native input:
  - `PoolOperation::Swap`
  - native transfer into the pool creator-chain pool application
  - pool creator-chain `PoolMessage::Swap`
  - reserve/transaction update
  - output claim-balance credit

Validation:

- Tests prove meme-input Swap does not create, read, or update persisted `FundRequest` state.
- Tests prove failed meme funding does not update reserves and does not credit an input refund when no custody was acquired.
- Tests prove slippage/check failure after input custody credits the input claim-balance refund.
- Tests prove successful output is credited exactly once.
- Tests prove swap remains rejected before finalized reserve/share facts exist.
- Funding request and result handlers validate source chain, authenticated caller application, message signer, token, owner, amount, request facts, and successor facts before mutating custody, reserve, transaction, or claim state.
- Tests prove credited values can exit through `Claim`.

Atomic implementation steps:

- A1 (done): Update funding docs and task routing with the Swap migration, legacy persisted funding removal, and `Ext` canonicalization plan.
- A2 (done): Move meme-input `PoolOperation::Swap` to message-carried funding while keeping temporary `Ext` names.
- A3 (done): Extend the funding result handler to support `FundType::Swap`; successful meme custody continues to pool creator-chain swap settlement, and failed meme funding terminates without reserve or claim mutation.
- A4 (done): Change `PoolMessage::Swap` settlement so successful outputs are credited to claim balances and post-custody settlement failures credit input refunds to claim balances.
- A5 (done): Add focused Swap tests for no persisted request creation, funding failure, successful settlement, output claim credit, post-custody refund claim credit, and wrong source/signer/token rejection.
- A6 (done): Remove the legacy persisted funding implementation: old state, query, interface methods, ABI messages, handlers, and obsolete tests.
- A7 (done): Rename the remaining message-carried funding protocol from `Ext` names to canonical names.
- A8 (done): Run targeted tests and the full memory-limited `cargo test -j 1`.

### FUND-012 Iteration 7: Remove/protocol-fee claim balances and duplicate create-pool direct refund

Purpose: settle remove-liquidity and protocol-fee owed value through claim balances, and handle duplicate user CreatePool open-chain budget with a direct native refund on the swap creator chain.

Minimal changes:

- Credit remove owed amounts to claim balances.
- If user CreatePool loses because the canonical pool already exists, refund the open-chain fee budget directly from the swap creator-chain balance to the message signer account. This is intentionally not modeled as pool claimable value.
- Credit protocol-fee value through claim balances when the fee receiver removes liquidity.

Validation:

- Burn/decrease cannot lose owed value.
- Remove/protocol-fee claim accounting and duplicate CreatePool refund accounting are reachable only from expected workflow states.
- Remove and protocol-fee claim paths validate owner, token, amount, and current state before mutating claim balances. Duplicate CreatePool refund stays on the swap creator chain and does not mutate pool claim balances.
- Credited values can exit through `Claim`.

### FUND-013 Iteration 8: Internal entry and application-caller hardening sweep

Purpose: close residual public-operation, internal-message, and cross-application caller bypass boundaries after the funding-path iterations. User-authored contracts can call public operations through `call_application`, so every operation handler must enforce the same actor, chain, and workflow constraints as a frontend-submitted operation.

Entry matrix:

- `SwapOperation::UpdatePool`: public operation that currently forwards caller-supplied transaction, reserve, and price facts to `SwapMessage::UpdatePool`. Target constraint: authenticated caller must exist and `Account { chain_id: runtime.chain_id(), owner: AccountOwner::from(caller) }` must equal the canonical pool application account from `swap.get_pool_exchangable(token_0, token_1)`. Pool must already be registered by `PoolCreated`; first update has no exception.
- `SwapMessage::UpdatePool`: catalog mutation message emitted by the validated `SwapOperation::UpdatePool` path. No duplicate message-side creator-chain guard is required; the required facts are that the operation caller is the canonical pool application on the pool chain and the emitted message destination is `application_creator_chain_id()`.
- `SwapMessage::PoolCreated`: pool registration receipt. Existing constraints must remain: source pool chain is tracked, same-pool duplicate is idempotent, different pool for existing pair rejects, and catalog registration precedes later updates.
- `SwapMessage::{CreatePool, CreateUserPool, InitializeLiquidity, UserPoolCreated}`: create-pool choreography messages. Target review: each message has one legal execution chain and cannot be forged to bypass public `CreatePool` or meme initialization constraints.
- Pool receipt operations/messages: `AddLiquidityTransferReceipt`, `SwapTransferReceipt`, and `ClaimTransferReceipt` must reject wrong caller, wrong chain, wrong token, wrong fund type, and invalid state transitions.
- Meme transfer receipt paths: `TransferFromApplication`, `TransferFromApplicationWithReceipt`, and `TransferFromApplicationReceipt` must reject forged caller/source/purpose/pool targets while preserving valid claim, swap, and add-liquidity callbacks.
- Proxy message boundaries: `CreateMemeExt` remains the user-chain exception; other proxy messages remain creator-chain only.

Atomic implementation steps:

- A1: Write the entry matrix and executable atomic steps.
- A2: Harden `SwapOperation::UpdatePool` as a pool-chain application-caller forwarding entry and move canonical pool-chain validation to `SwapMessage::UpdatePool`.
- A3: Add `SwapOperation::UpdatePool` tests for missing caller reject, creator-chain reject, and pool-chain application-caller forward success; add `SwapMessage::UpdatePool` tests for missing catalog and wrong message-origin chain reject.
- A4: Review and test `SwapMessage::UpdatePool` creator-chain settlement facts: message origin chain must equal the registered pool application chain, and valid operation forwarding sends to `application_creator_chain_id()`.
- A5: Review and test `SwapMessage::PoolCreated` boundaries.
- A6: Review and test user create-pool continuation boundaries for `CreateUserPool` and `UserPoolCreated`.
- A7: Sweep pool receipt operation/message boundaries.
- A8: Sweep meme transfer receipt boundaries.
- A9: Sweep proxy chain-boundary exceptions.
- A10: Run targeted tests and full memory-limited `cargo test -j 1`.

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
