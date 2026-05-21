---
schema_version: "0.1"
page_id: "final-exp"
title: "final-exp"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/final-exp.md"
source_of_truth: true
status: "generated"
summary: "Codex wrapper for WF11 final experiment planning. Use when the user wants ablations, robustness tests, cross-dataset evaluation, and compute budgeting organized according to the original template."
nav:
  section: "skills"
  position: 240
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "final-exp"
  - path: ".agents/skills/final-exp/SKILL.md"
    role: "skill_source"
references: ["skill:final-exp", "source:schemas/skill_contracts.json#final-exp", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/final-exp.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# final-exp

## Purpose

Codex wrapper for WF11 final experiment planning. Use when the user wants ablations, robustness tests, cross-dataset evaluation, and compute budgeting organized according to the original template.

## Triggers

- `$final-exp`
- `/final-exp`
- `final experiment`
- `WF11`

## Can Write

- `docs/Final_Experiment_Matrix.md`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/Final_Experiment_Matrix.md`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/final-exp/SKILL.md`
- `.agents/skills/final-exp/references/experiment-matrix.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

## Must Prove

- `respect_evaluation_contract`
- `respect_claim_boundary`
- `check_dynamic_context_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF11_readiness`
- `final_experiment_matrix_write`
- `docs_site_render`

## Cannot Do

- `final_exp_outside_claim_boundary`
- `WF11_without_approved_contracts`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:final-exp]]
- [[source:schemas/skill_contracts.json#final-exp]]
- [[term:Gate Evidence]]
