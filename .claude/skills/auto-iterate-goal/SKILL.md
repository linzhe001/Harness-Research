---
name: auto-iterate-goal
description: Generate or validate the auto-iterate goal file before launching WF8 auto-iterate
argument-hint: "[init|refresh|check]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

## Purpose

Bridge skill between WF7.5 PASS and WF8 auto-iterate `start`. Produces or validates `docs/auto_iterate_goal.md` — the operator-facing research objective that the controller's goal parser consumes.

## When To Use

- After `/validate-run` returns PASS (WF7.5 gate cleared)
- Before running `scripts/auto_iterate_ctl.sh start --goal docs/auto_iterate_goal.md`
- When the orchestrator auto-triggers a goal readiness check

## References

- `./templates/goal-template.md`
- `.claude/Workflow_Guide.md`
- `.claude/skills/evaluate/templates/stage-report.md`
- `docs/auto_iterate_goal_template.md`

## Subcommands

### `init`
Generate `docs/auto_iterate_goal.md` when it does not exist.

**Sources:**
- WF5 baseline metrics and evaluation protocol
- WF7.5 validate-run output
- Project context from `CLAUDE.md` / `PROJECT_STATE.json`

**Output:** `docs/auto_iterate_goal.md` with all required structured fields.

### `refresh`
Update an existing goal when fields are missing, defaults changed, or new context is available.

**Behavior:**
- Read existing `docs/auto_iterate_goal.md`
- Identify missing or outdated fields
- Generate updated version or draft
- **Do NOT silently overwrite** human-edited objective constraints (name, direction, target)
- Present diff or highlight changes for operator review

### `check`
Validate the existing goal file without modifying it.

**Checks:**
- All required fields present (see goal-template.md)
- `primary_metric.direction` is `maximize` or `minimize`
- `budget.max_rounds` is a positive integer
- `screening_policy.enabled` is boolean
- No placeholder `{{...}}` markers remain

**Output:** PASS or list of validation errors.

## What This Skill Does NOT Do

- Does not write `.auto_iterate/goal.md` (that is the controller's job via `start --goal`)
- Does not write `.auto_iterate/state.json`
- Does not start, stop, pause, or resume the auto-iterate loop
- Does not decide `NEXT_ROUND` / `CONTINUE` / etc. (that is `/evaluate`'s job)
- Claude runtime parity for auto-iterate is not in V1 scope

## Orchestrator Integration

The orchestrator should auto-trigger after WF7.5 PASS:
```
WF7.5 validate-run PASS
  → /auto-iterate-goal check
    → goal exists + valid: no-op
    → goal missing: /auto-iterate-goal init
    → goal invalid/incomplete: /auto-iterate-goal refresh
```
