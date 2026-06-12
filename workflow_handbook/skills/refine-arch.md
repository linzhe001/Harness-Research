---
schema_version: "0.1"
page_id: "refine-arch"
title: "refine-arch"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/refine-arch.md"
source_of_truth: true
status: "generated"
summary: "Read these first:"
nav:
  section: "skills"
  position: 110
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "refine-arch"
  - path: ".agents/skills/refine-arch/SKILL.md"
    role: "skill_source"
references: ["skill:refine-arch", "source:schemas/skill_contracts.json#refine-arch", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/refine-arch.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# refine-arch

## Purpose

Read these first:

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$refine-arch`
- `/refine-arch`
- `refine-arch`
- `refine arch`
- `architecture design`
- `WF6`

## Can Write

- `docs/Technical_Spec.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/35_protocol/`
- `PROJECT_STATE.json`

## Final Outputs

- `current_doc: docs/Technical_Spec.md`
- `current_doc: docs/35_protocol/`
- `fact_doc: docs/20_facts/Project_Glossary.md`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/code-style.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/refine-arch/SKILL.md`
- `.agents/skills/refine-arch/references/technical-spec.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/Refined_Idea.md`
- `docs/Dataset_Stats.md`
- `docs/Baseline_Report.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`
- `docs/30_evidence/Evidence_Index.md`
- `docs/35_protocol/Research_Protocol.md`

## Must Prove

- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `technical_spec_write`
- `contract_conflict`
- `project_glossary_write`
- `canonical_state_edit`
- `docs_site_boundary_report`

## Cannot Do

- `protocol_as_approved_contract`
- `project_map_stale`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:refine-arch]]
- [[source:schemas/skill_contracts.json#refine-arch]]
- [[term:Gate Evidence]]
