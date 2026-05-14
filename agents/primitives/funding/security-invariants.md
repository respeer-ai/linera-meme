# Funding Security Invariants

Type: Primitive
Audience: Coding assistants
Authority: High

## Public Entry Boundary

- Only operations are user-reachable ABI.
- User reachability includes frontend wallet signing and user-authored contracts calling via `call_application`.
- Every public operation must validate authorization, intent identity, token identity, and funds state.

## Internal Message Boundary

- Users cannot directly create messages.
- Messages are implementation choreography and must be bound to persisted intents or claim delivery state.
- Messages must not infer owner, token, amount, pair, or recipient from message signer once an intent exists.

## Caller And Source Checks

Every internal follow-up must verify the expected subset of:

- authenticated caller application
- source chain
- source application
- expected pool application
- expected token application
- `intent_id`
- `leg_id`
- `attempt_id`
- token identity
- amount
- owner/recipient account

## Token Validation

- Token identity is validated fail-fast at the earliest trusted user-started entry.
- Existing active pool operations use registered pool token identities and must not rediscover token identity.
- Meme token validation via `call_application(token_app, CreatorChainId)` is allowed only on safe user-started entry paths.
- Do not call token app for validation from `meme -> swap InitializeLiquidity`.
- Do not call token app from token funding callbacks, claim callbacks, or token-app-entered message handlers.

## Finalization Invariants

- Do not finalize reserve before required input custody is represented.
- Do not mint LP share before both add-liquidity legs are funded.
- Do not mark pool active before activation receipt is consumed by swap catalog.
- Do not burn LP share unless owed value is credited to claim balances or otherwise proven delivered.
- Do not mark claim delivery succeeded before success acknowledgement or successful synchronous native transfer.
- Do not double-credit claim balances on duplicate finalization.

## Virtual Liquidity

- Virtual liquidity is a pricing reference only.
- It is not deposited reserve.
- It is not TVL.
- It is not claimable balance.
- It is not payable native balance.
- It must be emitted and projected as virtual position state, not normal add-liquidity state.

## Stalled Workflows

- A target chain may never execute a message.
- Pending forever is allowed only when the state remains safe and observable.
- Do not use timeout assumptions to refund, retry, activate, or finalize.
- Do not introduce generic resume.
