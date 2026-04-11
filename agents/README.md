# agents/

- assistant-only operating layer
- `documents/` is human-facing
- read order:
  1. `index.yaml`
  2. `context/project-rules.md`
  3. `context/doc-standard.md`
  4. `tasks/board.yaml`
  5. nearest local `AGENTS.md`
  6. relevant files in `primitives/`, `context/`, `runbooks/`
- hard rules:
  - only live task source is `tasks/board.yaml`
  - do not keep competing assistant truth in `documents/`
  - promote durable conclusions into `context/` or `primitives/`
  - check nearest `AGENTS.md` before editing a directory
