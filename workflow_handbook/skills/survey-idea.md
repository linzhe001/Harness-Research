---
schema_version: "0.1"
page_id: "survey-idea"
title: "survey-idea"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/survey-idea.md"
source_of_truth: true
status: "generated"
summary: "Codex wrapper for WF1 idea survey and feasibility analysis. Use when the user wants literature-backed validation of a new research idea and a `docs/Feasibility_Report.md` outcome."
nav:
  section: "skills"
  position: 60
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "survey-idea"
  - path: ".agents/skills/survey-idea/SKILL.md"
    role: "skill_source"
references: ["skill:survey-idea", "source:schemas/skill_contracts.json#survey-idea", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/survey-idea.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# survey-idea

## Purpose

Codex wrapper for WF1 idea survey and feasibility analysis. Use when the user wants literature-backed validation of a new research idea and a `docs/Feasibility_Report.md` outcome.

## Triggers

- `$survey-idea`
- `/survey-idea`
- `survey-idea`
- `idea survey`
- `WF1`

## Can Write

- `docs/Feasibility_Report.md`
- `docs/30_evidence/`
- `docs/35_protocol/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/Feasibility_Report.md`
- `current_doc: docs/30_evidence/`
- `current_doc: docs/35_protocol/`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/survey-idea/SKILL.md`
- `.agents/skills/survey-idea/references/feasibility-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/30_evidence/Evidence_Index.md`
- `docs/30_evidence/Open_Questions.md`
- `docs/35_protocol/Research_Protocol.md`

## Must Prove

- `compile_protocol_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `evidence_table_write`
- `feasibility_report_write`
- `canonical_state_edit`
- `docs_site_render`

## Cannot Do

- `protocol_as_approved_contract`
- `direct_edit_evidence`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:survey-idea]]
- [[source:schemas/skill_contracts.json#survey-idea]]
- [[term:Gate Evidence]]
