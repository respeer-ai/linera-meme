# Funding Security Invariants

Type: Primitive
Audience: Coding assistants
Authority: High

## Public Entry Boundary

- Only operations are user-reachable ABI.
- User reachability includes frontend wallet signing and user-authored contracts calling via `call_application`.
- Every public operation must validate authorization, token identity, and funds state. When a path uses persisted workflow state, it must validate that state explicitly.
- User-owned operations derive the owner from the authenticated operation account unless the path has an explicitly documented recipient field. `Claim` must not accept a user-supplied owner field.

## Internal Message Boundary

- Users cannot directly create messages.
- Messages are implementation choreography and must be bound to either authoritative chain facts, explicitly carried immutable workflow facts, or persisted workflow state where the reviewed design requires it.
- Messages must not infer owner, token, amount, pair, or recipient from message signer unless that signer is the reviewed business fact for that exact hop.

## Caller And Source Checks

Every internal follow-up must verify the complete field set required by its path. `FUND-005` must produce a path validation matrix before behavior-changing iterations begin.

The matrix must list, for every operation, message, callback, and receipt:

- authenticated caller application
- source chain
- source application
- expected pool application
- expected token application
- carried immutable workflow facts when the path uses them
- concrete funding-leg identity when the path uses it
- token identity
- amount
- owner/recipient account
- required current state
- allowed next state
- failure behavior, using one of the explicitly named outcomes for that path: reject, bounce-handled transition, no-op idempotency, or panic/abort

The matrix must choose exactly one failure behavior for each invalid condition on each path. Later implementation must not introduce a new failure behavior without updating the matrix and tests first.

Do not leave validation to implementation judgment with phrases such as "expected subset." A path may omit a field only if the matrix explicitly states that the field is not available or not meaningful for that path and explains why omitting it is safe.

## Token Validation

- Token identity is validated fail-fast at the earliest trusted user-started entry.
- The current protocol supports only native and meme token identities.
- Any non-native, non-meme token kind must reject until a concrete validation rule is designed and implemented.
- Existing active pool operations use registered pool token identities and must not rediscover token identity.
- Meme token validation via `call_application(token_app, CreatorChainId)` is allowed only on safe user-started entry paths.
- Do not call token app for validation from `meme -> swap InitializeLiquidity`.
- Do not call token app from token funding callbacks, claim callbacks, or token-app-entered message handlers.

## Finalization Invariants

- Do not finalize reserve before required input custody is represented.
- Do not mint LP share before both add-liquidity legs are funded.
- Do not mark a pair active in `swap` application state before the app-created receipt is consumed.
- Do not treat a pool as tradable, removable, or ordinary-add-liquidity-eligible before finalized reserve/share facts exist.
- Do not burn LP share unless owed value is credited to claim balances or otherwise proven delivered.
- Do not remove meme-token claiming balance before success acknowledgement, and do not remove native claim balance before successful synchronous native transfer.
- Finalization and claim-balance crediting must only be reachable from the expected workflow state.
- Do not add application-level defenses for exact operation/message duplicate execution; Linera core protocol provides once-only chain execution for accepted operations/messages.

## Virtual Liquidity

- Virtual liquidity is a pricing reference only.
- It is not deposited reserve.
- It is not TVL.
- It is not claimable balance.
- It is not payable native balance.
- It must be emitted and projected as virtual position state, not normal add-liquidity state.
- Any protocol branch that permits virtual-liquidity bootstrap semantics must be entered only through a reviewed internal discriminator. Ordinary user input must not be able to choose that branch.

## Stalled Workflows

- A target chain may never execute a message.
- Pending forever is allowed only when the state remains safe and observable.
- Do not use timeout assumptions to refund, retry, activate, or finalize.
- Do not introduce generic resume.
