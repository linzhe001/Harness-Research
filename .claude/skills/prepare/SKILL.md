---
name: prepare
description: "Visible Harness prepare entry. Use after Grill readiness is approved to acquire datasets, clone baselines, run baseline smoke checks, and complete prepare through workflow-supervisor."
argument-hint: "[--complete]"
allowed-tools: Read, Bash, Glob, Grep
---

# Prepare

Use `/prepare` as the human-facing alias for the Execution Supervisor
`prepare` action. This is not a separate Skill Contract.

Read and follow:
- `../../../.claude/skills/workflow-supervisor/SKILL.md`
- `../../../.claude/shared/workflow-supervisor-runtime.md`
- `../../../CLAUDE.md`
- `../../../AGENTS.md`

Default command:

```bash
python tooling/workflow_supervisor/scripts/workflow_ctl.py prepare --complete --json
```
