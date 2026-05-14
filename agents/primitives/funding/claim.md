# Claim And Funds Exit

Type: Primitive
Audience: Coding assistants
Authority: High

## Rule

`Claim` is the only user-facing funds-exit operation.

Refund, retry, excess withdrawal, protocol-fee withdrawal, remote-liquidity withdrawal, and trading-yield withdrawal are claim-accounting meanings. They are not separate user product operations.

## Claimable State

Long-lived owed value should be represented as aggregated claim balances:

```text
claim_balances[token_identity].balances[owner_account] += amount
```

Historical details and category/bucket display belong in parsed facts and projections, not in contract claim-balance keys.

The on-chain storage must use a two-level map:

- first level: `token_identity`
- second level: `owner_account`

`token_identity` must use the pool contract's canonical token representation. If the current implementation represents native as `None` and application tokens as `Some(ApplicationId)`, keep that representation instead of introducing a parallel token enum.

This keeps each token identity stored once at the outer level and avoids repeating token keys for every account. User-facing claim lists should be served from projection/API data rather than by scanning contract storage at product-read time.

## Claim Operation

Target ABI:

```text
PoolOperation::Claim { token_identity, amount }
```

Rules:

- owner authorization
- owner is derived from the authenticated operation account, following existing pool operation semantics; do not accept an owner payload field for `Claim`
- token identity
- available claim balance check
- `amount > 0`
- no claim key and no per-claim queue
- category/bucket display is a data-platform concern

## Native Claim

Native/TLINERA claim executes synchronously on the pool chain.

Rules:

- Validate owner and available claim balance.
- Execute native transfer.
- Decrement or consume claim balance only in the same successful transaction.
- If native transfer aborts/panics, the transaction does not commit and claim balance remains unchanged.
- Do not depend on catching native transfer failure as a business response.

## Meme Token Claim

Meme token claim is asynchronous and requires delivery-attempt state.

State:

- available claim balance
- frozen/pending delivery amount
- active `ClaimDeliveryAttempt`

Flow:

1. User submits `Claim`.
2. Pool validates owner and available balance.
3. Pool freezes or deducts the amount into pending delivery state.
4. Pool creates `ClaimDeliveryAttempt`.
5. Pool sends payout/transfer message to the meme application.
6. Success acknowledgement marks attempt succeeded.
7. Fail or bounce returns the amount to available claim balance.
8. While pending, the frozen amount cannot be claimed again.

Required attempt fields:

- `attempt_id`
- `owner_account`
- `token_identity`
- `amount`
- `destination_account`
- `destination_application`
- `destination_chain`
- `status`
- `outbound_message_key`
- `failure_reason`

## Forever Pending Delivery

The target meme chain may never execute the payout message.

Rules:

- Do not automatically mark the attempt failed.
- Do not allow the same frozen amount to be claimed again.
- Do not design timeout-based retry unless a future protocol can prove old delivery cannot execute.
- Expose pending delivery through projection and diagnostics.

Resolution: Open. A future cancel/expiry/retry design must be state-specific and prove no double payout.

## No Generic Resume

Do not introduce `Resume`, `RetryClaim`, or `Refund` as user product operations.

Any future recovery operation must be:

- scoped to one concrete state
- justified against Linera's core once-only execution model
- unable to violate custody or accounting safety
- explicitly documented in the relevant state machine
