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

## Implications

- When debugging missing LP share or missing positions, inspect both minted liquidity state and transaction persistence
- When reviewing fund safety, inspect partial-success branches, refund branches, and downstream call failure handling
