---
schema_version: "0.1"
page_id: "data-prep"
title: "data-prep"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/data-prep.md"
source_of_truth: true
status: "generated"
summary: "Use this Skill for WF4 dataset analysis, subset design, and data-pipeline preparation."
nav:
  section: "skills"
  position: 90
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "data-prep"
  - path: ".agents/skills/data-prep/SKILL.md"
    role: "skill_source"
references: ["skill:data-prep", "source:schemas/skill_contracts.json#data-prep", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/data-prep.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# data-prep

## Purpose

Use this Skill for WF4 dataset analysis, subset design, and data-pipeline preparation.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$data-prep`
- `/data-prep`
- `data-prep`
- `dataset prep`
- `WF4`

## Can Write

- `docs/Dataset_Stats.md`
- `docs/20_facts/`
- `docs/30_evidence/Dataset_Table.md`
- `PROJECT_STATE.json`
- `CLAUDE.md`
- `AGENTS.md`
- `configs/`
- `src/`

## Final Outputs

- `current_doc: docs/Dataset_Stats.md`
- `conclusion_evidence: docs/30_evidence/Dataset_Table.md`
- `fact_doc: docs/20_facts/`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/data-prep/SKILL.md`
- `.agents/skills/data-prep/references/dataset-stats.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `CLAUDE.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/Refined_Idea.md`
- `docs/20_facts/Execution_Contract.md`
- `docs/30_evidence/Dataset_Table.md`

## Must Prove

- `compile_doc_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `archive_existing_data_docs_or_NOT_RUN`
- `dataset_acquisition_or_NOT_RUN`
- `dataset_acquisition_decision_request_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `data_doc_archive`
- `dataset_acquisition`
- `dataset_stats_write`
- `evidence_table_write`
- `dataset_config_write`
- `canonical_state_edit`
- `CLAUDE_dataset_sync`
- `docs_site_boundary_report`

## Cannot Do

- `direct_edit_evidence`
- `direct_edit_auto_iterate`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:data-prep]]
- [[source:schemas/skill_contracts.json#data-prep]]
- [[term:Gate Evidence]]
