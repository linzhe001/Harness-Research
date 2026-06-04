---
schema_version: "0.1"
page_id: "auto-paper-response"
title: "auto-paper-response"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-paper-response.md"
source_of_truth: true
status: "generated"
summary: "Run the optional auto-paper reviewer-response branch. Use when Codex needs to handle rebuttal writing, revision response letters, reviewer comment maps, response strategy, or revision commitment registers for an academic manuscript."
nav:
  section: "skills"
  position: 310
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-paper-response"
  - path: ".agents/skills/auto-paper-response/SKILL.md"
    role: "skill_source"
references: ["skill:auto-paper-response", "source:schemas/skill_contracts.json#auto-paper-response", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-paper-response.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-paper-response

## Purpose

Run the optional auto-paper reviewer-response branch. Use when Codex needs to handle rebuttal writing, revision response letters, reviewer comment maps, response strategy, or revision commitment registers for an academic manuscript.

## Triggers

- `$auto-paper-response`
- `/auto-paper-response`
- `auto-paper response`
- `auto paper response`
- `reviewer response`
- `rebuttal`
- `response letter`

## Can Write

- `auto_paper_output/`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: auto_paper_output/`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/language-policy.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/auto-paper-response/SKILL.md`
- `.agents/skills/auto-paper/SKILL.md`
- `.agents/skills/auto-paper/references/auto-paper-loop.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/citation-support-bank.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `auto_paper_output/`
- `reviewer_comments.md`
- `decision_letter.md`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `auto_paper_response`
- `human_gate`
- `docs_site_render`

## Cannot Do

- `direct_edit_auto_iterate`
- `manual_edit_auto_iterate`
- `direct_edit_evidence`
- `manual_edit_evidence_chain`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:auto-paper-response]]
- [[source:schemas/skill_contracts.json#auto-paper-response]]
- [[term:Gate Evidence]]
