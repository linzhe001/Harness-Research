---
schema_version: "0.1"
page_id: "auto-paper-figure"
title: "auto-paper-figure"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-paper-figure.md"
source_of_truth: true
status: "generated"
summary: "Run the optional auto-paper figure and caption branch. Use when Codex needs to audit figure assets, define figure contracts, map caption claims to evidence, or plan/generate manuscript figures only after figure requirements are explicit."
nav:
  section: "skills"
  position: 330
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-paper-figure"
  - path: ".agents/skills/auto-paper-figure/SKILL.md"
    role: "skill_source"
references: ["skill:auto-paper-figure", "source:schemas/skill_contracts.json#auto-paper-figure", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-paper-figure.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-paper-figure

## Purpose

Run the optional auto-paper figure and caption branch. Use when Codex needs to audit figure assets, define figure contracts, map caption claims to evidence, or plan/generate manuscript figures only after figure requirements are explicit.

## Triggers

- `$auto-paper-figure`
- `/auto-paper-figure`
- `auto-paper figure`
- `auto paper figure`
- `figure contract`
- `caption audit`
- `caption claim map`

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
- `.agents/skills/auto-paper-figure/SKILL.md`
- `.agents/skills/auto-paper/SKILL.md`
- `.agents/skills/auto-paper/references/auto-paper-loop.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/citation-support-bank.md`
- `.agents/skills/auto-paper/references/latex-source-control.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `auto_paper_output/`
- `figures/`
- `plots/`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `auto_paper_figure`
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

- [[skill:auto-paper-figure]]
- [[source:schemas/skill_contracts.json#auto-paper-figure]]
- [[term:Gate Evidence]]
