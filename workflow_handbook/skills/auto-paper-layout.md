---
schema_version: "0.1"
page_id: "auto-paper-layout"
title: "auto-paper-layout"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-paper-layout.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for auto-paper-layout. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 280
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-paper-layout"
  - path: ".agents/skills/auto-paper-layout/SKILL.md"
    role: "skill_source"
references: ["skill:auto-paper-layout", "source:schemas/skill_contracts.json#auto-paper-layout", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-paper-layout.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-paper-layout

## Purpose

Internal Harness instruction source for auto-paper-layout. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$auto-paper-layout`
- `/auto-paper-layout`
- `auto-paper layout`
- `auto paper layout`
- `writing rationale matrix`
- `latex patch plan`

## Can Write

- `auto_paper_output/`

## Final Outputs

- `current_doc: auto_paper_output/`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/language-policy.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/auto-paper-layout/SKILL.md`
- `.agents/skills/auto-paper/SKILL.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/writing-rationale-matrix.md`
- `.agents/skills/auto-paper/references/latex-source-control.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `auto_paper_output/`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `auto_paper_layout`
- `human_gate`
- `docs_site_boundary_report`

## Constraints

- `direct_edit_auto_iterate [hard_invariant/block; exception=never]`
- `manual_edit_auto_iterate [hard_invariant/block; exception=never]`
- `direct_edit_evidence [hard_invariant/block; exception=never]`
- `manual_edit_evidence_chain [hard_invariant/block; exception=never]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:auto-paper-layout]]
- [[source:schemas/skill_contracts.json#auto-paper-layout]]
- [[term:Gate Evidence]]
