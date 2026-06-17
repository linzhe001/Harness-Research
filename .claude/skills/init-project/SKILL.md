# Project CLAUDE.md Phased Generator

`CLAUDE.md` is loaded every session, so keep it compact. Initial output should
be under 40 lines; mature output must stay under 120 lines. Preserve every
existing `## Custom` section.

## Read First

- Existing `CLAUDE.md`, `AGENTS.md`, `README.md`, `OPERATOR_CONTEXT.md`, and
  `PROJECT_STATE.json` when present.
- Template: `templates/claude-md-template.md`.
- Shared rules: `language-policy.md`, `ubiquitous-language.md`,
  `documentation-evidence-rule.md`, and `documentation-style.md`.
- For `update-from-grill`: `docs/05_intake/Research_Intent_Draft.md`,
  `docs/05_intake/Grill_Round_Log.md`, `docs/05_intake/Execution_Readiness_Packet.md`, and
  `.workflow_supervisor/readiness.json` only if tooling produced it.

## Modes

### `init`

Ask for English project name and optional virtual environment name. Auto-detect
available environment facts with narrow commands such as Python version,
PyTorch/CUDA, GPU, dependency files, and relevant package versions. If no
runnable environment exists, keep placeholders.

Create a minimal `CLAUDE.md` with:
- project title and idea placeholder
- `## Environment` with activation command and detected facts/placeholders
- `## Language Policy`
- `## Global Rule: Code Style`
- `## Global Rule: Documentation Style`
- compact workflow line from WF0 through WF12 and WF10 decision loop

Do not fill idea, dataset, tech stack, project structure, core artifacts, or
entry scripts in init mode.

### `update`

Read `PROJECT_STATE.json` and existing artifacts, then use precise section
replacement. Do not rewrite the whole file.

Stage fills:
- WF1: one-sentence idea from `docs/Feasibility_Report.md`.
- WF2: selected direction from `docs/Idea_Debate.md`.
- WF3: target task, success criteria, baseline candidates, open questions from
  `docs/Refined_Idea.md`.
- WF4: dataset paths, split info, and key stats from `docs/Dataset_Stats.md`;
  keep `AGENTS.md` as a pointer, not a duplicate source of volatile paths.
- WF5: environment truth and baseline metric references from
  `docs/Baseline_Report.md`.
- WF6: tech stack and architecture summary from `docs/Technical_Spec.md`.
- WF7: top-level structure, core artifacts, and project-map maintenance rule
  from `project_map.json` and roadmap context.
- First successful WF10 experiment: lock `## Entry Scripts` from actual
  `scripts/` train/eval/test utilities.

### `deps-changed`

Only re-detect environment facts and refresh `## Environment`. This is
equivalent to `/env-setup refresh`.

### `update-from-grill`

Use immediately after explicit operator acceptance of a Grill draft or
`grill_draft_ready`.

1. Read Grill handoff artifacts from disk:
   `docs/05_intake/Research_Intent_Draft.md`, `docs/05_intake/Grill_Round_Log.md`, and
   `docs/05_intake/Execution_Readiness_Packet.md`.
2. Read `.workflow_supervisor/readiness.json` only if it exists.
3. Read current guidance/state files when present. Missing
   `PROJECT_STATE.json` is expected in a fresh target workspace.
4. Create `CLAUDE.md` from template if missing; otherwise edit only necessary
   sections and preserve unrelated content.
5. Fill only candidate-clear Grill context: current intent, accepted draft
   status, startup artifacts, candidate dataset acquisition needs and local
   targets, candidate baselines/negative controls and clone targets,
   unresolved questions, falsifiers, claim boundaries, and prepare blockers.
6. Label all dataset paths and baseline clone targets as candidate until
   `prepare` / WF4-WF5 verify them.
7. Ensure `AGENTS.md` exists or points to `CLAUDE.md` plus Grill artifacts.
   Do not duplicate volatile paths in `AGENTS.md`.
8. Ensure `README.md` exists for new target workspaces, or refresh only short
   startup pointers when requested.
9. Do not write `.workflow_supervisor/**` or `.evidence/**` by hand. Do not
   mark WF1-WF3 complete. Do not create `PROJECT_STATE.json`, `project_map.json`, or
   `iteration_log.json` from this mode.
10. Report Gate Evidence for changed guidance files and `NOT_RUN` for skipped
    workflow-state checks, docs-site render, or absent optional runtime files.
    Absence of `PROJECT_STATE.json`, `project_map.json`, `iteration_log.json`,
    or `.workflow_supervisor/readiness.json` is expected unless another tool
    already produced them.

## Common Update Rules

- Re-detect environment when relevant.
- Keep the `Current stage` line aligned with verified state.
- Preserve `## Language Policy`, `## Global Rule: Ubiquitous Language`, and
  every `## Custom` section.
- Do not overwrite already valid filled-in content.
- Use English for file names, paths, commands, code identifiers, schema keys,
  workflow IDs, metric keys, and placeholder tokens.

## Hard Constraints

- `CLAUDE.md` total line count never exceeds 120 lines.
- Initial `init` output never exceeds 40 lines.
- Always include virtual environment activation, even as a placeholder.
- Auto-detect environment facts; do not invent versions or paths.
- Never promote Grill draft facts into approved contracts.

## Durable Docs Render

After stable Markdown outputs are finalized, invoke `/docs-site` or report
`docs_site_boundary_report`. Do not render for temporary drafts.

## Durable Docs Render

After stable Markdown is finalized, invoke `/docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
