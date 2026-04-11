# Project Rules

Type: Rules
Audience: Coding assistants
Authority: High

## Source Of Truth

- The only task board is [`PROJECT_TASK_BOARD.md`](./PROJECT_TASK_BOARD.md)
- Assistant-facing durable project knowledge belongs under `agents/`
- Human-facing plans, proposals, and background belong under `documents/`

## Documentation Rules

- Do not create feature-specific task boards
- Do not treat plan documents as task sources
- Do not introduce parallel "latest" versions of the same assistant doc
- If a document is superseded, update or remove it instead of leaving competing copies

## Debugging Rules

- For product bugs:
  1. inspect code path
  2. inspect chain/app state or live service data
  3. identify root cause
  4. patch only after the chain of evidence is clear
- Do not patch frontend display for problems that originate upstream in contracts or data services

## Responsibility Boundaries

- chain contracts are the protocol truth
- `service/kline` is an off-chain aggregation layer, not protocol truth
- frontend should consume APIs and wallet state, not invent protocol state

## Task Board Rules

- Update task status in [`PROJECT_TASK_BOARD.md`](./PROJECT_TASK_BOARD.md) when work meaningfully changes status
- Prefer adding concise tasks over large prose in the board
- Keep completed tasks for history, but move design detail to facts or human docs

## Test Rules

- Prefer targeted tests first
- When running heavy Rust tests, reduce parallelism and memory pressure
- For async contract flows, test both happy path and message-chain failure/duplication edges
