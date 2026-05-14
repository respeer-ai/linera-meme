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
- open intents that hold or reference funds in custody

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

`TokenIdentity` means the canonical asset identity used by the current contract model. It does not require a new enum. If the pool contract represents the native asset as `None` in `Option<ApplicationId>` and meme/application assets as `Some(application_id)`, claim balances should use the same canonical representation rather than translating it into a second token model.

This must not be flattened into one global compound key such as `(owner_account, token_identity)`, and it must not be stored owner-first. Token-first storage is more economical for a pool application because each token identity appears once at the outer level, while account balances live under that token.

Connected-owner claim lists are product reads and should be served from parsed facts/projection APIs. They must not require scanning contract storage at UI read time.

The contract must not include product/accounting buckets in the claim-balance key. Category display belongs to parsed facts and projections.

All owed-value categories exit through `Claim { token_identity, amount }`.

## Workflow State

Workflow state exists for business safety while a cross-chain action is not terminal. It does not compensate for duplicate execution of the exact same operation or message; that is a Linera core protocol guarantee.

Required intent classes:

- `PoolCreationIntent`
- `PoolInitialLiquidityIntent`
- `AddLiquidityIntent`
- `SwapIntent`
- `RemoveLiquidityIntent`

Intent state must carry enough data to reject forged, stale, wrong-chain, wrong-app, wrong-token, wrong-leg, or wrong-state follow-up effects.

Intent identity must be allocated by the application that stores the canonical workflow intent state. For user pool creation, the canonical `PoolCreationIntent` is stored in `swap` application state on the swap chain. Store a persistent monotonic `next_intent_seq` in `swap` application state and allocate `intent_id = (swap_application_id, intent_seq)` or an equivalent typed value. The id must be stable across all internal messages and receipts for that workflow. Frontend input, wall-clock timestamps, token pairs, and message delivery order are not valid uniqueness sources.

Pool-local state may reference the same `intent_id` after receiving a swap-authored message, but it must not allocate a second canonical id for that same pool-creation workflow. Cross-chain storage is not shared. Consistency is established by carrying the id through messages and validating source chain, authenticated caller/application, expected pool chain/application, pair, and current status on the receiving chain.

## Terminal Handling

When a workflow succeeds:

- move value into reserves, positions, or claim balances
- mark the intent terminal
- keep only the minimum terminal state required for stale follow-up rejection, diagnostics, and audit

When a workflow fails with funds in custody:

- credit the owner claim balance
- mark the intent terminal or failed with credited status
- do not leave funds only in an opaque intent

When a workflow stalls without failure evidence:

- keep the intent open
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
