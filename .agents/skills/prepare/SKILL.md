---
name: prepare
description: "Visible Harness prepare entry. Use after Grill readiness is approved to acquire datasets, clone baselines, run baseline smoke checks, and complete prepare through workflow-supervisor."
---

# Prepare

Use `$prepare` as the human-facing alias for the Execution Supervisor
`prepare` action. This is not a separate Skill Contract.

Read and follow:
- `../../../.agents/skills/workflow-supervisor/SKILL.md`
- `../../../.agents/references/workflow-supervisor-runtime.md`
- `../../../AGENTS.md`
- `../../../CLAUDE.md`

Default command:

```bash
python tooling/workflow_supervisor/scripts/workflow_ctl.py prepare --complete --json
```

Use Grill-produced approved readiness from `.workflow_supervisor/readiness.json`
when it exists. Pause only for missing inputs, policy blockers, worker
failures, or gate failures.
