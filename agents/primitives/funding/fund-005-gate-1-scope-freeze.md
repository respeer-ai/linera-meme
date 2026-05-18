# FUND-005 Gate 1 Scope Freeze

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Define the canonical review organization for `FUND-005` Gate 1. Review and approval proceed sub-gate by sub-gate. Do not batch the full Gate 1 scope freeze into one delivery.

## Rules

- Review Gate 1 through these sub-gates only:
  1. `Gate 1A`: audit layers
  2. `Gate 1B`: in-scope files
  3. `Gate 1C`: fixed protocol paths
  4. `Gate 1D`: exclusions
  5. `Gate 1E`: audit dimensions and Gate 2 format constraints
- Do not start a later sub-gate before the earlier sub-gate is reviewed and accepted.
- Do not repeat the full Gate 1 body in later prompts. Reference this file and include only the current sub-gate content under review.
- Do not use vague scope terms such as `related`, `as needed`, `etc`, or similar expandable wording.
- Do not treat a prose summary as approval. Each sub-gate must be reviewable item by item.

## Gate 1A Audit Layers

`FUND-005` Gate 2 must organize the current implementation audit table through these fixed layers and in this order:

1. Protocol definition layer
2. Runtime abstraction layer
3. Contract dispatch boundary layer
4. Contract handler layer
5. Persistent state layer
6. Product entry and truth boundary layer
7. Test baseline layer

### Gate 1A Layer Definitions

1. Protocol definition layer
   - Authority:
     - `abi/`
   - Purpose:
     - define operation, message, response, and payload shapes
     - define instantiation argument shapes
     - define service query and query-response shapes used by product funding paths
     - define token, account, and chain identity shapes used by funding workflows
   - Must answer:
     - which funding protocol objects currently exist
     - which instantiation arguments currently exist
     - which are public operations
     - which are internal messages
     - which are response or callback carriers
     - which service query and query-response objects are funding-relevant
     - whether claim, fail, and bounce closure objects already exist
     - whether `CreatePool`, `InitializeLiquidity`, `AddLiquidity`, `Swap`, `RemoveLiquidity`, and `CreateMeme` already have explicit funding semantics

2. Runtime abstraction layer
   - Authority:
     - `runtime/`
   - Purpose:
     - define capabilities exposed to contracts, not business workflow ownership
     - define authenticated caller, message context, application-call context, access control, message send capability, application-call capability, direct transfer capability, application creation capability, chain opening capability, application-permission capability, bounce capability, and close-chain capability
   - Must answer:
     - how contracts currently obtain caller, source, app, and message context
     - whether `call_application` capability is exposed
     - whether message send capability is exposed
     - whether direct native transfer capability is exposed
     - whether direct combined owner/application transfer capability is exposed
     - whether application creation capability is exposed
     - whether chain opening capability is exposed
     - whether application-permission read/write capability is exposed
     - whether bounce detection capability is exposed
     - whether close-chain capability is exposed
     - which runtime capabilities required by later funding iterations already exist and which are missing
     - whether runtime send capability currently applies authentication by default
     - whether runtime send capability currently applies tracking by default
     - whether close-chain is a current capability or a target capability gap
     - where each exposed capability is consumed by handler architecture, without treating capability exposure as workflow ownership

3. Contract dispatch boundary layer
   - Authority:
     - each funding contract's `contract.rs`
     - each funding contract's `contract_impl.rs`
   - Purpose:
     - define instantiation entry dispatch
     - define operation entry dispatch
     - define message entry dispatch
     - define outgoing message send boundary
     - define bounced-message receive boundary
   - Must answer:
     - where instantiation is dispatched
     - where operations are dispatched
     - where messages are dispatched
     - whether instantiation creates funding-relevant state, applications, chains, permissions, transactions, or outgoing messages
     - where `.send_message(...)` actually sends
     - whether authentication and tracking are attached here or scattered in business handlers
     - whether bounced messages have an explicit dispatch entry
     - what the real send modifiers are, without assuming design intent equals current implementation

4. Contract handler layer
   - Authority:
     - handler boundary:
       - each funding contract's `contract_inner/handlers/*`
     - instantiation-handler boundary:
       - each funding contract's `contract_inner/instantiation_handler*`
     - contract-impl instantiation boundary:
       - instantiation-side business behavior inside each funding contract's `contract_impl.rs`
   - Purpose:
     - define current business behavior, state transition logic, checks, and side effects
   - Must answer:
     - what each current handler actually does
     - what instantiation-side business behavior does when it creates funding-relevant state or messages
     - which handlers act as callback consumers
     - which handlers act as receipt consumers
     - which source, authenticated-caller, application, intent, token, amount, owner, and state checks each callback or receipt consumer performs
     - which runtime capabilities each handler consumes
     - where `call_application(...)` is actually initiated
     - where direct native transfer or combined transfer is actually initiated
     - whether direct transfer occurs inside liquidity, swap, remove, refund, payout, initialization, or claim-like behavior
     - which state preconditions each handler relies on
     - which economic states each handler mutates
     - how each handler treats invalid input, duplicate input, and stale follow-up
     - whether owner, intent, token, or amount is currently inferred from signer or payload where it should not be
     - whether late guards are currently substituting for real terminal truth
     - whether funds exit currently happens inside a workflow that should later credit claim balances instead

5. Persistent state layer
   - Authority:
     - each funding contract's `interfaces/state*`
     - each funding contract's `state*`
   - Purpose:
     - define protocol truth storage for active, pending, finalized, failed, reserve, LP, payout, refund, claim, and claiming state
   - Must answer:
     - which state fields are initialized by instantiation before any operation or message
     - which fields currently determine whether a pool is active
     - which fields currently determine whether reserves are finalized
     - which fields currently determine whether LP is minted or burned
     - whether claim and claiming balance truth already exists
     - whether terminal truth is unique
     - whether double truth exists
     - whether late guards currently stand in for real terminal truth

6. Product entry and truth boundary layer
   - Authority:
     - frontend entry boundary:
       - frontend funding operation submission chain
       - frontend GraphQL read layer
     - contract service boundary:
       - contract `service.rs` query surface
       - contract `service.rs` mutation surface when used by product entry
     - observability fact/projection boundary:
       - `service/kline/` raw fact ingestion
       - `service/kline/` application discovery and registry persistence
       - `service/kline/` decoder and registry selection
       - `service/kline/` normalized event family mapping
       - `service/kline/` projection and market/funding derivation
       - `service/kline/` projection-backed query and serializer boundary
       - `service/kline/` debug and diagnostic visibility for pending, stalled, and failed workflows
     - product truth boundary:
       - `service/kline/` projection-backed funding truth
   - Purpose:
     - define how users enter funding workflows
     - define how products read funding prerequisites
     - define where product truth is projection-backed versus live-query-backed
   - Must answer:
     - which frontend entries submit funding operations
     - what the frontend operation submission chain is beyond page components
     - which GraphQL or read paths are used to determine pair existence, meme application existence, creator chain, and create-pool versus add-liquidity routing
     - where account, application, and token identity are normalized before chain submission
     - what the wallet-type-specific submission capability matrix is across funding operations
     - which funding-relevant query and mutation surfaces contract `service.rs` exposes
     - which raw facts are needed for funding workflow visibility
     - which application discovery and registry persistence entries are needed for funding workflow visibility
     - which decoder and registry entries are needed for funding workflow visibility
     - which normalized event families are needed for funding workflow visibility
     - which projections derive claim balances, claiming balances, pending workflows, stalled workflows, failed workflows, pool lifecycle, reserves, LP, positions, TVL, APR inputs, and diagnostics
     - which query handlers, read models, serializers, and repositories expose projected funding truth
     - which product truths come from projections
     - which product truths still depend on live query
     - whether stalled, pending, and failed workflows are visible to product or diagnostics
   - Scope requirements:
     - page entry layer
     - route and flow decision layer
     - store layer
     - wallet and provider adapter layer
     - protocol utility layer
     - frontend GraphQL read layer
     - account, application, and token identity normalization boundary
     - wallet-type-specific submission capability boundary
     - contract `service.rs` query surface
     - contract `service.rs` mutation surface when the frontend or product entry actually depends on it
     - raw fact ingestion boundary
     - application discovery and registry persistence boundary
     - decoder and registry boundary
     - normalized event family boundary
     - projection and market/funding derivation boundary
     - projection-backed query and serializer boundary
     - debug and diagnostic visibility boundary
   - Required product-entry semantics:
     - `CreatePool`
     - `InitializeLiquidity`
     - `AddLiquidity`
     - `Swap`
     - `RemoveLiquidity`
     - `CreateMeme`

7. Test baseline layer
   - Authority:
     - runtime capability test boundary
     - base handler and dispatch support test boundary
     - funding contract test boundary
     - contract service test boundary
     - observability fact/projection test boundary
     - frontend funding-entry test boundary
   - Purpose:
     - define what current behavior is already locked by tests
     - define which current behaviors still need characterization before refactor
   - Must answer:
     - which runtime capabilities are already locked by tests
     - which base handler outcome and dispatch message-shape behaviors are already locked by tests
     - which send authentication and tracking behaviors are already locked by tests
     - which missing bounce and close-chain capability gaps have characterization coverage
     - which funding behaviors are already locked by contract tests
     - which funding-related contract service query or mutation semantics are locked by service tests
     - which raw ingestion, decoder, registry, normalizer, projection, query/read-model, serializer, and diagnostic visibility behaviors are already locked by tests
     - which pending, stalled, and failed workflow visibility behaviors are already locked by tests
     - which funding entry semantics are locked by frontend baseline tests
     - which funding routing and mode-selection semantics are locked by baseline tests
     - which funding submission semantics are locked by baseline tests
     - which critical behaviors still lack characterization tests
     - which behaviors must be locked before protocol mutation

### Gate 1A Acceptance Criteria

Gate 1A is accepted only if:

1. The seven layers are complete.
2. The layer order is accepted.
3. Layers 1, 2, 3, and 5 each have one clear authority boundary.
4. Each layer has one clear purpose boundary.
5. Layer 1 explicitly includes operation, message, response, instantiation argument, service query, and service query-response shapes.
6. Layer 2 explicitly includes `call_application` and runtime send-capability reality checks.
7. Layer 2 explicitly treats runtime as a capability boundary and not as business workflow ownership.
8. Layer 2 explicitly includes direct transfer capability, application creation capability, chain opening capability, application-permission capability, and close-chain current-vs-target capability checks.
9. Layer 3 explicitly includes instantiation dispatch and `send_message` dispatch-boundary reality checks.
10. Layer 3 explicitly includes instantiation-side funding state, transaction, application, chain, permission, and outgoing-message side effects.
11. Layer 4 has exactly these three authority sub-boundaries:
   - handler boundary
   - instantiation-handler boundary
   - contract-impl instantiation boundary
12. Layer 4 explicitly includes actual handler-side `call_application`, direct transfer, payout, refund, and funds-exit location checks.
13. Layer 4 explicitly includes instantiation-side business behavior inside `contract_inner/instantiation_handler*` and `contract_impl.rs`.
14. Layer 4 explicitly includes callback and receipt consumer checks.
15. Layer 5 explicitly includes state initialized by instantiation before operation or message handling.
16. Layer 6 has exactly these four authority sub-boundaries:
   - frontend entry boundary
   - contract service boundary
   - observability fact/projection boundary
   - product truth boundary
17. Layer 6 explicitly includes:
   - `CreateMeme` as a funding-relevant product entry
   - wallet/provider adapter boundary
   - frontend GraphQL read layer
   - contract `service.rs` query/mutation surface
   - account/application/token identity normalization boundary
   - wallet-type-specific submission capability boundary
   - raw fact ingestion boundary
   - application discovery and registry persistence boundary
   - decoder and registry boundary
   - normalized event family boundary
   - projection and market/funding derivation boundary
   - projection-backed query and serializer boundary
   - debug and diagnostic visibility boundary
18. Layer 7 has exactly these six authority sub-boundaries:
   - runtime capability test boundary
   - base handler and dispatch support test boundary
   - funding contract test boundary
   - contract service test boundary
   - observability fact/projection test boundary
   - frontend funding-entry test boundary
19. Layer 7 explicitly includes:
   - runtime capability baseline tests
   - base handler and dispatch support baseline tests
   - funding contract tests for `swap`, `pool`, `meme`, and `proxy`
   - contract service tests / service-layer baseline tests
   - observability raw ingestion / decoder / normalizer / projection / query / diagnostic baseline tests
   - frontend funding-entry baseline tests
   - frontend funding-entry routing / mode-selection baseline tests
   - frontend funding submission semantics baseline tests
20. Gate 2 is constrained to use these layers in this order.

## Gate 1B In-Scope Files

To be reviewed separately after Gate 1A acceptance.

## Gate 1C Fixed Protocol Paths

To be reviewed separately after Gate 1B acceptance.

## Gate 1D Exclusions

To be reviewed separately after Gate 1C acceptance.

## Gate 1E Audit Dimensions And Gate 2 Format Constraints

To be reviewed separately after Gate 1D acceptance.
