---
name: auto-iterate-goal
description: Generate or validate the auto-iterate goal file before launching WF10 auto-iterate
---

## Purpose

Bridge skill between WF9 PASS and WF10 auto-iterate `start`. Produces or validates `docs/auto_iterate_goal.md` — the operator-facing research objective that the controller's goal parser consumes.

## When To Use

- After `$validate-run` returns PASS (WF9 gate cleared)
- Before running `tooling/auto_iterate/scripts/auto_iterate_ctl.sh start --goal docs/auto_iterate_goal.md`
- When the orchestrator auto-triggers a goal readiness check

## References (read before executing)

- `./references/goal-template.md`
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `../evaluate/references/stage-report.md`
- `tooling/auto_iterate/docs/auto_iterate_goal_template.md`
- `docs/10_contract/Evaluation_Contract.md` if it exists
Tooling:
- `tooling/evidence/check_context_gates.py`

## Subcommands

### `init`
Generate `docs/auto_iterate_goal.md` when it does not exist.

**Sources:**
- WF5 baseline metrics and evaluation protocol
- WF9 validate-run output
- Project context from `CLAUDE.md` / `PROJECT_STATE.json`
- Dynamic projects: `docs/10_contract/Evaluation_Contract.md`

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
- Dynamic projects: Evaluation Contract is approved, or the current operator explicitly accepts running with a draft contract
  - Prefer `python tooling/evidence/check_context_gates.py --workspace-root . --stage wf10-auto` when shell access is available

**Output:** PASS or list of validation errors.

## What This Skill Does NOT Do

- Does not write `.auto_iterate/goal.md` (that is the controller's job via `start --goal`)
- Does not write `.auto_iterate/state.json`
- Does not start, stop, pause, or resume the auto-iterate loop
- Does not decide `NEXT_ROUND` / `CONTINUE` / etc. (that is `$evaluate`'s job)
- Does not promote raw auto-run observations into `MEMORY.md`; lesson promotion must follow `lesson-quality-rule.md` through `$iterate eval` or human review.

## Orchestrator Integration

The orchestrator should auto-trigger after WF9 PASS:
```
WF9 validate-run PASS
  → $auto-iterate-goal check
    → goal exists + valid: no-op
    → goal missing: $auto-iterate-goal init
    → goal invalid/incomplete: $auto-iterate-goal refresh
```
