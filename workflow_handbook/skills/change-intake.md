---
schema_version: "0.1"
page_id: "change-intake"
title: "change-intake"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/change-intake.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for change-intake. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 390
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "change-intake"
  - path: ".agents/skills/change-intake/SKILL.md"
    role: "skill_source"
references: ["skill:change-intake", "source:schemas/skill_contracts.json#change-intake", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/change-intake.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# change-intake

## Purpose

Internal Harness instruction source for change-intake. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$change-intake`
- `/change-intake`
- `change-intake`
- `harness change`
- `change request`
- `new request`
- `new idea after codebase`
- `codebase delta`

## Can Write

- `docs/Change_Request.md`

## Final Outputs

- none

## Tool-Owned Outputs

- `tool_trace: .workflow_supervisor/runs/`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/project-map-rule.md`
- `.agents/skills/change-intake/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `docs/20_facts/Codebase_Map.md`
- `iteration_log.json`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`
- `docs/20_facts/Project_Glossary.md`

## Must Prove

- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `change_request_classification`
- `contract_impact_detected`
- `change_route_selected`

## Cannot Do

- `direct_edit_evidence`
- `direct_edit_auto_iterate`
- `direct_edit_workflow_supervisor`
- `approve_without_explicit_human_approval`
- `stage_transition_without_user_approval`
- `packet_as_approval`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:change-intake]]
- [[source:schemas/skill_contracts.json#change-intake]]
- [[term:Gate Evidence]]
