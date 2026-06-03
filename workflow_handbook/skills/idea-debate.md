---
schema_version: "0.1"
page_id: "idea-debate"
title: "idea-debate"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/idea-debate.md"
source_of_truth: true
status: "generated"
summary: "Codex wrapper for WF2 idea debate. Use after WF1 feasibility to stress-test candidate research directions before WF3 refine-idea and before any architecture design."
nav:
  section: "skills"
  position: 70
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "idea-debate"
  - path: ".agents/skills/idea-debate/SKILL.md"
    role: "skill_source"
references: ["skill:idea-debate", "source:schemas/skill_contracts.json#idea-debate", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/idea-debate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# idea-debate

## Purpose

Codex wrapper for WF2 idea debate. Use after WF1 feasibility to stress-test candidate research directions before WF3 refine-idea and before any architecture design.

## Triggers

- `$idea-debate`
- `/idea-debate`
- `idea-debate`
- `idea debate`
- `WF2`

## Can Write

- `docs/Idea_Debate.md`
- `docs/35_protocol/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/Idea_Debate.md`
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

## Must Prove

- `compile_protocol_or_NOT_RUN`
- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `idea_debate_report_write`
- `protocol_doc_write`
- `canonical_state_edit`
- `docs_site_render`

## Cannot Do

- `protocol_as_approved_contract`
- `direct_edit_evidence`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:idea-debate]]
- [[source:schemas/skill_contracts.json#idea-debate]]
- [[term:Gate Evidence]]
