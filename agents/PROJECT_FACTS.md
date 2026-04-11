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
- For Linera contracts here, `operation` only handles the current transaction and queues outgoing messages; it does not synchronously execute later hops in the message chain
- State mutations from one `operation` or one `message` are flushed when that transaction ends; later cross-chain or same-chain messages persist in their own subsequent transactions
- The same application on different chains has different state replicas; any analysis must name the execution chain explicitly
- An `operation` reads and writes only the current chain's replica of that application
- A `message` reads and writes the destination chain's replica of that application, not the sender's replica
- An `application call` executes on the caller chain against the callee application's local replica on that same chain; it does not jump to the callee creator chain
- In `pool`, `PoolOperation::AddLiquidity` only creates `FundRequest`s and queues funding messages; it does not mint liquidity or write transaction history
- In `pool`, `PoolMessage::FundSuccess` persists `FundStatus::Success` and may queue follow-up `RequestFund` or `AddLiquidity`, but queued messages are not yet executed state changes
- In `pool`, liquidity is minted only when `PoolMessage::AddLiquidity` executes
- In `pool`, transaction history is recorded only when `PoolMessage::NewTransaction` executes `create_transaction`; building a transaction struct or queueing the message is not equivalent to persistence
- Some silent / idempotent paths are intentional for duplicate internal message delivery; not every no-op should be converted into an error
- For user-initiated contract actions, silent no-op can hide invalid state or wrong-chain execution; callers and handlers must be audited before changing this behavior
- In this project, `claim` / `redeem`-style actions mean "for the current authenticated caller"; the authenticated subject should come from runtime identity, and cross-chain delivery should preserve or reconstruct origin rather than trusting a payload `owner`

## Sensitive Areas

- pool add/remove liquidity is asynchronous and message-driven
- meme-native liquidity flow has a native-funding branch that deserves extra scrutiny
- `latestTransactions` queue length is capped; tests should cover queue-boundary behavior

## Recent Confirmed Findings

- Recent missing positions were not caused by the 5000-entry transaction window
- live pool inspection showed liquidity funds can appear to move without a corresponding `AddLiquidity` transaction landing in pool history
- contract-level tests now assert that liquidity operations must produce transaction history when the follow-up `NewTransaction` message executes
