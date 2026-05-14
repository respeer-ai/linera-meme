# Funding Architecture

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Define the canonical architecture for AMM funding consistency across `swap`, `pool`, `meme`, `proxy`, frontend product flows, and observability.

## Goals

- Preserve funds consistency when cross-chain or cross-application effects are delayed, rejected, duplicated, reordered, or never executed.
- Never expose finalized reserves, LP shares, positions, claim balances, or active catalog state before the required protocol state transition is committed.
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

Its only allowed product meaning is create-with-initial-liquidity. It must not mean:

- empty pool
- shell-only pool
- zero-liquidity pool
- one-sided user pool
- user virtual-liquidity pool

Internal create-pool messages may exist as implementation choreography, but they must be bound to a persisted intent and must not define independent product semantics.

## Uniswap Alignment

Uniswap does not create an append-only per-event claim queue for owed value. Long-lived unclaimed value is represented as aggregated accounting state, such as reserve/share value in V2 or position owed accounting in V3.

This protocol follows that direction:

- Long-lived claimable value should be aggregated into claim balances.
- Workflow intents exist only for cross-chain safety and idempotency.
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
