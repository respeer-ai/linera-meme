# Liquidity And Funds Semantics

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Canonical LP, position, and fund-consistency semantics.

## Facts

- Affected Modules:
  - `pool/`
  - `swap/`
  - `service/kline/`
  - `webui-v2/`
- Read Before:
  - debugging positions
  - reviewing liquidity accounting
  - reviewing refund or payout safety
- Current LP model is V2-like and share-based
- The UI term `LMM` represents liquidity share, not a separately traded token
- User-facing positions should use V2 semantics such as `active` and `closed`, not V3 range semantics
- Positions depend on recorded liquidity transactions
- If `AddLiquidity` is absent upstream, positions cannot reconstruct it later
- `added_liquidity = sum(AddLiquidity.liquidity)`
- `removed_liquidity = sum(RemoveLiquidity.liquidity)`
- `current_liquidity = added_liquidity - removed_liquidity`
- `current_liquidity > 0` means `active`
- `added_liquidity > 0` and `current_liquidity = 0` means `closed`
- Add-liquidity two-leg flows can partially succeed and still fail later
- Payout and refund paths must not silently swallow downstream token-transfer failures
- Initial pool creation must not persist success if downstream initialization or funding failed
- Linera `tracked + bouncing` can help convert a destination-chain reject into a native source-chain failure signal, but only for that one message hop
- `tracked + bouncing` does not provide atomicity or end-to-end rollback for later async payout or refund hops
- Grant refunds in bouncing flows concern message execution resources, not business-asset refunds

## Implications

- When debugging missing LP share or missing positions, inspect both minted liquidity state and transaction persistence
- When reviewing fund safety, inspect partial-success branches, refund branches, and downstream call failure handling
- When designing reliable refund paths, tracked messages may be used to close the gap between `pending` and `failed` for a single cross-chain step
- Do not rely on bouncing messages to recover business funds after a later hop has already diverged; that still requires explicit pending/commit/claim-style protocol design
