# Funding On-Chain Data Model

Type: Primitive
Audience: Coding assistants
Authority: High

## Long-Lived Economic State

These are protocol accounting state and must not be deleted by TTL, diagnostic quota, or cache policy:

- pool reserves
- pool total liquidity
- positions keyed by owner and pool
- claim balances
- claiming balances
- active/pending/failed pair state in `swap` application state
- open workflow state that holds or references funds in custody

## Claim Balances

Claim balances are aggregated accounting balances, not append-only per-event queues.

Required storage shape:

```text
claim_balances: MapView<token_identity, TokenClaimBalances>
claiming_balances: MapView<token_identity, TokenClaimBalances>
TokenClaimBalances.balances: MapView<owner_account, amount>
```

Recommended concrete model:

- `ClaimBalancesByToken = MapView<TokenIdentity, TokenClaimBalances>`
- `TokenClaimBalances { balances: MapView<Account, Amount> }`

`TokenIdentity` means the canonical asset identity used by the current contract model. It does not require a new enum. If the pool contract represents the native asset as `None` in `Option<ApplicationId>` and meme/application assets as `Some(application_id)`, claim balances must use the same canonical representation rather than translating it into a second token model.

This must not be flattened into one global compound key such as `(owner_account, token_identity)`, and it must not be stored owner-first. Token-first storage is more economical for a pool application because each token identity appears once at the outer level, while account balances live under that token.

Connected-owner claim lists are product reads and must be served from parsed facts/projection APIs. They must not require scanning contract storage at UI read time.

The contract must not include product/accounting buckets in the claim-balance key. Category display belongs to parsed facts and projections.

All owed-value categories exit through `Claim { token_identity, amount }`.

## Workflow State

Workflow state exists for business safety while a cross-chain action is not terminal. It does not compensate for duplicate execution of the exact same operation or message; that is a Linera core protocol guarantee.

Workflow state must carry enough data to reject forged or mismatched follow-up effects, but the approved target design now minimizes persisted workflow state to the places where chain facts and direct message choreography are not sufficient.

Required target workflow state:

- swap pair/pool registry state, including protocol pair existence and active/pending/failed pair facts
- concrete per-leg funding state that proves custody and remaining non-terminal branches
- claim balances and claiming balances
- `CreateMemeIntent` and `MemeInitializeLiquidityRoute` as reviewed special cases

Rejected target state classes for the current funding redesign:

- `PoolCreationIntent`
- `PoolInitialLiquidityIntent`
- `AddLiquidityIntent`
- `SwapIntent`
- `RemoveLiquidityIntent`

For user pool creation, consistency is established by carrying immutable create-pool facts such as `token_0`, `token_1`, `amount_0`, `amount_1`, `to`, and explicit `origin` through the required internal messages, and by validating those facts against authoritative chain facts at every hop that can derive them. `origin` means the initial operation account that started the workflow. It is not a generic stored base field; it is carried only on the later messages that need it for pool `creator`, `fee_to`, or share-owner semantics.

Pool usability must not rely on a separate persisted `initialized` bit. The authoritative readiness fact is the presence of finalized reserve/share economics in the pool state itself. A pool application may exist before those facts exist.

Do not allocate synthetic workflow ids where concrete message-carried immutable facts plus authoritative chain facts are sufficient. Frontend input, wall-clock timestamps, token pairs, and message delivery order are not valid uniqueness sources for any state that must be authoritative.

## Terminal Handling

When a workflow succeeds:

- move value into reserves, positions, or claim balances
- mark the workflow state terminal where such state exists
- keep only the minimum terminal state required for stale follow-up rejection, diagnostics, and audit

When a workflow fails with funds in custody:

- credit the owner claim balance
- mark the workflow state terminal or failed with credited status where such state exists
- do not leave funds only in opaque non-terminal workflow state

When a workflow stalls without failure evidence:

- keep the workflow state open
- do not finalize economic state
- expose the stalled state through projection

## Non-Business Data

These may have quotas, retention windows, or compaction:

- debug logs
- diagnostic traces
- historical claim delivery metadata
- derived stalled-workflow indexes
- API caches

Quotas must never delete protocol accounting state, including claim balances and claiming balances.
