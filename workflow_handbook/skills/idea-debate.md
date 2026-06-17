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
summary: "Internal Harness instruction source for idea-debate. Route through visible Harness aliases or hook contracts instead of invoking directly."
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

Internal Harness instruction source for idea-debate. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

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

## Final Outputs

- `current_doc: docs/Idea_Debate.md`
- `current_doc: docs/35_protocol/`

## Tool-Owned Outputs

- none

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
- `docs_site_boundary_report`
- `idea_debate_report_write`
- `protocol_doc_write`
- `canonical_state_edit`
- `docs_site_boundary_report`

## Constraints

- `protocol_as_approved_contract [hard_invariant/block; exception=never]`
- `direct_edit_evidence [hard_invariant/block; exception=never]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:idea-debate]]
- [[source:schemas/skill_contracts.json#idea-debate]]
- [[term:Gate Evidence]]
