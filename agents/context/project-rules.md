# Project Rules

Type: Rules
Audience: Coding assistants
Authority: High

## Facts

- The only task board is [`../tasks/board.yaml`](../tasks/board.yaml)
- Assistant-facing durable knowledge belongs under `agents/` or in directory-local `AGENTS.md`
- Human-facing plans, proposals, reports, and background belong under `documents/`
- Chain contracts are protocol truth
- `service/kline` is an off-chain aggregation layer, not protocol truth
- Frontend should consume APIs and wallet state, not invent protocol state

## Rules

- Unless the user explicitly asks for human-facing docs, write docs for assistants
- Default assistant docs belong either under `agents/` or in directory-scoped `AGENTS.md` files near the code they govern
- Optimize assistant docs for execution and maintenance, not for human readability
- For assistant docs with non-trivial semantics, prefer Markdown with a fixed section contract over forcing pure YAML or TOML
- Use YAML for navigation, indexes, and task metadata; use Markdown for semantics, rules, implications, and workflows
- Before changing files in a directory, check for a local `AGENTS.md` in that directory or its parent directories
- Do not create feature-specific task boards
- Do not treat plan documents as task sources
- Do not introduce parallel "latest" versions of the same assistant doc
- If a document is superseded, update or remove it instead of leaving competing copies
- Do not patch frontend display for problems that originate upstream in contracts or data services
- Do not convert silent handling into hard errors without first auditing all call sites
- Before changing a silent `Ok(())` or no-op path, classify it as one of:
  - required idempotency for duplicate or replayable internal messages
  - explicit user-facing invalid input that should fail loudly
  - a mixed case that should be handled differently at different layers
- When silent handling is intentional for idempotency, keep the state transition safe and add tests for duplicate delivery
- When silent handling hides invalid user input, prefer explicit errors, but verify the caller or handler layer can surface them without breaking legitimate retry paths
- Do not design local or k8s init flows that require reading a wallet after the corresponding service has started if that service may lock the wallet
- Any runtime dependency needed after service startup, such as owner, chain id, or imported-chain metadata, must be resolved before the service starts and carried forward by the init flow without re-reading locked wallets
- When investigating transactions, positions, pool state, or other runtime data during development, default to querying through the relevant API or local service interface first; do not assume `kubectl` access exists on the development machine
- Use `kubectl` for runtime inspection only when the user explicitly asks for cluster-level checks or when the task is clearly a k8s environment issue rather than an application/API issue
- Update [`../tasks/board.yaml`](../tasks/board.yaml) when work meaningfully changes status
- Prefer concise rows over prose-heavy plans inside the task board
- Keep completed tasks for history, but move stable conclusions into `context/` or `primitives/`
- Prefer targeted tests first
- When running `cargo test`, always apply explicit memory limits to avoid host lockups
- Do not run `cargo test` without an explicit memory limit
- Treat the limit as an explicit virtual-memory cap such as `ulimit -v`, not as a requirement that the host must have the same amount of physical RAM
- For Wasmer-heavy Rust suites, increase the virtual-memory cap gradually if module instantiation still fails with `os error 12`; the required cap can be higher in sandboxed or containerized environments than on a developer's local machine
- For heavy Rust tests, reduce parallelism and memory pressure further
- For async contract flows, test both happy path and message-chain failure or duplication edges

## Checklist

1. Read code path before patching
2. Read chain/app/service/db state before patching
3. Identify root cause before patching
4. Patch only after the evidence chain is explicit
5. Add or update tests
6. Update [`../tasks/board.yaml`](../tasks/board.yaml) if task status changed
