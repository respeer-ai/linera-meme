# Assistant Doc Standard

Type: Standard
Audience: Coding assistants
Authority: High

## Facts

- Assistant docs optimize for assistant execution speed, retrieval accuracy, and update consistency
- Assistant docs do not optimize for human reading comfort
- `yaml` is preferred for indexes, navigation, task boards, machine-updated metadata, and stable enumerations with little explanation
- `md` is preferred for semantics, rules, architecture slices, workflows, implications, and checklists with non-trivial exceptions
- Task status lives only in `agents/tasks/board.yaml`
- Each durable fact should have one canonical file

## Rules

- Prefer short bullets over paragraphs
- Prefer explicit assertions over explanation-heavy prose
- Put invariants before examples
- Put prohibitions in bullets starting with `Do not`
- Put required sequences in numbered lists
- Put file or path references inline using exact repo paths
- Avoid motivational or conversational wording
- Avoid historical narrative unless it changes current execution
- Avoid duplicate facts across files when one file can be canonical
- If a fact is reused, point to the canonical file instead of re-explaining it
- If a file is superseded, update or delete it; do not leave parallel versions
- Do not keep live status in prose docs
- If a runbook or context file mentions a task, reference its task id only

## Checklist

1. Use this front matter in assistant-facing Markdown:
   ```md
   # <doc title>

   Type: <Rules|Context|Primitive|Runbook|Standard>
   Audience: Coding assistants
   Authority: <High|Medium|Low>
   ```
2. Use only needed sections from:
   - `Purpose`
   - `Facts`
   - `Rules`
   - `Semantics`
   - `Flow`
   - `Implications`
   - `Checklist`
   - `Commands`
   - `Validation`
   - `Sources`
3. Update the canonical file first
4. Update `agents/index.yaml` if navigation changes
5. Remove stale references
6. Keep formatting consistent with this standard
