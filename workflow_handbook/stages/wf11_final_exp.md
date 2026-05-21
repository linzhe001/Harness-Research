---
schema_version: "0.1"
page_id: "wf11_final_exp"
title: "WF11 Final Exp"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf11_final_exp.md"
source_of_truth: true
status: "generated"
summary: "Run final experiment checks against approved contracts and claim boundaries."
nav:
  section: "stages"
  position: 110
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "final-exp"
  - path: ".agents/skills/final-exp/SKILL.md"
    role: "skill_source"
references: ["stage:WF11", "skill:final-exp", "source:schemas/skill_contracts.json#final-exp", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf11_final_exp.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF11 Final Exp

## Purpose

Run final experiment checks against approved contracts and claim boundaries.

## How To Run

`$final-exp` after WF10 evidence supports a final evaluation.

## Completion Effect

`docs/Final_Experiment_Matrix.md` records the final experiment plan and gate result.

## Contract Detail

Codex wrapper for WF11 final experiment planning. Use when the user wants ablations, robustness tests, cross-dataset evaluation, and compute budgeting organized according to the original template.

## Inputs

- `$final-exp`
- `/final-exp`
- `final experiment`
- `WF11`

## Outputs

- `current_doc: docs/Final_Experiment_Matrix.md`
- `canonical_state: PROJECT_STATE.json`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Required Reads

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

## Gates

- `respect_evaluation_contract`
- `respect_claim_boundary`
- `check_dynamic_context_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF11_readiness`
- `final_experiment_matrix_write`
- `docs_site_render`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:final-exp]]

## Related References

- [[stage:WF11]]
- [[skill:final-exp]]
- [[source:schemas/skill_contracts.json#final-exp]]
- [[term:Gate Evidence]]
