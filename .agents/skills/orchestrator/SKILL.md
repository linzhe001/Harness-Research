---
name: orchestrator
description: Codex wrapper for the canonical WF orchestrator. Use when the user wants project initialization, stage status, gate checks, rollback, or decision logging around `PROJECT_STATE.json`.
---

# Orchestrator

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/evidence-chain-rule.md`
- `../../../.agents/references/language-policy.md`
- `./references/project-state-schema.json`
- `./references/stage-gates.md`
- `../../../CLAUDE.md`
- `../../../PROJECT_STATE.json`
Tooling:
- `../../../tooling/evidence/init_context.py`
- `../../../tooling/evidence/compile_protocol.py`
- `../../../tooling/evidence/compile_doc.py`
- `../../../tooling/evidence/check_context_gates.py`
- `../../../tooling/evidence/check_protocol_drift.py`
- `../../../tooling/evidence/check_docchain_gates.py`
- `../../../tooling/evidence/check_dynamic_context.py`
- `../../../tooling/evidence/check_workflow_state.py`
- `../../../tooling/evidence/build_review_packet.py`
- `../../../tooling/evidence/approve_contract.py`

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
- `project_map.json` is read-only for ordinary stage control. It is generated
  by `$build-plan` and must be updated by any code-writing workflow step that
  adds/removes/renames stable files or changes stable interfaces.

## Core Workflow

### `init`

1. Gather project name, idea summary, target venue, deadline, codebase path, and dataset name.
2. Create the standard workflow directories if missing.
   - For dynamic-context projects, also create `docs/10_contract`, `docs/20_facts`, `docs/30_evidence`, `docs/35_protocol`, `docs/40_iterations/auto`, `docs/50_memory`, `.evidence/chains`, and `.evidence/schemas`.
   - Prefer running `python tooling/evidence/init_context.py --workspace-root . --set-state` for this layout.
3. If the operator explicitly provides stable preferences or local constraints, create or update `OPERATOR_CONTEXT.md`. Do not infer preferences from behavior or project facts.
4. Call `$init-project` in `init` mode to generate the minimal `CLAUDE.md`.
5. Initialize `PROJECT_STATE.json` using the canonical schema. Set `workflow_mode` explicitly:
   - `dynamic_context` for new projects using numbered context docs
   - `standard` for new projects that intentionally do not use numbered context docs
   - `compatibility` only for imported older projects that predate mandatory WF2/dynamic gates

### `status`

1. Read `PROJECT_STATE.json`.
2. Validate the current stage name against the canonical stage table and stage-gate reference.
3. If the project is in WF10, also read `iteration_log.json` for latest and best iteration status.
4. If in WF10 and `.auto_iterate/state.json` exists, include loop state (current round, goal, progress) in the report (read-only — orchestrator never writes to that file).
5. Report current stage, completed stages, blockers, latest artifacts, and the most appropriate next action.

### `next`

1. Confirm the current stage is completed.
2. Check required artifacts for the next transition.
   - If dynamic-context current docs or protocol drafts changed in the stage,
     run the mandatory evidence tooling listed in
     `evidence-chain-rule.md` before treating the stage as machine-checked.
3. Apply special gate logic from the canonical prompt:
   - New projects must pass WF2 `$idea-debate` and WF3 `$refine-idea` before data preparation, baseline reproduction, or architecture design. Skipping WF2 is a hard failure for new projects.
   - WF4 completion requires `PROJECT_STATE.json.dataset_paths` and `CLAUDE.md` dataset paths to be synchronized, plus an `AGENTS.md` stable-pointer consistency check when `AGENTS.md` exists.
   - WF5 must have `docs/Baseline_Report.md` and populated baseline metrics.
   - WF5 is the first hard contract approval point for dynamic-context projects; baseline/evaluation contracts must be approved or explicitly accepted as draft before unattended WF10.
   - WF6 `$refine-arch` must happen after WF5 and must read the refined idea, dataset facts, baseline report, and evaluation protocol or contracts.
   - WF7 `$build-plan` requires `docs/Technical_Spec.md`; if planning exposes a new architecture decision, route back to WF6 or `$deep-check`.
   - WF8 to WF9 requires `$validate-run`.
   - WF9 PASS hook: after `$validate-run` passes, orchestrator should auto-trigger a `$auto-iterate-goal` check so that an iteration goal is set before WF10 begins.
   - In dynamic-context projects, WF10 auto-iteration requires an approved Evaluation Contract or explicit operator acceptance of a draft.
   - Prefer `python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet` as the all-in-one dynamic gate when shell access is available.
   - Prefer `python tooling/evidence/check_context_gates.py --workspace-root . --stage wf10-auto` for this check when shell access is available.
   - Also run `python tooling/evidence/check_protocol_drift.py --workspace-root . --stage wf10` or `$protocol-drift-check` before unattended WF10; unresolved drift requires review or explicit operator acceptance.
   - Also run `python tooling/evidence/check_workflow_state.py --workspace-root .` before stage transitions when state files changed.
   - WF10 to WF11 requires the latest completed iteration decision to be `CONTINUE`.
   - WF10 decision handling:
     - `NEXT_ROUND` → stay in WF10 (do not advance stage); ordinary improvement round
     - `DEBUG` → stay in WF10 (do not advance stage); fix technical issues
     - `CONTINUE` → can advance to WF11
     - `PIVOT` → rollback to WF2 idea debate/refine-idea
     - `ABORT` → terminate project
4. Never auto-advance without explicit user confirmation in the current conversation.

### `rollback`

- Move `current_stage` back without deleting artifacts, and append a rollback event to history.

### `decision`

- Append a timestamped project-level decision with rationale and alternatives.

## Codex Adaptation

- Ask the user directly, in plain text, when the canonical Claude prompt would have used `AskUserQuestion`.
- Call Codex wrapper skills such as `$init-project`, `$validate-run`, and `$iterate` instead of Claude slash commands.
- Keep the stage table, gate rules, and state semantics from the canonical prompt unchanged.
- Use `../../../.agents/references/language-policy.md` for reply language; keep workflow IDs, schema keys, and explicitly English-only fields unchanged.

## Execution Rule

Use the local references above as the workflow contract. Do not depend on `.claude` at runtime.
