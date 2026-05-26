# Claim And Funds Exit

Type: Primitive
Audience: Coding assistants
Authority: High

## Rule

`Claim` is the only user-facing funds-exit operation.

Refund, retry, excess withdrawal, protocol-fee withdrawal, remote-liquidity withdrawal, and trading-yield withdrawal are claim-accounting meanings. They are not separate user product operations.

## Claimable State

Long-lived owed value must be represented as aggregated claim balances:

```text
claim_balances[token_identity].balances[owner_account] += amount
claiming_balances[token_identity].balances[owner_account] += amount
```

Historical details and category/bucket display belong in parsed facts and projections, not in contract claim-balance keys.

The on-chain storage must use a two-level map:

- first level: `token_identity`
- second level: `owner_account`

`token_identity` must use an explicit token identity enum. Use `MemeToken::Native` for the native asset and `MemeToken::Fungible(ApplicationId)` for meme/fungible tokens. Do not use a claim-specific name such as `ClaimToken`: native is a token identity, not a claim-only concept.

Existing protocol surfaces still use `Option<ApplicationId>` in several places. `FUND-008` must not refactor unrelated pool catalog, proxy, frontend, or observability token representations. Convert those boundary values into `MemeToken` at the claim-accounting boundary. Record a separate follow-up before any project-wide token-identity unification.

`claim_balances` is available-to-claim value. `claiming_balances` is aggregated in-flight claim value after a user starts an asynchronous meme-token claim. Both maps use the same token-first, owner-second shape.

This keeps each token identity stored once at the outer level and avoids repeating token keys for every account. User-facing claim lists must be served from projection/API data rather than by scanning contract storage at product-read time.

Claim-balance accounting must exist before any workflow credits owed value to claim balances. The user-facing `Claim` operation may be delivered in the same iteration as the accounting foundation or earlier than the first workflow that credits owed value, but it must not be delivered later than the first owed-value credit path.

## Claim Operation

Target ABI:

```text
PoolOperation::Claim { token: Option<ApplicationId>, amount }
```

`token = None` means the native asset. `token = Some(application_id)` means a meme/application token and must match one of the current pool tokens.

Rules:

- owner authorization
- owner is derived from the authenticated operation account, following existing pool operation semantics; do not accept an owner payload field for `Claim`
- token identity
- available claim balance check
- `amount > 0`
- no claim key, no per-claim queue, and no per-claim attempt id
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

Meme token claim is asynchronous and uses aggregated `claiming_balances`, not per-claim delivery attempts.

State:

- available claim balance
- in-flight claiming balance

Flow:

1. User submits `Claim`.
2. Pool validates owner and available balance.
3. Pool moves `amount` from `claim_balances[token][owner]` to `claiming_balances[token][owner]`.
4. Pool calls `MemeOperation::TransferFromApplicationWithReceipt` on the meme application.
5. Success acknowledgement decreases `claiming_balances[token][owner]` by `amount`.
6. Fail or bounce decreases `claiming_balances[token][owner]` by `amount` and returns it to `claim_balances[token][owner]`.
7. While in `claiming_balances`, the amount is unavailable for another claim.

The meme transfer receipt ABI for `FUND-008` is:

```text
MemeOperation::TransferFromApplicationWithReceipt {
    to: Account,
    amount: Amount,
    receipt: TransferFromApplicationReceipt,
}

MemeMessage::TransferFromApplicationWithReceipt {
    caller: Account,
    to: Account,
    amount: Amount,
    receipt: TransferFromApplicationReceipt,
}

TransferFromApplicationReceipt {
    pool_chain: ChainId,
    pool_application: ApplicationId,
    payload: TransferFromApplicationReceiptPayload,
}

TransferFromApplicationReceiptPayload::PoolClaim {
    owner: Account,
    token: ApplicationId,
    amount: Amount,
    destination: Account,
}
```

The existing receipt-free `TransferFromApplication` remains available for paths not migrated in `FUND-008`. After all protocol funds paths are migrated to receipt-first application transfer, the receipt-free variant can be removed and the default `TransferFromApplication` can carry a receipt. Pool claim receipt handlers validate source chain, authenticated caller, pool application, token application, owner, amount, and `claiming_balances[token][owner] >= amount`. Linera core once-only execution is the duplicate-delivery boundary for the exact same message; the application does not add per-attempt ids.

`FUND-008` tests may seed claim balances through contract test fixtures or internal test helpers. Do not add a production debug operation or public ABI solely to create claim balances for tests.

## Forever Pending Claiming Balance

The target meme chain may never execute the payout message.

Rules:

- Do not automatically mark the claiming balance failed.
- Do not allow the same in-flight amount to be claimed again.
- Do not design timeout-based retry unless a future protocol can prove old delivery cannot execute.
- Expose pending claiming balance through projection and diagnostics.

Resolution: Open. A future cancel/expiry/retry design must be state-specific and prove no double payout.

## No Generic Resume

Do not introduce `Resume`, `RetryClaim`, or `Refund` as user product operations.

Any future recovery operation must be:

- scoped to one concrete state
- justified against Linera's core once-only execution model
- unable to violate custody or accounting safety
- explicitly documented in the relevant state machine
