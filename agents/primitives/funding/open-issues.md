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

Current safe behavior: keep intent stalled/pending; do not activate; do not resend non-idempotent create message.

Unsafe shortcuts:

- timeout-based activation
- opening another pool for the same pair
- generic resume

## OI-002 Shell Receipt Never Reaches Swap

Status: Open

Affected flow: user `CreatePool`, meme native pool initialization.

Problem: pool shell may exist while swap catalog never receives the receipt.

Current safe behavior: shell is not active/tradable; projection may show stalled shell if facts are available.

Unsafe shortcuts:

- treating shell existence as active catalog truth
- allowing users to trade directly against shell

## OI-003 One Funding Leg Pending Forever

Status: Open

Affected flow: create pool initial liquidity, add liquidity.

Problem: one leg may be funded while the opposite leg never executes and never fails.

Current safe behavior: keep funded custody value in stalled intent; do not reserve, mint, refund, or claim unless explicit failure evidence exists.

Unsafe shortcuts:

- timeout refund
- retrying non-idempotent funding
- minting one-sided LP

## OI-004 Finalized Pool Activation Receipt Missing

Status: Open

Affected flow: create pool initial liquidity.

Problem: pool may finalize reserves and mint LP while activation receipt never reaches swap catalog.

Current safe behavior: do not recreate pool or mint again; do not mark swap catalog active without a valid activation transition.

Unsafe shortcuts:

- rebuild pool
- infer active from pool finalized state without a designed reconciliation path

## OI-005 Meme Claim Delivery Pending Forever

Status: Open

Affected flow: meme token `Claim`.

Problem: pool may send meme payout message and freeze claim balance while target chain never executes the message.

Current safe behavior: keep delivery pending; do not allow the frozen amount to be claimed again; expose pending delivery through projection.

Unsafe shortcuts:

- timeout retry
- returning frozen amount to available balance without proof old delivery cannot execute

## OI-006 Recovery Operations

Status: Deferred

Problem: future operational recovery may be needed.

Decision: do not design a generic `Resume`. Any recovery operation must be state-specific, idempotent, and proven not to double-pay, double-mint, double-create, or double-credit.

## OI-007 Claim ABI Shape

Status: Open

Options:

- `Claim { token_identity, amount }`
- `Claim { claim_key, amount }`
- `Claim { token_identity }`

Decision criteria:

- authorization clarity
- bucket support
- frontend UX
- duplicate handling
- projection/API compatibility

## OI-008 Claim Balance Bucket Design

Status: Open

Problem: protocol fee, remote liquidity, trading yield, refund, excess, swap output, and remove output may need category separation for display and accounting.

Constraint: bucket separation must not create separate funds-exit operations.

## OI-009 Terminal Intent Compaction

Status: Open

Problem: terminal intents should not grow without bound, but duplicate protection and audit facts may still be needed.

Constraint: compaction must not remove active custody or claim accounting state.
