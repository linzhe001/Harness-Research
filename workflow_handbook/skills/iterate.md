---
schema_version: "0.1"
page_id: "iterate"
title: "iterate"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/iterate.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for iterate. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 220
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "iterate"
  - path: ".agents/skills/iterate/SKILL.md"
    role: "skill_source"
references: ["skill:iterate", "source:schemas/skill_contracts.json#iterate", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/iterate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# iterate

## Purpose

Internal Harness instruction source for iterate. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$iterate`
- `/iterate`
- `iterate`
- `NEXT_ROUND`
- `DEBUG`
- `CONTINUE`
- `PIVOT`
- `ABORT`
- `WF10`

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
- `runs/wf10/`
- `.evidence/light/index.json`
- `docs/45_discoveries/`
- `docs/40_iterations/Experiment_Queue.md`

## Final Outputs

- `current_doc: docs/context/experiments.md`
- `current_doc: docs/context/memory.md`
- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.json`
- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.md`

## Tool-Owned Outputs

- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.json`
- `conclusion_evidence: docs/30_evidence/Experiment_Evidence_Index.md`
- `tool_trace: .evidence/light/index.json`

## Must Read

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

## Must Prove

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

## Constraints

- `auto_observation_direct_to_MEMORY [advisory/notice; exception=not_required]`
- `manual_edit_auto_iterate [hard_invariant/block; exception=never]`
- `stage_transition_from_iterate [ownership_boundary/notice; exception=owner_delegation_required]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:iterate]]
- [[source:schemas/skill_contracts.json#iterate]]
- [[term:Gate Evidence]]
