---
name: build-plan
description: Codex wrapper for WF7 implementation planning. Use after WF6 architecture design when the user wants `docs/Implementation_Roadmap.md` and `project_map.json` built from the technical spec, baseline evidence, templates, and schemas.
---

# Build Plan

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/project-map-rule.md`
- `./references/implementation-roadmap.md`
- `./references/project-map-schema.json`
- `../../../PROJECT_STATE.json`
- `../../../docs/Technical_Spec.md` if it exists
- `../../../docs/Refined_Idea.md` if it exists
- `../../../docs/Dataset_Stats.md` if it exists
- `../../../docs/Baseline_Report.md` if it exists
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists

## When To Use

Use this skill for WF7 when the user wants the implementation roadmap and stable project blueprint.

This skill does not choose the architecture. WF6 `$refine-arch` owns architecture decisions; WF7 translates those decisions into implementation order, files, tests, and stable map entries.

## Required Work

1. Read the technical spec, refined idea, dataset stats, baseline report, and baseline/evaluation contracts or protocol.
2. Convert the approved architecture into a stable file tree that separates research code from baselines.
3. Write `project_map.json` using the canonical schema and stable/volatile policy.
4. Write `docs/Implementation_Roadmap.md` using the canonical template.
5. Include:
   - module pseudocode
   - shared interfaces and contracts between modules
   - expected function/class signatures for stable files
   - input/output shape and data-type constraints
   - config schema
   - file ownership and dependency order
   - training pipeline with smoke test
   - validation checkpoints
   - `git_snapshot.py` expectations
6. Update `PROJECT_STATE.json` with roadmap and project-map artifacts.
7. Run `python tooling/evidence/check_workflow_state.py --workspace-root .`
   when `PROJECT_STATE.json` or `project_map.json` changed, and report the gate
   ledger.

## Output Rules

- Use `./references/implementation-roadmap.md`.
- Use `./references/project-map-schema.json`.
- Apply `../../../.agents/references/project-map-rule.md` when deciding what belongs in `project_map.json`.
- Include evidence sources for all source docs, discovered stable files, entry scripts, and interface assumptions.
- Do not introduce new architecture choices here. WF7 may refine implementation details, module interfaces, configuration fields, validation checks, and coding constraints needed to execute the approved architecture efficiently. If the roadmap requires a different architecture, stop and route back to WF6 or a design review.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Codex Adaptation

- Treat natural-language requests as the canonical `$build-plan` flow.
- Preserve the separation between main research code and baselines.
- Preserve the staged training-pipeline design, including the smoke-test stage and `git_snapshot` expectations.

## Execution Rule

Use the local prompt, roadmap template, schema, project-map rule, and language policy as the source of truth for WF7.
Do not mark WF7 complete without reporting the project-map and workflow-state
gate results, or `NOT_RUN` if the checks could not execute.
