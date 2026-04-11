# Pool Contract Rules

Type: Rules
Audience: Coding assistants
Authority: High

## Purpose

Local rules for `pool/` contract logic, async liquidity flow, and tests.

## Facts

- Scope:
  - applies to `pool/`
- Primary Files:
  - `src/contract.rs`
  - `src/contract_impl.rs`
  - `src/contract_inner.rs`
  - `src/state.rs`
  - `src/interfaces.rs`
  - `src/contract_tests.rs`
  - `tests/*.rs`
- High-Risk Semantics:
  - add/remove liquidity is asynchronous and message-driven
  - transaction persistence is separate from initiating operations
  - fund success/fail handling can cause funds-consistency issues

## Rules

- Do not assume initiating `operation` success implies liquidity minted or transaction persisted
- Trace `FundRequest`, follow-up messages, `AddLiquidity`, and `NewTransaction` separately
- Do not change silent/no-op behavior without auditing duplicate-delivery and retry semantics
- When changing ownership-sensitive behavior, preserve authenticated-origin semantics; do not trust payload actor fields for current-caller actions
- When changing funds flow, review:
  - partial success branches
  - refund branches
  - payout branches
  - downstream call failures
- Any change to liquidity or transaction history behavior should add or update contract/integration tests

## Checklist

- Message-chain termination point understood
- Funds-consistency branches reviewed
- Duplicate-delivery semantics reviewed
- Contract/integration tests updated
