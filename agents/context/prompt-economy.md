# Prompt Economy

Type: Context
Audience: Coding assistants
Authority: High

## Purpose

Define how assistant context is minimized without losing correctness.

## Facts

- `agents/tasks/board.yaml` is the only live task source
- `agents/tasks/prompt-state.yaml` is a derived routing artifact, not a task source
- Durable conclusions belong in `agents/context/` or `agents/primitives/`
- Completed-task narrative should not remain the default prompt payload

## Rules

- Read `agents/tasks/prompt-state.yaml` before reading `agents/tasks/board.yaml`
- Read full `agents/tasks/board.yaml` only when at least one of these is true:
  - you need to update task status
  - you need details for a task id listed in `prompt-state.yaml`
  - you need to inspect dependencies or neighboring tasks around an active task
- Do not send completed tasks by default just because they exist in `board.yaml`
- For `Done` tasks, include them in prompt only when at least one of these is true:
  - an active task depends on them semantically
  - they contain unresolved caveats still relevant to active work
  - their durable conclusion has not yet been promoted into canonical `context/` or `primitives/`
- When a `Done` task no longer meets those conditions:
  - remove it from prompt-state active summaries
  - keep it in `board.yaml` for history
  - keep only minimal historical notes in `board.yaml`
- Prefer one-line task summaries in prompt-state
- Prefer references to canonical docs over re-explaining long task history
- If task notes in `board.yaml` become long because they encode durable semantics, move those semantics into canonical docs and replace the task note with a short pointer

## Semantics

- `board.yaml`
  - source of truth for status, priority, dependency, and existence of tasks
- `prompt-state.yaml`
  - source of truth for default prompt inclusion
  - lists current focus tasks, compact summaries, and on-demand task references
  - must be updated whenever task status or prompt relevance changes

## Checklist

1. Update `board.yaml` when task status changes
2. Update `prompt-state.yaml` in the same change when prompt relevance changes
3. Promote durable conclusions out of task notes before adding more narrative
4. Keep default prompt set as small as possible
