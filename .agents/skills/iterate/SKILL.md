---
name: iterate
description: Codex wrapper for WF10 structured iteration. Use when the user wants to run `plan`, `code`, `run`, `eval`, `ablate`, `status`, or `log` while preserving the original iteration schema and workflow logic.
---

# Iterate

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/lesson-quality-rule.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/ubiquitous-language.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `./references/iteration-log-schema.json`
- `./references/iteration-context.md`
- `./references/iteration-constraints.md`
- `../../../iteration_log.json`
- `../../../PROJECT_STATE.json`
- `../../../CLAUDE.md`
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists
- `../../../docs/20_facts/Project_Glossary.md` if it exists
- `../../../docs/50_memory/Lessons.md` if it exists

## When To Use

Use this skill for WF10 structured experimentation.

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
- Stable file or stable interface changes during `code` still require
  `project_map.json` sync by the code-writing step, normally through
  `$code-debug`.

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
4. Read `docs/50_memory/Lessons.md` and `MEMORY.md` when present; accepted lessons are stronger than candidate lessons.
5. Record hypothesis, changes summary, config diff, and screening recommendation (`screening.recommended` as a structured boolean field).
6. Preserve the canonical `codex_review` field behavior in `iteration_log.json`.
7. If reviewer cross-validation is used, follow reviewer independence and tracing protocols.

### `code`

1. Select the latest planned iteration.
2. Write canonical iteration context to `.agents/state/iterations/<iter-id>/context.json`.
3. Mirror active context to `.agents/state/current_iteration.json`.
4. Follow `./references/iteration-context.md` when creating both the persistent and active context files.
5. Apply the pre-edit checklist from `../../../.agents/references/code-style.md`.
6. Preserve the current slice boundary and glossary terms. Route any needed
   stable implementation edits through `$code-debug`.
7. Invoke `$code-debug`.
8. Require a semantic commit before moving from `coding` to `training`.

### `run`

1. Select the latest `training` iteration.
2. Build the training command from `CLAUDE.md` entry scripts and the config.
3. Resolve the tracked metrics from the baseline or evaluation protocol established in WF5 instead of hard-coding PSNR/SSIM-style keys.
4. Record run metadata in `run_manifest`.
5. When this is a screening/proxy run that returns `passed` or `failed`, record
   `screening.metrics` from the tracked metric set and keep the screening
   command/exp_dir in `run_manifest`.
6. Preserve the canonical error handling and manual-mode fallback behavior.

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
   - lesson_candidates when a finding may be promoted later
   - lesson_promotion_status
   - slice completion or drift
   - complexity and boundary observations
   - completion state
7. Produce or refresh the per-iteration report and, when useful, `docs/50_memory/Lessons.md`.
8. Append to `MEMORY.md` only for accepted lessons that satisfy `lesson-quality-rule.md`.
9. When `iteration_log.json`, lesson files, or accepted memory changed, report a
   gate ledger. Run `check_workflow_state.py` near WF10 handoff points; for
   routine in-loop updates, explicitly state whether the workflow-state gate was
   run or deferred.

### `ablate`, `status`, `log`

- Preserve the canonical behavior and schema for ablations, summaries, and full history views.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_render_or_NOT_RUN`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Codex Adaptation

- Treat natural-language requests as the canonical `$iterate {plan|code|run|eval|ablate|status|log}` interface.
- When the canonical workflow calls for code or analysis substeps, use `$code-debug` and `$evaluate`.
- Use `.agents/state/` as the local active-context directory; create context files inside it only when needed.
- Use `../../../.agents/references/language-policy.md` for reply language and for localizing natural-language iteration summaries; keep schema keys, commands, and decision/status tokens unchanged.

## Execution Rule

Follow the local iteration logic and schema rather than replacing it with a generic experiment log loop.
`./references/iteration-constraints.md` is mandatory behavior, not optional guidance.
Instructional decisions are not gate results. Report the actual evaluation,
state, and readiness checks that were run.
