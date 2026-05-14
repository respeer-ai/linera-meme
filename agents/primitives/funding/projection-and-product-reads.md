# Funding Projection And Product Reads

Type: Primitive
Audience: Coding assistants
Authority: High

## Rule

Product-facing funding data must come from parsed block facts and projections, not live chain queries.

## Projection-Backed Product Data

These must be projection/API-backed:

- pools
- tokens
- transactions
- candles
- volume
- TVL
- APR inputs
- positions
- virtual positions
- claim balances
- pending workflow display
- stalled workflow display
- protocol yield
- trading yield
- diagnostics and reconciliation views

## Allowed Live Query

Live query is allowed for:

- wallet/account/chain identity
- operation submission
- explicitly labeled live wallet balance

Live query is not allowed to reconstruct product accounting truth.

## Required Protocol Facts

Protocol changes must emit or preserve facts sufficient to derive:

- intent created
- pool shell created
- pool created
- pool active
- leg funded
- intent failed
- value credited to claim balance
- claim started
- claim delivery pending
- claim delivery succeeded
- claim delivery failed
- position changed
- reserve changed
- virtual position created

## Pagination

Projection/API must paginate:

- claim balances
- positions
- transactions
- stalled intents
- diagnostic history
- delivery attempts/history

Do not solve product pagination by deleting protocol accounting state.

## Diagnostic Quotas

Diagnostic, debug, and monitoring persistence must be bounded by TTL, max rows, or equivalent quota.

Quota may shed non-business diagnostic data only. It must not delete claim balances, positions, reserves, or open intents with funds in custody.
