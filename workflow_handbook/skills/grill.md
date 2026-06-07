---
schema_version: "0.1"
page_id: "grill"
title: "grill"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/grill.md"
source_of_truth: true
status: "generated"
summary: "Clarify early research intent through hard questions and produce draft-only Research Intent, Grill Round Log, and Execution Readiness Packet artifacts. Does not approve contracts or complete WF1-WF3 by itself."
nav:
  section: "skills"
  position: 370
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "grill"
  - path: ".agents/skills/grill/SKILL.md"
    role: "skill_source"
references: ["skill:grill", "source:schemas/skill_contracts.json#grill", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/grill.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# grill

## Purpose

Clarify early research intent through hard questions and produce draft-only Research Intent, Grill Round Log, and Execution Readiness Packet artifacts. Does not approve contracts or complete WF1-WF3 by itself.

## Triggers

- `$grill`
- `/grill`
- `grill`
- `harness grill`
- `Research Intent Draft`
- `Execution Readiness Packet`
- `delta grill`

## Can Write

- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- none

## Tool-Owned Outputs

- `tool_trace: .workflow_supervisor/readiness.json`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/skills/grill/SKILL.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `OPERATOR_CONTEXT.md`
- `docs/Feasibility_Report.md`
- `docs/Idea_Debate.md`
- `docs/Refined_Idea.md`
- `docs/30_evidence/Open_Questions.md`
- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`

## Must Prove

- `gate_ledger`
- `grill_round_contract`
- `gap_check`
- `human_exit_decision_status`
- `docs_site_render_or_NOT_RUN`
- `grill_draft_write`
- `readiness_packet_write`
- `readiness_json_write`
- `docs_site_render`

## Cannot Do

- `direct_edit_evidence`
- `direct_edit_auto_iterate`
- `direct_edit_workflow_supervisor`
- `protocol_as_approved_contract`
- `packet_as_approval`
- `stage_transition_without_user_approval`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:grill]]
- [[source:schemas/skill_contracts.json#grill]]
- [[term:Gate Evidence]]
