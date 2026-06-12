---
schema_version: "0.1"
page_id: "wf1_survey_idea"
title: "WF1 Survey Idea"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf1_survey_idea.md"
source_of_truth: true
status: "generated"
summary: "Collect early Conclusion Evidence and decide whether the idea is worth pursuing."
nav:
  section: "stages"
  position: 10
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "survey-idea"
  - path: ".agents/skills/survey-idea/SKILL.md"
    role: "skill_source"
references: ["stage:WF1", "skill:survey-idea", "source:schemas/skill_contracts.json#survey-idea", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf1_survey_idea.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF1 Survey Idea

## Purpose

Collect early Conclusion Evidence and decide whether the idea is worth pursuing.

## How To Run

`$grill` when the idea still needs evidence-backed clarification.

## Completion Effect

`docs/Feasibility_Report.md` and evidence tables summarize viability and open questions.

## Contract Detail

Internal Harness instruction source for survey-idea. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Trigger Visibility

Inputs below are internal contract triggers or readiness signals. For normal operation, start from the stage's visible alias in `How To Run`; the only human-facing `$` entries are `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Inputs

- `$survey-idea`
- `/survey-idea`
- `survey-idea`
- `idea survey`
- `WF1`

## Outputs

- `current_doc: docs/Feasibility_Report.md`
- `current_doc: docs/30_evidence/`
- `current_doc: docs/35_protocol/`
- `canonical_state: PROJECT_STATE.json`

## Required Reads

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

## Gates

- `compile_protocol_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `evidence_table_write`
- `feasibility_report_write`
- `canonical_state_edit`
- `docs_site_boundary_report`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:survey-idea]]

## Related References

- [[stage:WF1]]
- [[skill:survey-idea]]
- [[source:schemas/skill_contracts.json#survey-idea]]
- [[term:Gate Evidence]]
