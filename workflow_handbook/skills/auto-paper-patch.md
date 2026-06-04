---
schema_version: "0.1"
page_id: "auto-paper-patch"
title: "auto-paper-patch"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-paper-patch.md"
source_of_truth: true
status: "generated"
summary: "Run the auto-paper patch phase. Use to produce bounded LaTeX or bibliography diffs from latex_patch_plan.md, write patch_ledger.md with guard results, and prepare apply-ready manuscript patches without bypassing artifact gates."
nav:
  section: "skills"
  position: 290
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-paper-patch"
  - path: ".agents/skills/auto-paper-patch/SKILL.md"
    role: "skill_source"
references: ["skill:auto-paper-patch", "source:schemas/skill_contracts.json#auto-paper-patch", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-paper-patch.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-paper-patch

## Purpose

Run the auto-paper patch phase. Use to produce bounded LaTeX or bibliography diffs from latex_patch_plan.md, write patch_ledger.md with guard results, and prepare apply-ready manuscript patches without bypassing artifact gates.

## Triggers

- `$auto-paper-patch`
- `/auto-paper-patch`
- `auto-paper patch`
- `auto paper patch`
- `patch ledger`
- `latex patch`

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
- `.agents/skills/auto-paper-patch/SKILL.md`
- `.agents/skills/auto-paper/SKILL.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/writing-rationale-matrix.md`
- `.agents/skills/auto-paper/references/latex-source-control.md`
- `.agents/skills/auto-paper/references/citation-support-bank.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `auto_paper_output/`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `auto_paper_patch`
- `latex_patch`
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

- [[skill:auto-paper-patch]]
- [[source:schemas/skill_contracts.json#auto-paper-patch]]
- [[term:Gate Evidence]]
