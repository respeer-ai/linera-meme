# Cross-Chain Execution Semantics

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Canonical execution semantics for operation, message, replica, and application-call behavior.

## Facts

- Affected Modules:
  - `pool/`
  - `swap/`
  - `proxy/`
  - `meme/`
- Read Before:
  - debugging async contract behavior
  - reviewing message-driven flows
  - reasoning about wrong-chain execution

## Semantics

- For Linera contracts here, an `operation` only handles the current transaction and queues outgoing messages
- An `operation` does not synchronously execute later hops in the message chain
- State mutations from one `operation` or one `message` are flushed when that transaction ends
- Later cross-chain or same-chain messages persist in their own subsequent transactions
- The same application on different chains has different state replicas
- Any analysis must name the execution chain explicitly
- An `operation` reads and writes only the current chain's replica of that application
- A `message` reads and writes the destination chain's replica of that application, not the sender's replica
- An `application call` executes on the caller chain against the callee application's local replica on that same chain
- An `application call` does not jump to the callee creator chain
- In `pool`, `PoolOperation::AddLiquidity` only creates `FundRequest`s and queues funding messages
- `PoolOperation::AddLiquidity` does not mint liquidity or write transaction history
- In `pool`, `PoolMessage::FundSuccess` persists `FundStatus::Success` and may queue follow-up `RequestFund` or `AddLiquidity`
- Queued follow-up messages are not yet executed state changes
- Liquidity is minted only when `PoolMessage::AddLiquidity` executes
- `PoolMessage::NewTransaction` is the settled pool fact carrier and catalog-update trigger
- Building a transaction struct or queueing the message is not equivalent to a settled fact
- Pool contracts must not keep a product-facing transaction-history queue; observability derives product history from parsed blocks
- `SwapOperation::UpdatePool` is currently a public operation surface for catalog updates
- Risk: if external callers can invoke `UpdatePool` directly, they may spoof pool catalog reserve/price updates
- Do not rely on transaction cursors to secure `UpdatePool`; the correct mitigation is source/authentication validation or narrowing the callable surface
- Linera `tracked` messages only guarantee a receipt when that specific destination-chain message is rejected
- A rejected tracked message is returned as a protocol-generated bouncing message to the sender chain
- Contracts can detect the bounced receipt with `message_is_bouncing()`
- `tracked + bouncing` applies to one message hop, not to an entire multi-hop business workflow
- If hop N succeeds but a later hop fails, hop N will not be automatically bounced
- Therefore `tracked + bouncing` can be used as a native reject-receipt mechanism for one-hop failure handling, but it cannot replace explicit pending/success/fail protocol state across multi-hop flows

## Implications

- If funds moved but no transaction exists, inspect the async message chain and termination point
- Never assume a successful initiating operation implies completed downstream state changes
- When designing refund or rollback behavior, use `tracked` for critical one-hop messages where a native reject receipt is valuable
- Do not treat a non-bounced tracked message as proof that the whole workflow completed; it only proves that hop was not rejected
- Multi-hop flows such as swap, payout, refund, or liquidity funding still require explicit intent IDs, pending states, and success-only finalization
