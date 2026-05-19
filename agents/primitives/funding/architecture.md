# Funding Architecture

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Define the canonical architecture for AMM funding consistency across `swap`, `pool`, `meme`, `proxy`, frontend product flows, and observability.

## Goals

- Preserve funds consistency when cross-chain or cross-application effects are delayed, rejected, arrive after related state has changed, compete with another workflow, or never execute.
- Never expose finalized reserves, LP shares, positions, claim balances, or active pool entries in `swap` application state before the required protocol state transition is committed.
- Keep owner funds recoverable through a single funds-exit operation, `Claim`.
- Make every committed intermediate state observable through parsed block facts and projections.
- Implement the protocol through independently verifiable iterations.

## Non-Goals

- Do not introduce per-operation temp chains for the current AMM.
- Do not rely on chain-level timeout semantics.
- Do not design a generic `Resume` operation.
- Do not assume a target chain will eventually execute a message.
- Do not treat off-chain workers as protocol truth.
- Do not derive product accounting from live chain queries.

## User-Reachable ABI

Only operations are user-reachable ABI. Messages are contract-created follow-up effects and users cannot directly create them.

User-reachable operation entry includes both:

- A frontend wallet directly signing and submitting an operation.
- A user-authored contract calling the application via `call_application`.

Both forms must satisfy the same authorization, intent, identity, and funds-safety rules. Frontend-only validation is not a security boundary.

## Funds Exit

`Claim` is the only user-facing funds-exit operation.

These are not separate user product operations:

- retry claim
- refund
- excess withdrawal
- protocol-fee withdrawal
- remote-liquidity withdrawal
- trading-yield withdrawal
- generic workflow resume

They are accounting meanings inside claim state and claim balances.

## Product CreatePool Semantics

`SwapOperation::CreatePool` remains a public user operation only for the existing Add Liquidity missing-pair path.

Its only allowed product meaning is user create-with-real-initial-liquidity. It must not mean:

- empty pool
- shell-only pool
- zero-liquidity pool
- one-sided user pool
- user virtual-liquidity pool

Meme-native pool initialization is a different path. It uses `SwapOperation::InitializeLiquidity` and may use virtual native reference semantics when called from the meme application on the valid creator chain. Do not use public `CreatePool` to express meme initialization or virtual liquidity.

Internal create-pool messages may exist as implementation choreography, but they must be bound to a persisted intent and must not define independent product semantics.

The current protocol supports only the native token and meme tokens for pool creation and liquidity funding. Native token identity is built in. Meme token identity is validated only from a safe user-started path by calling the meme token application for creator-chain identity. Public `SwapOperation::CreatePool` must not require the frontend or user to supply creator-chain identity. Authoritative chain facts are preferred wherever the executing hop can read them safely. For any actual implementation path that uses `call_application`, reentrant constraints must be analyzed before choosing whether that path reads chain facts directly, carries the necessary creator-chain identity in internal messages, or defers the authoritative check to a later hop. Any other token kind must be rejected until a concrete protocol validation rule exists for it.

Pending pair contention follows first-funded-wins semantics. Multiple users may race to create the same pair, but the first workflow that reaches the required funded terminal state wins and becomes the active pool entry in `swap` application state. Losing workflows must fail safely: any already-custodied value is credited to claim balances, and any opened-but-losing shell chain/application must be cleaned up or made permanently failed. Active pair creation still must not create another pool.

Terminal state for pool creation must be unique and reliable. Do not split terminal truth across an additional "created" flag plus an intent status. The intent state machine is the authority for whether a create-pool workflow is pending, active, failed, or cleaned up. A failed terminal workflow must not leave a reusable old shell or pool application that can later be confused with a new attempt.

After a pool shell/application exists, a wallet may technically call the pool application directly. That is acceptable only because a shell has no finalized reserves or LP supply until a funding workflow finalizes. The safety boundary is not hiding the pool application; it is ensuring pending or losing shells are non-finalized and never exposed as active pool entries in `swap` application state before a valid funding workflow wins.

If a shell exists and the original creator has not injected/finalized funding yet, another user may call `AddLiquidity` on that shell. This is allowed. That later user does not create a second `PoolCreationIntent`; the operation creates only a pool-local `AddLiquidityIntent`. If that `AddLiquidityIntent` is the first two-leg funding workflow to finalize, it defines the initial reserves and wins the pool creation race. The pool activation receipt binds to the already-existing shell and pair, and the single swap-side `PoolCreationIntent` becomes active for that pool application. The winner owner and LP recipient come from the finalized funding workflow, not from the original shell creator. Later funding from the original creator, or from any other losing workflow, must be processed against the already-finalized pool using the normal add-liquidity calculation at the current reserves. The limiting side determines the accepted liquidity amount; excess from the other side is credited to claim balances. It must not be applied as a second initial reserve.

Linera applications can close the current chain through `ContractRuntime::close_chain()` if their application id is authorized by the chain's `ApplicationPermissions.close_chain`. Linera close only marks the chain closed; it does not move remaining balance or application custody. The current pool child-chain creation path already grants close permission to the router/swap application. Cleanup may close a losing shell only after all application-level cleanup has completed: no reserves/LP are finalized, owed user value has been credited to claim balances, and any remaining shell custody has been resolved according to the shell cleanup state. If cleanup is not fully completed, the shell must remain permanently failed/non-economic rather than be closed.

## Message Delivery

Outgoing application messages must be tracked by default. Tracking is not an end-to-end transaction guarantee; its purpose is to let the sender chain receive a protocol bounce when the destination chain rejects that one message hop, so the sender-side workflow can converge from `pending` to a safe failed, refund-ready, or claimable state.

Tracking must be centralized in the runtime send-message abstraction. Business handlers must not construct or expose a separate tracked-message builder. In this repository, the relevant abstraction is `ContractRuntimeContext::send_message`; the contract runtime adapter must attach authentication and tracking there by default. This default is introduced by the user-pool-creation intent iteration before later claim and funding workflows depend on bounce handling.

Receiving handlers must check whether a message is bouncing with Linera's `message_is_bouncing()` API and handle that as the reject receipt for the previously sent tracked message. A non-bounced tracked message still only means the specific hop was not rejected; it does not prove that later business workflow steps completed.

Reference implementation pattern: `linera-protocol/examples/fungible/src/contract.rs` uses `prepare_message(...).with_authentication().with_tracking().send_to(...)` when sending cross-chain credit messages, and checks `runtime.message_is_bouncing()` when receiving them.

## Uniswap Alignment

Uniswap alignment is rationale, not the protocol authority. Uniswap does not create an append-only per-event claim queue for owed value. Long-lived unclaimed value is represented as aggregated accounting state, such as reserve/share value in V2 or position owed accounting in V3.

This protocol follows that direction:

- Long-lived claimable value must be aggregated into claim balances.
- Workflow intents exist for cross-chain business state, authorization, and custody safety.
- Linera core protocol is responsible for executing a chain operation or accepted incoming message once in chain history. Application code must not add protocol-level duplicate-delivery defenses for the exact same operation or message.
- Application state still needs business guards for distinct operations or messages that target the same business workflow, stale follow-ups, wrong source/caller, or effects that arrive after a workflow status has changed.
- Event-level detail belongs in parsed facts and projections, not in unbounded on-chain claim queues.

## Source Of Truth

- Chain contracts are protocol truth.
- Product-facing data comes from parsed block facts and projections.
- Frontend live query is allowed for wallet identity, operation submission, and explicitly labeled live wallet balances only.
- Frontend claim lists must come from projection/API, not live query reconstruction.

## Canonical References

- State machines: `agents/primitives/funding/state-machines.md`
- On-chain data model: `agents/primitives/funding/on-chain-data-model.md`
- Claim design: `agents/primitives/funding/claim.md`
- Security invariants: `agents/primitives/funding/security-invariants.md`
- Projection boundaries: `agents/primitives/funding/projection-and-product-reads.md`
