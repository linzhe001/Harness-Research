---
schema_version: "0.1"
page_id: "wf6_refine_arch"
title: "WF6 Refine Arch"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf6_refine_arch.md"
source_of_truth: true
status: "generated"
summary: "Refine the technical architecture within approved boundaries."
nav:
  section: "stages"
  position: 60
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "refine-arch"
  - path: ".agents/skills/refine-arch/SKILL.md"
    role: "skill_source"
references: ["stage:WF6", "skill:refine-arch", "source:schemas/skill_contracts.json#refine-arch", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf6_refine_arch.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF6 Refine Arch

## Purpose

Refine the technical architecture within approved boundaries.

## How To Run

`$refine-arch` after baseline and contract boundaries are available.

## Completion Effect

`docs/Technical_Spec.md` and glossary updates define the implementation shape.

## Contract Detail

Codex wrapper for WF6 architecture design. Use after WF4 data preparation and WF5 baseline reproduction to convert the refined idea, dataset facts, baseline evidence, and evaluation contract into a technical spec and MVP architecture.

## Inputs

- `$refine-arch`
- `/refine-arch`
- `refine-arch`
- `refine arch`
- `architecture design`
- `WF6`

## Outputs

- `current_doc: docs/Technical_Spec.md`
- `current_doc: docs/35_protocol/`
- `fact_doc: docs/20_facts/Project_Glossary.md`
- `canonical_state: PROJECT_STATE.json`

## Required Reads

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

## Gates

- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `technical_spec_write`
- `contract_conflict`
- `project_glossary_write`
- `canonical_state_edit`
- `docs_site_boundary_report`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:refine-arch]]

## Related References

- [[stage:WF6]]
- [[skill:refine-arch]]
- [[source:schemas/skill_contracts.json#refine-arch]]
- [[term:Gate Evidence]]
