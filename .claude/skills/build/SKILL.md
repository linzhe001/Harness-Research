---
name: build
description: "Visible Harness build entry. Use after prepare to plan and implement the first codebase slice through workflow-supervisor build automation."
argument-hint: "[--auto]"
allowed-tools: Read, Bash, Glob, Grep
---

# Build

Use `/build` as the human-facing alias for the Execution Supervisor `build`
action. This is not a separate Skill Contract.

Read and follow:
- `../../../.claude/skills/workflow-supervisor/SKILL.md`
- `../../../.claude/shared/workflow-supervisor-runtime.md`
- `../../../CLAUDE.md`
- `../../../AGENTS.md`

Default command:

```bash
python tooling/workflow_supervisor/scripts/workflow_ctl.py build --auto --json
```
