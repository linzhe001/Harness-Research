---
name: init-project
description: "Internal Harness instruction source for init-project. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Init Project

Use this Skill for `init`, `update`, `update-from-grill`, or `deps-changed`.
It maintains compact guidance, preserves `## Custom`, and does not approve
research contracts.

## Read First

- `./references/claude-md-template.md`
- `./references/claude-maintenance.md`
- context, language, documentation, and ubiquitous-language rules under
  `../../../.agents/references/`
- Existing `PROJECT_STATE.json`, `CLAUDE.md`, `AGENTS.md`, `README.md`, and
  `OPERATOR_CONTEXT.md` when present
- For `update-from-grill`: `docs/05_intake/Research_Intent_Draft.md`,
  `docs/05_intake/Grill_Round_Log.md`, `docs/05_intake/Execution_Readiness_Packet.md`, and
  `.workflow_supervisor/readiness.json` only if supervisor tooling produced it

## Modes

### `init`

Collect project name and known environment name. Create the minimal
`CLAUDE.md` from the template. If no runnable environment exists, leave an
explicit WF5-owned environment placeholder. Create dynamic-context directories
only when the project opts in; do not fabricate evidence. Write
`OPERATOR_CONTEXT.md` only for explicit stable operator preferences.

### `update`

Read `PROJECT_STATE.json` and source artifacts. Fill only sections whose source
is now known: idea, debate/refinement, tech stack, environment, dataset paths,
baseline references, project structure, core artifacts, language policy, entry
scripts, and current stage. At WF4, sync dataset paths into `CLAUDE.md` and
ensure `AGENTS.md` points to `CLAUDE.md` instead of duplicating volatile paths.
At WF5, replace environment placeholders with first runnable environment facts.

### `update-from-grill`

Use immediately after `grill_draft_ready` or an accepted Grill draft.

1. Read the three Grill docs and `.workflow_supervisor/readiness.json` when it
   exists.
2. Read existing guidance/state files. Missing `PROJECT_STATE.json` is not a
   failure.
3. Create `CLAUDE.md` from template if missing; otherwise use
   `./references/claude-maintenance.md` for section-safe edits.
4. Write only candidate-clear Grill context: current intent, accepted draft
   status, startup artifacts, candidate datasets/baselines and targets,
   unresolved questions, falsifiers, claim boundaries, and prepare blockers.
5. Keep candidate dataset paths and baseline clone targets explicitly labeled
   candidate until `prepare` / WF4-WF5 verify them.
6. Ensure `AGENTS.md` and `README.md` exist or point to `CLAUDE.md` plus Grill
   artifacts; keep them concise and avoid volatile path duplication.
7. Do not write `.workflow_supervisor/**` or `.evidence/**` by hand, do not
   mark WF1-WF3 complete, and do not promote Grill draft facts into approved
   contracts. Do not create `PROJECT_STATE.json`, `project_map.json`, or
   `iteration_log.json` from `update-from-grill`.
8. In `update-from-grill`, absence of `PROJECT_STATE.json`, `project_map.json`,
   `iteration_log.json`, or `.workflow_supervisor/readiness.json` is expected
   unless another tool already produced them.

### `deps-changed`

Refresh only `## Environment`, equivalent to `$env-setup refresh`.

## Write Rules

- Preserve `## Custom`, `## Language Policy`, and Ubiquitous Language guidance.
- Use precise section replacement, not whole-file rewrites.
- Keep `CLAUDE.md` line-budget discipline.
- Report Gate ledger for `CLAUDE.md`, `AGENTS.md`, `README.md`,
  `OPERATOR_CONTEXT.md`, dynamic-context directory, or state writes.
- Mark context init, workflow-state checks, Grill handoff reads, or docs-site
  rendering as `NOT_RUN` when skipped.

After stable Markdown outputs are finalized, invoke `$docs-site` or report
`docs_site_boundary_report`.

## Durable Docs Render

After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
