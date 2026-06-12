---
schema_version: "0.1"
page_id: "auto-paper-intake"
title: "auto-paper-intake"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-paper-intake.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for auto-paper-intake. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 240
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-paper-intake"
  - path: ".agents/skills/auto-paper-intake/SKILL.md"
    role: "skill_source"
references: ["skill:auto-paper-intake", "source:schemas/skill_contracts.json#auto-paper-intake", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-paper-intake.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-paper-intake

## Purpose

Internal Harness instruction source for auto-paper-intake. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$auto-paper-intake`
- `/auto-paper-intake`
- `auto-paper intake`
- `auto paper intake`
- `paper intake`
- `start auto-paper`

## Can Write

- `auto_paper_output/`
- `docs/auto_paper_goal.md`

## Final Outputs

- `current_doc: auto_paper_output/`
- `current_doc: docs/auto_paper_goal.md`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/language-policy.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/auto-paper-intake/SKILL.md`
- `.agents/skills/auto-paper/SKILL.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/auto-iterate-boundary.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `docs/auto_paper_goal.md`
- `auto_paper_output/`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `auto_paper_intake`
- `human_gate`
- `docs_site_boundary_report`

## Cannot Do

- `direct_edit_auto_iterate`
- `manual_edit_auto_iterate`
- `direct_edit_evidence`
- `manual_edit_evidence_chain`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:auto-paper-intake]]
- [[source:schemas/skill_contracts.json#auto-paper-intake]]
- [[term:Gate Evidence]]
