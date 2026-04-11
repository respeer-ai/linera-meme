# Project Facts

Type: Facts
Audience: Coding assistants
Authority: High

## Module Map

- `meme/`
  - token contract, mining, approvals, redemption, liquidity funding support
- `pool/`
  - liquidity pool contract, add/remove liquidity, swaps, transaction queue
- `swap/`
  - router, pool registry, pool creation, pool metadata updates
- `proxy/`
  - governance, miner management, meme creation orchestration
- `service/kline/`
  - off-chain aggregation for transactions, klines, positions
- `webui-v2/`
  - frontend consuming APIs and wallet integrations

## Important Truths

- Missing pool transactions must be debugged upstream before blaming `kline` or frontend
- `pool_application` identifies a pool, not the acting user
- `from_account` is intended to represent the actor identity
- positions depend on recorded liquidity transactions; if `AddLiquidity` is absent upstream, positions cannot recover it

## Sensitive Areas

- pool add/remove liquidity is asynchronous and message-driven
- meme-native liquidity flow has a native-funding branch that deserves extra scrutiny
- `latestTransactions` queue length is capped; tests should cover queue-boundary behavior

## Recent Confirmed Findings

- Recent missing positions were not caused by the 5000-entry transaction window
- live pool inspection showed liquidity funds can appear to move without a corresponding `AddLiquidity` transaction landing in pool history
- contract-level tests now assert that liquidity operations must produce transaction history when the follow-up `NewTransaction` message executes
