# Skills

Type: Skills Index
Audience: Coding assistants
Authority: High

## Purpose

Project-local skills are the canonical executable workflows for this repository.

## Rules

- Store each skill at `agents/skills/<skill-name>/SKILL.md`
- Use lowercase kebab-case skill names
- When the user writes `@skill:<skill-name>`, load `agents/skills/<skill-name>/SKILL.md` before acting
- When a task matches a route in `agents/index.yaml`, load the listed skill before acting
- Keep full workflow steps inside the skill or its local `references/` and `assets/`
- Do not create `agents/runbooks/` or parallel workflow documents
- Do not duplicate durable architecture facts from `agents/primitives/`; link to the primitive instead
- Keep generated or temporary investigation code outside product paths unless the skill explicitly stores a reusable template under its own `assets/`
