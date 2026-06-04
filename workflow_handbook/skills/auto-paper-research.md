---
schema_version: "0.1"
page_id: "auto-paper-research"
title: "auto-paper-research"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-paper-research.md"
source_of_truth: true
status: "generated"
summary: "Run the auto-paper research phase for a LaTeX manuscript. Use to build local source context, summarize author evidence, learn exemplar structure and style, map SOTA gaps, and prepare research artifacts without editing the manuscript."
nav:
  section: "skills"
  position: 250
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-paper-research"
  - path: ".agents/skills/auto-paper-research/SKILL.md"
    role: "skill_source"
references: ["skill:auto-paper-research", "source:schemas/skill_contracts.json#auto-paper-research", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-paper-research.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-paper-research

## Purpose

Run the auto-paper research phase for a LaTeX manuscript. Use to build local source context, summarize author evidence, learn exemplar structure and style, map SOTA gaps, and prepare research artifacts without editing the manuscript.

## Triggers

- `$auto-paper-research`
- `/auto-paper-research`
- `auto-paper research`
- `auto paper research`
- `research dossier`
- `style profile`

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
- `.agents/skills/auto-paper-research/SKILL.md`
- `.agents/skills/auto-paper/SKILL.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/auto-paper-loop.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `auto_paper_output/`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `auto_paper_research`
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

- [[skill:auto-paper-research]]
- [[source:schemas/skill_contracts.json#auto-paper-research]]
- [[term:Gate Evidence]]
