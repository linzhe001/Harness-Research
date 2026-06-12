---
schema_version: "0.1"
page_id: "orchestrator"
title: "orchestrator"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/orchestrator.md"
source_of_truth: true
status: "generated"
summary: "Read these first:"
nav:
  section: "skills"
  position: 0
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "orchestrator"
  - path: ".agents/skills/orchestrator/SKILL.md"
    role: "skill_source"
references: ["skill:orchestrator", "source:schemas/skill_contracts.json#orchestrator", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/orchestrator.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# orchestrator

## Purpose

Read these first:

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$orchestrator`
- `/orchestrator`
- `orchestrator`
- `stage transition`
- `advance stage`
- `rollback`
- `workflow status`

## Can Write

- `PROJECT_STATE.json`
- `iteration_log.json`
- `project_map.json`

## Final Outputs

- `canonical_state: PROJECT_STATE.json`
- `canonical_state: iteration_log.json`
- `canonical_state: project_map.json`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/language-policy.md`
- `.agents/skills/orchestrator/SKILL.md`
- `.agents/skills/orchestrator/references/stage-gates.md`
- `.agents/skills/orchestrator/references/project-state-schema.json`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `project_map.json`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

## Must Prove

- `explicit_user_approval_for_transition`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `stage_transition`
- `canonical_state_edit`
- `WF10_readiness`
- `WF11_readiness`
- `WF12_readiness`

## Cannot Do

- `stage_transition_without_user_approval`
- `direct_edit_auto_iterate`
- `direct_edit_evidence`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:orchestrator]]
- [[source:schemas/skill_contracts.json#orchestrator]]
- [[term:Gate Evidence]]
