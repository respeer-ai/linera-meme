# Agents Knowledge Base

Type: Index
Audience: Coding assistants
Authority: High

## Purpose

This directory is the assistant-oriented knowledge layer for the whole project.

- `documents/` is for human-facing material
- `agents/` is for coding assistants
- task tracking, project facts, and engineering rules should converge here

## Reading Order

1. [`PROJECT_RULES.md`](./PROJECT_RULES.md)
2. [`PROJECT_FACTS.md`](./PROJECT_FACTS.md)
3. [`PROJECT_TASK_BOARD.md`](./PROJECT_TASK_BOARD.md)

## File Roles

- [`PROJECT_RULES.md`](./PROJECT_RULES.md)
  - workflow rules, source-of-truth rules, and editing constraints specific to this project
- [`PROJECT_FACTS.md`](./PROJECT_FACTS.md)
  - stable project facts, module boundaries, and frequently-misunderstood truths
- [`PROJECT_TASK_BOARD.md`](./PROJECT_TASK_BOARD.md)
  - the only task board for the project

## Maintenance Rules

- Do not create a second task board
- Do not place assistant-only operating rules in `documents/`
- When a temporary investigation becomes durable knowledge, move the conclusion into
  `PROJECT_FACTS.md` or `PROJECT_RULES.md`
