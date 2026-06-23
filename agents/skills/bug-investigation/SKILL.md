# Bug Investigation Skill

Type: Skill
Audience: Coding assistants
Authority: High

## Purpose

Default workflow for bug investigation and root-cause-first fixing.

## Facts

- Inputs:
  - user-reported bug or failing behavior
  - accessible code path
  - accessible runtime evidence such as chain state, service state, database rows, or logs
- Outputs:
  - explicit root cause
  - code change if warranted
  - regression tests
  - updated task status if applicable
- Stop Conditions:
  - root cause proven and fixed
  - or blocker identified that cannot be resolved from current environment

## Flow

1. Read [`../../context/project-rules.md`](../../context/project-rules.md)
2. Read [`../../context/doc-standard.md`](../../context/doc-standard.md)
3. Read [`../../context/prompt-economy.md`](../../context/prompt-economy.md)
4. Read [`../../tasks/prompt-state.yaml`](../../tasks/prompt-state.yaml)
5. Read the nearest directory-local `AGENTS.md`
6. Inspect the relevant primitive semantics before touching code
7. Trace the code path end to end
8. Inspect live chain state, service state, database rows, or logs as appropriate
9. Identify the first broken state transition, not just the final bad UI symptom
10. Patch only after the evidence chain is explicit
11. Add or update tests for the failure mode
12. Update [`../../tasks/board.yaml`](../../tasks/board.yaml) if the work changes task status
13. Update [`../../tasks/prompt-state.yaml`](../../tasks/prompt-state.yaml) if prompt relevance changed
14. Run `python3 scripts/validate_prompt_state.py` if either task file changed

## Rules

- Do not patch UI for upstream data bugs
- Do not stop at the first suspicious layer if protocol truth may be wrong
- For async flows, identify where the message chain stops
- For ownership bugs, trace authenticated identity end to end
