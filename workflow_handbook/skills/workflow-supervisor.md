---
schema_version: "0.1"
page_id: "workflow-supervisor"
title: "workflow-supervisor"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/workflow-supervisor.md"
source_of_truth: true
status: "generated"
summary: "Use this Skill for `harness prepare`, `build`, `iterate`, `release`, `change`, or direct `workflow_ctl` work. The supervisor orchestrates existing Skills; it does not replace Stage Skills, Evidence Chain tooling, Gate Evidence, or Human Approval."
nav:
  section: "skills"
  position: 380
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "workflow-supervisor"
  - path: ".agents/skills/workflow-supervisor/SKILL.md"
    role: "skill_source"
references: ["skill:workflow-supervisor", "source:schemas/skill_contracts.json#workflow-supervisor", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/workflow-supervisor.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# workflow-supervisor

## Purpose

Use this Skill for `harness prepare`, `build`, `iterate`, `release`, `change`, or direct `workflow_ctl` work. The supervisor orchestrates existing Skills; it does not replace Stage Skills, Evidence Chain tooling, Gate Evidence, or Human Approval.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$workflow-supervisor`
- `/workflow-supervisor`
- `workflow supervisor`
- `workflow_ctl`
- `harness prepare`
- `harness build`
- `harness iterate`
- `harness release`
- `harness change`
- `execution supervisor`

## Can Write

- `.workflow_supervisor/`

## Final Outputs

- none

## Tool-Owned Outputs

- `tool_trace: .workflow_supervisor/`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/skills/workflow-supervisor/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `project_map.json`
- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`
- `docs/auto_iterate_goal.md`
- `.auto_iterate/state.json`

## Must Prove

- `workflow_state_gate_or_NOT_RUN`
- `build_review_packet_or_NOT_RUN`
- `gate_ledger`
- `supervisor_runtime_write`
- `human_interrupt_created`
- `approval_resume`
- `worker_result_validation`
- `WF10_readiness`

## Cannot Do

- `direct_edit_evidence`
- `direct_edit_auto_iterate`
- `direct_edit_workflow_supervisor`
- `approve_without_explicit_human_approval`
- `stage_transition_without_user_approval`
- `packet_as_approval`
- `start_auto_iterate_without_goal_validation`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:workflow-supervisor]]
- [[source:schemas/skill_contracts.json#workflow-supervisor]]
- [[term:Gate Evidence]]
