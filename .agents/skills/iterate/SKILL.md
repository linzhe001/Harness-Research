---
name: iterate
description: "Internal Harness instruction source for iterate. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Iterate

Use this Skill only for WF10 experiment-loop state. It owns
`iteration_log.json`; it never writes stage transitions into
`PROJECT_STATE.json` and never writes `.auto_iterate/**`.

## Read First

- Workflow, context, contract, lesson, code-style, review, language, and docs
  rules under `../../../.agents/references/`
- `../../../.agents/references/run-artifact-contract.md`
- `./references/iteration-log-schema.json`
- `./references/iteration-context.md`
- `./references/iteration-constraints.md`
- `iteration_log.json`, `PROJECT_STATE.json`, `CLAUDE.md`
- Evaluation/Baseline contracts, glossary, and lessons when present

## State Rules

- `iteration_log.json` is the experiment source of truth.
- `$orchestrator` owns `PROJECT_STATE.json` transitions.
- Code-writing substeps must sync `project_map.json` when stable files or
  interfaces change.
- Auto-iterate may invoke phases through a runtime adapter, but it only reads
  `iteration_log.json` postconditions.
- Active context belongs in `.agents/state/iterations/<iter-id>/context.json`
  plus `.agents/state/current_iteration.json` only when needed.

## Context Budget

- Load active iteration plus 5 most recent summaries; reference full
  `iteration_log.json` and Gate ledger by path.
- Include at most 5 Gate ledger summaries in prompts or status context.

## Commands

- `plan`: ensure no blocking unfinished iteration, allocate ID, check accepted
  lessons and candidate lessons, record hypothesis, changes summary,
  `config_diff`, screening recommendation, and canonical `codex_review`
  behavior.
- `code`: select latest planned iteration, write context, apply code-style
  checklist, preserve slice/glossary boundaries, route implementation through
  `$code-debug`, and require a semantic commit before status `training`.
- `run`: select latest `training` iteration, resolve Train/Eval scripts from
  `CLAUDE.md`, use WF5 protocol metric keys, record `run_manifest` with run
  artifact bundle paths, tracked metrics, screening result when relevant, and
  canonical failure/manual-mode behavior.
- `eval`: refresh context, invoke `$evaluate` when needed, compare baseline,
  previous, and best metrics, record decision, lessons, lesson candidates,
  slice/drift observations, complexity/boundary observations, reports, and
  completion state.
- `ablate`, `status`, `log`: preserve canonical schema and history behavior.

## Lesson And Gate Rules

- Append `MEMORY.md` only for accepted lessons satisfying
  `lesson-quality-rule.md`; raw observations stay in iteration reports or
  `docs/50_memory/Lessons.md`.
- When `iteration_log.json`, lesson files, or accepted memory changed, report a
  Gate ledger.
- Run `check_workflow_state.py` near WF10 handoff points; for routine in-loop
  updates, report whether it was run or deferred.

## Docs

After stable Markdown outputs are finalized, invoke `$docs-site` or report
`docs_site_boundary_report`.

## Durable Docs Render

After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
