---
name: iterate
description: Codex wrapper for WF8 structured iteration. Use when the user wants to run `plan`, `code`, `run`, `eval`, `ablate`, `status`, or `log` while preserving the original iteration schema and workflow logic.
---

# Iterate

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/language-policy.md`
- `./references/iteration-log-schema.json`
- `./references/iteration-context.md`
- `./references/iteration-constraints.md`
- `../../../iteration_log.json`
- `../../../PROJECT_STATE.json`
- `../../../CLAUDE.md`

## When To Use

Use this skill for WF8 structured experimentation.

Interpret natural-language requests as one of these canonical intents:
- `plan`
- `code`
- `run`
- `eval`
- `ablate`
- `status`
- `log`

## State Ownership

- `iteration_log.json` is the only experiment source of truth.
- Do not write stage transitions into `PROJECT_STATE.json`; `$orchestrator` owns those.
- Stable interface changes still require `project_map.json` sync through `$code-debug`.

## Controller Coexistence

- When the auto-iterate controller is active, `$iterate` phases are invoked via runtime adapter prompt, not directly by the user.
- `iteration_log.json` ownership is unchanged — `$iterate` still owns it exclusively.
- The controller only reads `iteration_log.json` via postcondition validation; it does not write to it.
- The controller does not write to `.agents/state/**`.
- `.auto_iterate/` is controller-owned; `$iterate` must not write to it.

## Canonical Workflow

### Startup Cleanup

- Before any sub-command, inspect active iteration context files.
- Prefer `.agents/state/current_iteration.json`.
- If interrupted state is found, apply the canonical cleanup behavior from the Claude prompt.
- Follow `./references/iteration-context.md` for deterministic cleanup.

### `plan`

1. Ensure there is no blocking unfinished iteration.
2. Allocate the next iteration ID.
3. Check prior lessons to avoid repeating known failed ideas blindly.
4. Record hypothesis, changes summary, config diff, and screening recommendation (`screening.recommended` as a structured boolean field).
5. Preserve the canonical `codex_review` field behavior in `iteration_log.json`.

### `code`

1. Select the latest planned iteration.
2. Write canonical iteration context to `.agents/state/iterations/<iter-id>/context.json`.
3. Mirror active context to `.agents/state/current_iteration.json`.
4. Follow `./references/iteration-context.md` when creating both the persistent and active context files.
5. Invoke `$code-debug`.
6. Require a semantic commit before moving from `coding` to `training`.

### `run`

1. Select the latest `training` iteration.
2. Build the training command from `CLAUDE.md` entry scripts and the config.
3. Resolve the tracked metrics from the baseline or evaluation protocol established in WF5 instead of hard-coding PSNR/SSIM-style keys.
4. Record run metadata in `run_manifest`.
5. Preserve the canonical error handling and manual-mode fallback behavior.

### `eval`

1. Select the latest runnable iteration.
2. Write or refresh active iteration context.
3. Follow `./references/iteration-context.md` when reusing an existing context file.
4. Invoke `$evaluate` when full analysis is needed.
5. Compare against baseline, previous iteration, and best iteration using the tracked metric set inherited from WF5.
6. Record:
   - metrics
   - decision
   - lessons
   - completion state

### `ablate`, `status`, `log`

- Preserve the canonical behavior and schema for ablations, summaries, and full history views.

## Codex Adaptation

- Treat natural-language requests as the canonical `$iterate {plan|code|run|eval|ablate|status|log}` interface.
- When the canonical workflow calls for code or analysis substeps, use `$code-debug` and `$evaluate`.
- Use `.agents/state/` as the local active-context directory; create context files inside it only when needed.
- Use `../../../.agents/references/language-policy.md` for reply language and for localizing natural-language iteration summaries; keep schema keys, commands, and decision/status tokens unchanged.

## Execution Rule

Follow the local iteration logic and schema rather than replacing it with a generic experiment log loop.
`./references/iteration-constraints.md` is mandatory behavior, not optional guidance.
