# Assistant Entry

For coding assistants, project-specific instructions live under [`agents/`](./agents).

Start here:

- [`agents/README.md`](./agents/README.md)
- [`agents/index.yaml`](./agents/index.yaml)
- [`agents/context/project-rules.md`](./agents/context/project-rules.md)
- [`agents/tasks/board.yaml`](./agents/tasks/board.yaml)

Project-local skills:

- Skills live under [`agents/skills/`](./agents/skills).
- When the user writes `@skill:<skill-name>`, names a project skill, or asks for a workflow covered by `agents/skills/index.yaml`, load `agents/skills/<skill-name>/SKILL.md` before acting.
- Treat `agents/skills/` as the only canonical home for executable assistant workflows.
