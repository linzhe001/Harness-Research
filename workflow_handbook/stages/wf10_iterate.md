---
schema_version: "0.1"
page_id: "wf10_iterate"
title: "WF10 Iterate"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf10_iterate.md"
source_of_truth: true
status: "generated"
summary: "Run the Ralph-style loop: plan, code, run, evaluate, and decide the next round."
nav:
  section: "stages"
  position: 100
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "iterate"
  - path: ".agents/skills/iterate/SKILL.md"
    role: "skill_source"
references: ["stage:WF10", "skill:iterate", "source:schemas/skill_contracts.json#iterate", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf10_iterate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF10 Iterate

## Purpose

Run the Ralph-style loop: plan, code, run, evaluate, and decide the next round.

## How To Run

`$run` for experiment execution and `$analyze` for result decisions.

## Completion Effect

`iteration_log.json`, `docs/context/experiments.md`, and `docs/context/memory.md` capture runs, lessons, and decisions.

## Contract Detail

Internal Harness instruction source for iterate. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Trigger Visibility

Inputs below are internal contract triggers or readiness signals. For normal operation, start from the stage's visible alias in `How To Run`; the only human-facing `$` entries are `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Inputs

- `$iterate`
- `/iterate`
- `iterate`
- `NEXT_ROUND`
- `DEBUG`
- `CONTINUE`
- `PIVOT`
- `ABORT`
- `WF10`

## Outputs

- `current_doc: docs/context/experiments.md`
- `current_doc: docs/context/memory.md`
- `canonical_state: iteration_log.json`
- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.json`
- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.md`
- `legacy_compat: docs/40_iterations/ -> docs/context/`
- `legacy_compat: docs/45_discoveries/ -> docs/context/`
- `legacy_compat: docs/50_memory/ -> docs/context/`
- `legacy_compat: docs/iterations/ -> docs/context/`
- `legacy_compat: MEMORY.md -> docs/context/`
- `tool_trace: .evidence/light/index.json`
- `implementation: runs/wf10/`

## Required Reads

- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/run-artifact-contract.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/references/commit-checkpoint-rule.md`
- `.agents/references/research-supervision-patterns.md`
- `.agents/references/research-supervision/experiment-and-build-canvas.md`
- `.agents/references/research-supervision/ai-assisted-research-workflow.md`
- `.agents/skills/iterate/SKILL.md`
- `.agents/skills/iterate/references/iteration-log-schema.json`
- `.agents/skills/iterate/references/iteration-context.md`
- `.agents/skills/iterate/references/iteration-constraints.md`
- `schemas/iteration_log.schema.json`
- `schemas/run_code_manifest.schema.json`
- `schemas/run_promotion_plan.schema.json`
- `schemas/light_evidence_index.schema.json`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/context/contracts.md`
- `docs/context/experiments.md`
- `docs/context/memory.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/50_memory/Lessons.md`
- `MEMORY.md`
- `auto_paper_output/`
- `docs/30_evidence/Experiment_Evidence_Index.json`
- `docs/30_evidence/Experiment_Evidence_Index.md`
- `.evidence/light/index.json`
- `runs/wf10/`
- `docs/45_discoveries/Discovery_Ledger.md`
- `docs/45_discoveries/Research_Wiki.md`
- `docs/40_iterations/Experiment_Queue.md`

## Gates

- `wf10_state_preflight`
- `iteration_log_update`
- `single_next_command`
- `run_local_promotion_check`
- `decision_vocabulary`
- `build_experiment_evidence_index_or_NOT_RUN`
- `memory_context_update_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `iteration_log_v2_strict`
- `action_state_next_action_update`
- `run_code_manifest_or_config_only_record`
- `promotion_plan_or_NOT_READY`
- `build_light_evidence_index_or_NOT_RUN`
- `experiments_context_update_or_NOT_RUN`
- `pre_train_commit_or_debug_scope`
- `pre_eval_commit_or_NOT_CHANGED`
- `claim_delta_evidence_or_NOT_CHANGED`
- `assurance_axis_recorded`
- `iteration_log_write`
- `iteration_report_write`
- `memory_context_write`
- `WF11_handoff`
- `experiment_evidence_index_write`
- `docs_site_boundary_report`
- `run_code_manifest_write`
- `promotion_plan_write`
- `light_evidence_index_write`
- `experiments_context_write`
- `claim_delta_evidence`
- `pre_train_commit`
- `pre_eval_commit`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:iterate]]

## Related References

- [[stage:WF10]]
- [[skill:iterate]]
- [[source:schemas/skill_contracts.json#iterate]]
- [[term:Gate Evidence]]
