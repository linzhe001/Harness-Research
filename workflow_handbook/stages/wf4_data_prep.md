---
schema_version: "0.1"
page_id: "wf4_data_prep"
title: "WF4 Data Prep"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf4_data_prep.md"
source_of_truth: true
status: "generated"
summary: "Make data facts explicit before baseline or architecture work starts."
nav:
  section: "stages"
  position: 40
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "data-prep"
  - path: ".agents/skills/data-prep/SKILL.md"
    role: "skill_source"
references: ["stage:WF4", "skill:data-prep", "source:schemas/skill_contracts.json#data-prep", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf4_data_prep.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF4 Data Prep

## Purpose

Make data facts explicit before baseline or architecture work starts.

## How To Run

`$prepare` after Grill readiness records dataset sources and targets.

## Completion Effect

Dataset stats, data facts, configs, and evidence tables are current.

## Contract Detail

Internal Harness instruction source for data-prep. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Trigger Visibility

Inputs below are internal contract triggers or readiness signals. For normal operation, start from the stage's visible alias in `How To Run`; the only human-facing `$` entries are `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Inputs

- `$data-prep`
- `/data-prep`
- `data-prep`
- `dataset prep`
- `WF4`

## Outputs

- `current_doc: docs/Dataset_Stats.md`
- `conclusion_evidence: docs/30_evidence/Dataset_Table.md`
- `fact_doc: docs/20_facts/`
- `canonical_state: PROJECT_STATE.json`
- `guidance: CLAUDE.md`
- `guidance: AGENTS.md`
- `implementation: configs/`
- `implementation: src/`

## Required Reads

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

## Gates

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

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:data-prep]]

## Related References

- [[stage:WF4]]
- [[skill:data-prep]]
- [[source:schemas/skill_contracts.json#data-prep]]
- [[term:Gate Evidence]]
