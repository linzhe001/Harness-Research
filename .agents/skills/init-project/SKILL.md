---
name: init-project
description: WF0/bootstrap wrapper for staged `CLAUDE.md` generation and updates. Use when the user wants the compact project snapshot initialized or refreshed while preserving the original staged template behavior.
---

# Init Project

## References

Read these first:
- `./references/claude-md-template.md`
- `./references/claude-maintenance.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/ubiquitous-language.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../PROJECT_STATE.json` if it exists
- `../../../CLAUDE.md` if it exists
- `../../../AGENTS.md` if it exists
- `../../../README.md` if it exists
- `../../../OPERATOR_CONTEXT.md` if it exists
- `../../../docs/Research_Intent_Draft.md` when running `update-from-grill`
- `../../../docs/Grill_Round_Log.md` when running `update-from-grill`
- `../../../docs/Execution_Readiness_Packet.md` when running `update-from-grill`
- `../../../.workflow_supervisor/readiness.json` when running
  `update-from-grill` and supervisor tooling produced it

## When To Use

Interpret natural-language requests as one of:
- `init`
- `update`
- `update-from-grill`
- `deps-changed`

Treat WF0, bootstrap, and explicit operator-context setup requests as `init`
unless the user is clearly asking only to refresh an existing section.
Treat a Grill exit of `grill_draft_ready`, an accepted Grill draft, or an
explicit `$init-project update-from-grill` request as `update-from-grill`.

## Required Work

### `init`

This is the WF0 setup path. It prepares compact guidance and optional stable
operator context; it does not validate research evidence or approve contracts.

1. Gather project name and, if already known, an environment name.
2. If no runnable environment exists yet, create the minimal `CLAUDE.md` with an explicit placeholder that WF5 baseline-repro owns first environment creation.
3. Create the minimal `CLAUDE.md` using the canonical template.
4. If the project opts into dynamic context, create the numbered docs directories and `.evidence/` directories, but do not fabricate evidence.
5. If the operator explicitly provides stable preferences or local constraints, create or update `OPERATOR_CONTEXT.md`. Do not infer preferences from project facts.
6. Use `./references/claude-maintenance.md` when editing individual sections instead of rewriting the whole file.

### `update`

1. Read `PROJECT_STATE.json` and the stage artifacts.
2. Fill only the sections whose source artifacts are now known:
	   - idea
	   - idea debate decision and refined idea
	   - tech stack
   - environment and dataset paths
   - baseline reference
   - project structure
   - core artifacts
   - language policy
   - entry scripts
3. Preserve `## Custom`.
4. At WF4, dataset paths must be refreshed into `CLAUDE.md` immediately, and `AGENTS.md` must be checked for a stable pointer to `CLAUDE.md` when it exists.
5. At WF5, environment facts must stop being placeholders and be replaced with the first runnable environment.
6. Update the current stage line.
7. Use `./references/claude-maintenance.md` for section-safe updates.
8. Render data-backed section bodies according to `./references/claude-maintenance.md` before writing them into `CLAUDE.md`.
9. Report a Gate ledger when `CLAUDE.md`, `AGENTS.md`, `OPERATOR_CONTEXT.md`, dynamic-context directories, or `PROJECT_STATE.json` are written. If context init or workflow-state checks are not run, mark them `NOT_RUN` with the reason.

### `update-from-grill`

This is the Grill handoff path. It initializes or refreshes operator-facing
guidance immediately after the operator accepts a Grill draft, before canonical
WF1-WF3 Stage artifacts necessarily exist.

1. Read the Grill handoff artifacts from disk:
   - `docs/Research_Intent_Draft.md`
   - `docs/Grill_Round_Log.md`
   - `docs/Execution_Readiness_Packet.md`
   - `.workflow_supervisor/readiness.json` only when supervisor tooling has
     produced it
2. Read existing `CLAUDE.md`, `AGENTS.md`, `README.md`, `PROJECT_STATE.json`,
   and `OPERATOR_CONTEXT.md` when present.
3. If `CLAUDE.md` is missing, create it from the canonical template. If it
   exists, use `./references/claude-maintenance.md` and update only the
   relevant sections.
4. Write only candidate-clear Grill context:
   - project idea / current intent
   - current stage as Grill draft accepted, not WF1-WF3 complete
   - core startup artifacts and where to continue
   - candidate dataset acquisition needs and intended local paths
   - candidate baseline repositories or negative controls and intended clone
     locations
   - unresolved questions, falsifiers, claim boundaries, and prepare blockers
5. Keep candidate dataset paths and baseline clone targets out of the stable
   `CLAUDE.md` dataset/environment truth section unless they are explicitly
   labeled candidate. Verified paths still belong to WF4/WF5 or
   workflow-supervisor prepare/build evidence.
6. Ensure `AGENTS.md` exists or points to `CLAUDE.md` plus the Grill handoff
   artifacts for startup context. Do not duplicate volatile local paths in
   `AGENTS.md`.
7. Ensure `README.md` exists for a new target workspace, or refresh only its
   short project/startup pointers when the operator requested initialization.
   Keep it concise and link to `CLAUDE.md`, `AGENTS.md`, and the Grill draft
   artifacts instead of copying full Grill content.
8. Preserve every `## Custom` section in existing guidance files.
9. Do not write `.workflow_supervisor/**` or `.evidence/**` by hand, do not
   mark WF1-WF3 complete, and do not promote Grill draft facts into approved
   contracts.
10. Report a Gate ledger when `CLAUDE.md`, `AGENTS.md`, `README.md`,
    `OPERATOR_CONTEXT.md`, dynamic-context directories, or
    `PROJECT_STATE.json` are written. If Grill handoff artifacts, context init,
    workflow-state checks, or docs-site rendering are not run, mark the
    corresponding action `NOT_RUN` with the reason.

### `deps-changed`

- Refresh only the environment section, equivalent to `$env-setup refresh`.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_render_or_NOT_RUN`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Codex Adaptation

- Treat natural-language requests as the canonical `$init-project {init|update|deps-changed}` interface.
- Ask the user directly only for essential missing inputs.
- Preserve the staged fill-in behavior, line-budget discipline, and `## Custom` preservation rule.
- Preserve the rule that environment creation belongs to WF5 baseline-repro unless the environment already exists.
- Preserve the `## Language Policy` section and keep it aligned with `../../../.agents/references/language-policy.md`.
- Preserve the `## Global Rule: Ubiquitous Language` section when refreshing
  generated guidance.
- Keep `AGENTS.md` as Codex-native always-on guidance, but maintain `CLAUDE.md` for compatibility exactly as the canonical prompt expects.
- In `update-from-grill`, initialize or refresh `README.md` only as a concise
  project entry point. The stable operating truth remains in `CLAUDE.md` /
  `AGENTS.md`, and Grill artifacts remain draft inputs until later gates verify
  them.

## Execution Rule

Follow the local prompt, template, and language policy rather than replacing `CLAUDE.md` maintenance with a generic project summary.
