---
schema_version: "0.1"
page_id: "wf2_idea_debate"
title: "WF2 Idea Debate"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf2_idea_debate.md"
source_of_truth: true
status: "generated"
summary: "Compare candidate directions and choose the strongest research path."
nav:
  section: "stages"
  position: 20
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "idea-debate"
  - path: ".agents/skills/idea-debate/SKILL.md"
    role: "skill_source"
references: ["stage:WF2", "skill:idea-debate", "source:schemas/skill_contracts.json#idea-debate", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf2_idea_debate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF2 Idea Debate

## Purpose

Compare candidate directions and choose the strongest research path.

## How To Run

`$idea-debate` after WF1 has enough evidence to compare options.

## Completion Effect

`docs/Idea_Debate.md` records the selected direction, alternatives, and risks.

## Contract Detail

Codex wrapper for WF2 idea debate. Use after WF1 feasibility to stress-test candidate research directions before WF3 refine-idea and before any architecture design.

## Inputs

- `$idea-debate`
- `/idea-debate`
- `idea-debate`
- `idea debate`
- `WF2`

## Outputs

- `current_doc: docs/Idea_Debate.md`
- `current_doc: docs/35_protocol/`
- `canonical_state: PROJECT_STATE.json`

## Required Reads

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/references/language-policy.md`
- `.agents/skills/idea-debate/SKILL.md`
- `.agents/skills/idea-debate/references/idea-debate-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/Feasibility_Report.md`
- `docs/30_evidence/Evidence_Index.md`
- `docs/35_protocol/Research_Protocol.md`

## Gates

- `compile_protocol_or_NOT_RUN`
- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `idea_debate_report_write`
- `protocol_doc_write`
- `canonical_state_edit`
- `docs_site_boundary_report`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:idea-debate]]

## Related References

- [[stage:WF2]]
- [[skill:idea-debate]]
- [[source:schemas/skill_contracts.json#idea-debate]]
- [[term:Gate Evidence]]
