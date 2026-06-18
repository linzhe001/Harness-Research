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
summary: "Internal Harness instruction source for final-exp. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 350
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

Internal Harness instruction source for final-exp. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$final-exp`
- `/final-exp`
- `final experiment`
- `WF11`

## Can Write

- `docs/Final_Experiment_Matrix.md`
- `PROJECT_STATE.json`

## Final Outputs

- `current_doc: docs/Final_Experiment_Matrix.md`

## Tool-Owned Outputs

- none

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
- `pre_eval_commit_or_NOT_CHANGED`
- `claim_delta_evidence_or_NOT_CHANGED`
- `automation_policy_respected`
- `gate_ledger`
- `docs_site_boundary_report`
- `WF11_readiness`
- `final_experiment_matrix_write`
- `claim_delta_evidence`
- `pre_eval_commit`
- `docs_site_boundary_report`

## Constraints

- `final_exp_outside_claim_boundary [workflow_default/ledger; exception=overlay_allowed]`
- `WF11_without_approved_contracts [workflow_default/ledger; exception=overlay_allowed]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:final-exp]]
- [[source:schemas/skill_contracts.json#final-exp]]
- [[term:Gate Evidence]]
