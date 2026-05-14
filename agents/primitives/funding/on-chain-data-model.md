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
- active/pending/failed catalog state
- open intents that hold or reference funds in custody
- active claim delivery attempts

## Claim Balances

Claim balances are aggregated accounting balances, not append-only per-event queues.

Recommended key shape:

- `pool_app`
- `owner_account`
- `token_identity`
- optional `bucket`

The `bucket` may distinguish product/accounting categories such as:

- swap output
- remove output
- refund
- excess
- protocol fee
- remote liquidity
- trading yield

The bucket must not create separate user funds-exit operations. All buckets are exited through `Claim`.

## Workflow State

Workflow state exists for safety and idempotency while a business action is not terminal.

Required intent classes:

- `PoolCreationIntent`
- `PoolInitialLiquidityIntent`
- `AddLiquidityIntent`
- `SwapIntent`
- `RemoveLiquidityIntent`
- `ClaimDeliveryAttempt`

Intent state must carry enough data to reject forged, stale, duplicate, wrong-chain, wrong-app, wrong-token, and wrong-leg follow-up effects.

## Terminal Handling

When a workflow succeeds:

- move value into reserves, positions, or claim balances
- mark the intent terminal
- keep only the minimum state required for duplicate handling and audit

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
- historical delivery-attempt metadata beyond the active attempt
- derived stalled-workflow indexes
- API caches

Quotas must never delete protocol accounting state.
