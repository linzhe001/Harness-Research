---
name: build-plan
description: Codex wrapper for WF6 architecture planning. Use when the user wants `docs/Implementation_Roadmap.md` and `project_map.json` built from the canonical workflow, templates, and schemas.
---

# Build Plan

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/project-map-rule.md`
- `./references/implementation-roadmap.md`
- `./references/project-map-schema.json`
- `../../../PROJECT_STATE.json`

## When To Use

Use this skill for WF6 when the user wants the implementation roadmap and stable project blueprint.

## Required Work

1. Read the technical spec, dataset stats, and baseline report.
2. Design the stable file tree that separates research code from baselines.
3. Write `project_map.json` using the canonical schema and stable/volatile policy.
4. Write `docs/Implementation_Roadmap.md` using the canonical template.
5. Include:
   - module pseudocode
   - config schema
   - training pipeline with smoke test
   - validation checkpoints
   - `git_snapshot.py` expectations
6. Update `PROJECT_STATE.json` with roadmap and project-map artifacts.

## Output Rules

- Use `./references/implementation-roadmap.md`.
- Use `./references/project-map-schema.json`.
- Apply `../../../.agents/references/project-map-rule.md` when deciding what belongs in `project_map.json`.

## Codex Adaptation

- Treat natural-language requests as the canonical `$build-plan` flow.
- Preserve the separation between main research code and baselines.
- Preserve the staged training-pipeline design, including the smoke-test stage and `git_snapshot` expectations.

## Execution Rule

Use the local prompt, roadmap template, schema, and project-map rule as the source of truth for WF6.
