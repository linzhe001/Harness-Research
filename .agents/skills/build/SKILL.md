---
name: build
description: "Visible Harness build entry. Use after prepare to plan and implement the first codebase slice through workflow-supervisor build automation."
---

# Build

Use `$build` as the human-facing alias for the Execution Supervisor `build`
action. This is not a separate Skill Contract.

Read and follow:
- `../../../.agents/skills/workflow-supervisor/SKILL.md`
- `../../../.agents/references/workflow-supervisor-runtime.md`
- `../../../AGENTS.md`
- `../../../CLAUDE.md`

Default command:

```bash
python tooling/workflow_supervisor/scripts/workflow_ctl.py build --auto --json
```

Keep the build scoped to the current Grill intent, prepare outputs, baseline
state, and declared worker-result contract.
