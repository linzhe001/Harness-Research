---
schema_version: "0.1"
page_id: "evaluate"
title: "evaluate"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/evaluate.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for evaluate. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 130
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "evaluate"
  - path: ".agents/skills/evaluate/SKILL.md"
    role: "skill_source"
references: ["skill:evaluate", "source:schemas/skill_contracts.json#evaluate", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/evaluate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# evaluate

## Purpose

Internal Harness instruction source for evaluate. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$evaluate`
- `/evaluate`
- `evaluate`
- `eval results`
- `iteration eval`

## Can Write

- `iteration_log.json`
- `docs/context/experiments.md`
- `docs/context/memory.md`
- `docs/40_iterations/`
- `docs/iterations/`
- `docs/30_evidence/Experiment_Evidence_Index.json`
- `docs/30_evidence/Experiment_Evidence_Index.md`
- `docs/50_memory/`
- `MEMORY.md`
- `docs/Stage_Report.md`
- `runs/wf10/`
- `.evidence/light/index.json`
- `docs/45_discoveries/`
- `docs/40_iterations/Experiment_Queue.md`

## Final Outputs

- `current_doc: docs/context/experiments.md`
- `current_doc: docs/context/memory.md`
- `current_doc: docs/Stage_Report.md`
- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.json`
- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.md`

## Tool-Owned Outputs

- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.json`
- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.md`
- `tool_trace: .evidence/light/index.json`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/run-artifact-contract.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/references/language-policy.md`
- `.agents/references/commit-checkpoint-rule.md`
- `.agents/references/research-supervision-patterns.md`
- `.agents/references/research-supervision/experiment-and-build-canvas.md`
- `.agents/references/research-supervision/ai-assisted-research-workflow.md`
- `.agents/skills/evaluate/SKILL.md`
- `.agents/skills/evaluate/references/stage-report.md`
- `schemas/iteration_log.schema.json`
- `schemas/run_code_manifest.schema.json`
- `schemas/run_promotion_plan.schema.json`
- `schemas/light_evidence_index.schema.json`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/context/contracts.md`
- `docs/context/experiments.md`
- `docs/context/memory.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/50_memory/Lessons.md`
- `MEMORY.md`
- `docs/30_evidence/Experiment_Evidence_Index.json`
- `docs/30_evidence/Experiment_Evidence_Index.md`
- `.evidence/light/index.json`
- `runs/wf10/`
- `docs/45_discoveries/Discovery_Ledger.md`
- `docs/45_discoveries/Research_Wiki.md`
- `docs/40_iterations/Experiment_Queue.md`

## Must Prove

- `decision_vocabulary`
- `build_experiment_evidence_index_or_NOT_RUN`
- `memory_context_update_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `iteration_log_v2_strict`
- `action_state_next_action_update`
- `run_code_manifest_or_config_only_record`
- `promotion_plan_or_NOT_READY`
- `build_light_evidence_index_or_NOT_RUN`
- `run_local_promotion_check`
- `experiments_context_update_or_NOT_RUN`
- `pre_eval_commit_or_NOT_CHANGED`
- `claim_delta_evidence_or_NOT_CHANGED`
- `assurance_axis_recorded`
- `stage_report_write`
- `iteration_report_write`
- `memory_context_write`
- `iteration_log_write`
- `experiment_evidence_index_write`
- `docs_site_boundary_report`
- `run_code_manifest_write`
- `promotion_plan_write`
- `light_evidence_index_write`
- `experiments_context_write`
- `claim_delta_evidence`

## Constraints

- `stage_transition_from_iterate [ownership_boundary/notice; exception=owner_delegation_required]`
- `auto_observation_direct_to_MEMORY [advisory/notice; exception=not_required]`
- `protocol_as_approved_contract [hard_invariant/block; exception=never]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:evaluate]]
- [[source:schemas/skill_contracts.json#evaluate]]
- [[term:Gate Evidence]]
