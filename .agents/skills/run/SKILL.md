---
name: run
description: "Visible Harness run entry. Use for WF10 experiment iteration: model exploration, hyperparameter changes, ablations, visualization, and quantitative runs."
---

# Run

Use `$run` as the human-facing alias for WF10 iteration work. This is not a
separate Skill Contract.

Read and follow:
- `../../../.agents/skills/iterate/SKILL.md`
- `../../../.agents/skills/auto-iterate-goal/SKILL.md` when starting auto-iterate
- `../../../AGENTS.md`
- `../../../CLAUDE.md`

Route the actual work through `$iterate plan`, `$iterate code`, `$iterate run`,
and `$iterate eval`, or the auto-iterate controller when enabled.
