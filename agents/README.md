# agents/

- assistant-only operating layer
- `documents/` is human-facing
- read order:
  1. `index.yaml`
  2. `context/project-rules.md`
  3. `context/doc-standard.md`
  4. `context/prompt-economy.md`
  5. `tasks/prompt-state.yaml`
  6. `tasks/board.yaml` only when needed by `prompt-state.yaml` or when updating task status
  7. nearest local `AGENTS.md`
  8. relevant files in `primitives/`, `context/`, `runbooks/`
- hard rules:
  - only live task source is `tasks/board.yaml`
  - `tasks/prompt-state.yaml` is derived prompt-routing state, not a task source
  - do not keep competing assistant truth in `documents/`
  - promote durable conclusions into `context/` or `primitives/`
  - check nearest `AGENTS.md` before editing a directory
- maintenance:
  - validate prompt routing state with `python3 scripts/validate_prompt_state.py` after changing task status or prompt-state membership
