---
name: run
description: "Visible Harness run entry. Use for WF10 experiment iteration: model exploration, hyperparameter changes, ablations, visualization, and quantitative runs."
argument-hint: "[iteration goal]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Run

Use `/run` as the human-facing alias for WF10 iteration work. This is not a
separate Skill Contract.

Read and follow:
- `../../../.claude/skills/iterate/SKILL.md`
- `../../../.claude/skills/auto-iterate-goal/SKILL.md` when starting auto-iterate
- `../../../CLAUDE.md`
- `../../../AGENTS.md`

Route through `/iterate plan`, `/iterate code`, `/iterate run`, and
`/iterate eval`, or the auto-iterate controller when enabled.
