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
claim_balances[(pool_app, owner_account, token_identity, bucket?)] += amount
```

Historical details belong in parsed facts and projections.

## Claim Operation

The exact ABI is still open. Candidate shapes:

```text
PoolOperation::Claim { token_identity, amount }
PoolOperation::Claim { claim_key, amount }
PoolOperation::Claim { token_identity }
```

The chosen ABI must preserve:

- owner authorization
- token identity
- pool/accounting context
- optional bucket semantics when needed
- idempotent duplicate handling

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
- idempotent
- unable to double-pay, double-mint, double-create, or double-credit
- explicitly documented in the relevant state machine
