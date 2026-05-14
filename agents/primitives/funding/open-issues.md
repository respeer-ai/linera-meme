# Funding Open Issues

Type: Primitive
Audience: Coding assistants
Authority: High

## Format

Each issue tracks a protocol gap that must not be hidden behind implementation shortcuts.

## OI-001 Pool Shell Message Never Executes

Status: Open

Affected flow: user `CreatePool` with initial liquidity.

Problem: swap may create `PoolCreationIntent` and send a pool-shell creation message whose target chain never executes.

Current safe behavior: keep intent stalled/pending; do not activate.

Unsafe shortcuts:

- timeout-based activation
- opening another pool for the same pair
- generic resume or generic admin cancel

## OI-002 Shell Receipt Never Reaches Swap

Status: Open

Affected flow: user `CreatePool`, meme native pool initialization.

Problem: pool shell may exist while the swap chain never receives the receipt.

Current safe behavior: shell is not active in `swap` application state and has no finalized reserves. Projection may show stalled shell if facts are available.

Unsafe shortcuts:

- treating shell existence as active pool truth
- allowing swaps against the shell before finalized reserves exist

## OI-003 One Funding Leg Pending Forever

Status: Open

Affected flow: create pool initial liquidity, add liquidity.

Problem: one leg may be funded while the opposite leg never executes and never fails.

Current safe behavior: keep funded custody value in stalled intent; do not reserve, mint, refund, or claim unless explicit failure evidence exists.

Unsafe shortcuts:

- timeout refund
- generic retry or generic admin cancel
- minting one-sided LP

## OI-004 Finalized Pool Activation Receipt Missing

Status: Open

Affected flow: create pool initial liquidity.

Problem: pool may finalize reserves and mint LP while activation receipt never reaches the swap chain.

Current safe behavior: do not recreate pool or mint again; do not mark the pair active in `swap` application state without a valid activation transition.

Unsafe shortcuts:

- rebuild pool
- infer active from pool finalized state without a designed reconciliation path

## OI-005 Meme Claiming Balance Pending Forever

Status: Open

Affected flow: meme token `Claim`.

Problem: pool may send meme payout message and move value from `claim_balances` to `claiming_balances` while the target chain never executes the message.

Current safe behavior: keep the amount in `claiming_balances`; do not allow it to be claimed again; expose pending claiming balance through projection.

Unsafe shortcuts:

- timeout retry
- returning claiming balance to available balance without proof old delivery cannot execute

## OI-006 Recovery Operations

Status: Deferred

Problem: future operational recovery may be needed.

Decision: do not design a generic `Resume` or generic admin cancel. Any future recovery or cancellation operation must be state-specific and justified against Linera's core once-only operation/message execution model.

## OI-007 Claim ABI Shape

Status: Decided

Decision:

- `Claim { token_identity, amount }`

Rationale:

- Contract claim balances are stored as a two-level map: token first, owner second.
- There is no per-claim queue and no claim key.
- There is no per-claim delivery attempt id; asynchronous meme claims use aggregated `claiming_balances`.
- Product/accounting categories are maintained by the data platform.
- User funds exit through a single operation on the pool application.

## OI-008 Claim Balance Bucket Design

Status: Decided

Decision: contract claim balances do not include buckets.

Rationale: protocol fee, remote liquidity, trading yield, refund, excess, swap output, and remove output may need category separation for display and accounting, but that belongs to parsed facts and projections.

## OI-009 Terminal Intent Compaction

Status: Open

Problem: terminal intents should not grow without bound, but stale follow-up rejection, diagnostics, and audit facts may still be needed.

Constraint: compaction must not remove active custody or claim accounting state.
