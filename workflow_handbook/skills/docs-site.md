---
schema_version: "0.1"
page_id: "docs-site"
title: "docs-site"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/docs-site.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for docs-site. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 20
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "docs-site"
  - path: ".agents/skills/docs-site/SKILL.md"
    role: "skill_source"
references: ["skill:docs-site", "source:schemas/skill_contracts.json#docs-site", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/docs-site.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# docs-site

## Purpose

Internal Harness instruction source for docs-site. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$docs-site`
- `/docs-site`
- `docs-site`
- `docs site`
- `render docs`
- `HTML docs`
- `human docs`
- `rebuild docs site`

## Can Write

- `docs/_views/`
- `docs/_site/`

## Final Outputs

- none

## Tool-Owned Outputs

- `generated_view: docs/_site/`
- `tool_trace: docs/_views/evidence_preview_index.json`
- `tool_trace: docs/_site/manifest.json`

## Must Read

- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/skills/docs-site/SKILL.md`
- `AGENTS.md`
- `.evidence/index.json`
- `docs/10_contract/Project_Contract.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/Technical_Spec.md`
- `docs/Implementation_Roadmap.md`
- `docs/Validate_Run_Report.md`
- `docs/30_evidence/Validation_Table.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `docs/_views/evidence_preview_index.json`
- `docs/_site/manifest.json`

## Must Prove

- `build_evidence_preview_index_or_NOT_RUN`
- `build_docs_site_or_NOT_RUN`
- `validate_docs_site_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render`
- `human_doc_html_write`
- `preview_index_write`

## Cannot Do

- `manual_edit_evidence_chain`
- `direct_edit_evidence`
- `edit_source_markdown_during_render`
- `html_as_source_of_truth`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:docs-site]]
- [[source:schemas/skill_contracts.json#docs-site]]
- [[term:Gate Evidence]]
