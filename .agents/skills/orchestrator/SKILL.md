---
name: orchestrator
description: Codex wrapper for the canonical WF orchestrator. Use when the user wants project initialization, stage status, gate checks, rollback, or decision logging around `PROJECT_STATE.json`.
---

# Orchestrator

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `./references/project-state-schema.json`
- `./references/stage-gates.md`
- `../../../CLAUDE.md`
- `../../../PROJECT_STATE.json`

## When To Use

Use this skill when the user wants project-level workflow control rather than direct implementation work.

Interpret natural-language requests as one of these canonical intents:
- `init`
- `status`
- `next`
- `rollback`
- `decision`

## State Ownership

- `PROJECT_STATE.json` is the only stage-flow source of truth.
- `iteration_log.json` is read-only from this skill; `$iterate` owns experiment writes.
- `project_map.json` is read-only here; `$build-plan` and `$code-debug` own structure updates.

## Core Workflow

### `init`

1. Gather project name, idea summary, target venue, deadline, codebase path, and dataset name.
2. Create the standard workflow directories if missing.
3. Call `$init-project` in `init` mode to generate the minimal `CLAUDE.md`.
4. Initialize `PROJECT_STATE.json` using the canonical schema.

### `status`

1. Read `PROJECT_STATE.json`.
2. Validate the current stage name against the canonical stage table and stage-gate reference.
3. If the project is in WF8, also read `iteration_log.json` for latest and best iteration status.
4. Report current stage, completed stages, blockers, latest artifacts, and the most appropriate next action.

### `next`

1. Confirm the current stage is completed.
2. Check required artifacts for the next transition.
3. Apply special gate logic from the canonical prompt:
   - WF5 must have `docs/Baseline_Report.md` and populated baseline metrics.
   - WF7 to WF8 requires `$validate-run`.
   - WF8 to WF9 requires the latest completed iteration decision to be `CONTINUE`.
4. Never auto-advance without explicit user confirmation in the current conversation.

### `rollback`

- Move `current_stage` back without deleting artifacts, and append a rollback event to history.

### `decision`

- Append a timestamped project-level decision with rationale and alternatives.

## Codex Adaptation

- Ask the user directly, in plain text, when the canonical Claude prompt would have used `AskUserQuestion`.
- Call Codex wrapper skills such as `$init-project`, `$validate-run`, and `$iterate` instead of Claude slash commands.
- Keep the stage table, gate rules, and state semantics from the canonical prompt unchanged.

## Execution Rule

Use the local references above as the workflow contract. Do not depend on `.claude` at runtime.
