# Identity And Origin Semantics

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Canonical actor-binding and origin-tracing rules.

## Facts

- Affected Modules:
  - `pool/`
  - `meme/`
  - `ams/`
  - `service/kline/`
- Read Before:
  - debugging claim or redeem issues
  - reviewing actor identity usage
  - verifying transaction actor persistence

## Rules

- For user-bound actions such as `claim`, `redeem`, and similar "act for current caller" semantics, the effective actor must come from runtime authentication, not from request payload fields
- If such an action crosses chains, recover the actor from authenticated origin or message context on the destination chain
- `origin` means the initial operation account that started the workflow
- When a later internal message needs to preserve the identity of the initial workflow starter, carry that fact explicitly as `origin`
- All later internal messages derived from the same workflow must use that same `origin` when they need to express the initial workflow starter
- `origin` is not the same thing as the current hop runtime actor
- Do not store `origin` as a default base field on every intent
- Prefer runtime chain facts such as `authenticated_account()` and `message_signer_account()` when they express the exact business fact needed by the current hop
- Carry `origin` only when the current hop specifically needs the initial operation account and runtime chain facts on that hop cannot express it directly
- Do not trust a caller-provided `owner` or `operator` field as the security boundary
- Payload fields may identify the target object being acted on, but not the authenticated subject when the intent is "current caller only"
- `pool_application` identifies a pool, not the acting user
- `from_account` is intended to represent the actor identity
- Positions and liquidity ownership views depend on `from_account` being recorded correctly upstream

## Implications

- When checking ownership bugs, trace authenticated origin from wallet or runtime through operation, message, and final transaction persistence
