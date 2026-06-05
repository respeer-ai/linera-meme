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

Meme-native pool initialization is a different path. It uses `SwapOperation::InitializeLiquidity` and may include virtual native reference semantics, but virtual value is never claimable or withdrawable. Do not use public `CreatePool` to express meme initialization or virtual liquidity.

The current protocol supports only the native token and meme tokens for pool creation and liquidity funding. Native token identity is built in. Meme token identity is validated only from a safe user-started path by calling the meme token application for creator-chain identity. Public `SwapOperation::CreatePool` must not require the frontend or user to supply creator-chain identity. Authoritative chain facts are used on user-started `CreatePool` paths. The only current protocol field that carries meme creator-chain identity is `SwapOperation::InitializeLiquidity.token_0_creator_chain_id`, and it exists only for the synchronous `meme -> call_application(swap.InitializeLiquidity)` path. Swap must validate that carried value at the operation boundary and must not propagate it into `SwapMessage::InitializeLiquidity`, `SwapMessage::CreatePool`, `SwapMessage::CreateUserPool`, or `PoolParameters`. Any other token kind must be rejected until a concrete protocol validation rule exists for it.

Pool application creation and pool economic state are distinct protocol phases:

1. pool application creation
2. real-funding entry into the pool application
3. finalized reserve/share facts

Creating a pool application does not mean the pool is initialized, active, tradable, or ready for ordinary add-liquidity / swap / remove-liquidity paths.

The target design does not use persisted create-pool intents. Protocol truth for pool usability comes from finalized pool-side economic state itself: finalized reserve/share facts, not a separate lifecycle bit.

Meme initialization and user `CreatePool` are distinct paths with different funding sources and authorization boundaries. Meme initialization uses internal bootstrap authority and may use virtual-liquidity semantics. User `CreatePool` uses the existing `UserPoolCreated -> PoolOperation::AddLiquidity` flow to transfer both user-funded legs from the user chain. No user-pool-specific funding ABI is added, and user flow must not reuse meme virtual-liquidity authority. Ordinary existing-pool add liquidity, swap, and remove liquidity are allowed only after finalized reserve/share facts exist.

Linera applications can close the current chain through `ContractRuntime::close_chain()` if their application id is authorized by the chain's `ApplicationPermissions.close_chain`. Linera close only marks the chain closed; it does not move remaining balance or application custody. The current pool child-chain creation path already grants close permission to the router/swap application. Cleanup may close a failed pool chain only after all application-level cleanup has completed: no reserves/LP are finalized, owed user value has been credited to claim balances, and any remaining custody has been resolved according to the cleanup state. If cleanup is not fully completed, the chain must remain permanently non-economic rather than be closed.

## Initialization Boundary

For pool-based funding flows, the protocol must distinguish:

- pool application exists
- real funds entered the pool application
- first finalized pool economic facts written

`PoolCreated` is an app-created fact only. It is not by itself the boundary for active pool truth, final reserve/share state, or normal-path usability.

The boundary for ordinary pool behavior is finalized pool-side reserve/share facts.

After a pool application exists but before finalized reserve/share facts exist, the pool is a non-economic protocol object.

Rules:

- Pool applications without finalized reserve/share facts are valid protocol objects but are not yet usable for ordinary swap or remove-liquidity flows.
- Meme initialization writes its first finalized reserve/share facts through the explicit pool-side `InitializeLiquidity` path.
- User `CreatePool` keeps the existing `UserPoolCreated -> PoolOperation::AddLiquidity` path. That path is allowed on a zero-reserve user-created pool because current pool math accepts the two desired amounts as the initial reserve pair.
- Direct ordinary add-liquidity requests before finalized reserve/share facts do not get meme initialization authority or virtual-liquidity semantics.
- Ordinary existing-pool add liquidity exists only after finalized reserve/share facts exist; the pre-finalized AddLiquidity use is the `UserPoolCreated` user CreatePool funding continuation.
- Product-visible pool, market, and trading surfaces must exclude pools that do not yet have finalized reserve/share facts.
- Virtual-initial-liquidity economics, when used by meme initialization, must not create withdrawable, claimable, or removable value beyond the real assets that actually entered the pool application.

`meme initialization` is an internal protocol-path discriminator only. It exists to authorize virtual-liquidity bootstrap semantics and related create-pool choreography. It must not be selectable by ordinary user input.

## Message Delivery

Outgoing application messages must be authenticated by default. Tracking is explicit per message and is enabled only after the owning handler defines a `message_is_bouncing()` branch for that path. Tracking is not an end-to-end transaction guarantee; its purpose is to let the sender chain receive a protocol bounce when the destination chain rejects that one message hop, so the sender-side workflow can converge from `pending` to a safe failed, refund-ready, or claimable state.

Tracking selection must be centralized in the runtime send-message abstraction. Business handlers must not construct or expose a separate tracked-message builder. In this repository, the relevant abstraction is `ContractRuntimeContext::send_message`; callers pass an explicit `tracking` flag and the contract runtime adapter always attaches authentication, then attaches tracking only when that flag is true.

Receiving handlers must check whether a message is bouncing with Linera's `message_is_bouncing()` API and handle that as the reject receipt for the previously sent tracked message. A non-bounced tracked message still only means the specific hop was not rejected; it does not prove that later business workflow steps completed.

Reference implementation pattern: `linera-protocol/examples/fungible/src/contract.rs` uses `prepare_message(...).with_authentication().with_tracking().send_to(...)` when sending cross-chain credit messages, and checks `runtime.message_is_bouncing()` when receiving them.

## Uniswap Alignment

Uniswap alignment is rationale, not the protocol authority. Uniswap does not create an append-only per-event claim queue for owed value. Long-lived unclaimed value is represented as aggregated accounting state, such as reserve/share value in V2 or position owed accounting in V3.

This protocol follows that direction:

- Long-lived claimable value must be aggregated into claim balances.
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
