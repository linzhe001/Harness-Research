---
schema_version: "0.1"
page_id: "wf5_baseline_repro"
title: "WF5 Baseline Repro"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf5_baseline_repro.md"
source_of_truth: true
status: "generated"
summary: "Reproduce or establish a baseline and prepare approval-facing contracts."
nav:
  section: "stages"
  position: 50
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "baseline-repro"
  - path: ".agents/skills/baseline-repro/SKILL.md"
    role: "skill_source"
references: ["stage:WF5", "skill:baseline-repro", "source:schemas/skill_contracts.json#baseline-repro", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf5_baseline_repro.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF5 Baseline Repro

## Purpose

Reproduce or establish a baseline and prepare approval-facing contracts.

## How To Run

`$prepare` after executable baseline source provenance is approved.

## Completion Effect

Baseline report, baseline evidence, and draft or approved contracts are ready for later gates.

## Contract Detail

Read these first:

## Trigger Visibility

Inputs below are internal contract triggers or readiness signals. For normal operation, start from the stage's visible alias in `How To Run`; the only human-facing `$` entries are `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Inputs

- `$baseline-repro`
- `/baseline-repro`
- `baseline-repro`
- `baseline repro`
- `WF5`

## Outputs

- `current_doc: docs/Baseline_Report.md`
- `conclusion_evidence: docs/30_evidence/Baseline_Table.md`
- `approved_contract: docs/10_contract/`
- `fact_doc: docs/20_facts/Codebase_Map.md`
- `canonical_state: PROJECT_STATE.json`
- `canonical_state: project_map.json`
- `guidance: CLAUDE.md`
- `implementation: baselines/`
- `implementation: configs/`
- `implementation: scripts/`
- `implementation: src/`

## Required Reads

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/pre-training-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/baseline-repro/SKILL.md`
- `.agents/skills/baseline-repro/references/baseline-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `CLAUDE.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `project_map.json`
- `docs/Refined_Idea.md`
- `docs/Dataset_Stats.md`
- `docs/30_evidence/Baseline_Table.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/35_protocol/Research_Protocol.md`

## Gates

- `check_protocol_drift_or_NOT_RUN`
- `check_dynamic_context_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `codebase_map_sync_when_baseline_layout_changes`
- `semantic_commit_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `baseline_report_write`
- `evidence_table_write`
- `codebase_map_write`
- `baseline_contract_readiness`
- `evaluation_contract_readiness`
- `canonical_state_edit`
- `stable_code_change`
- `docs_site_boundary_report`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:baseline-repro]]

## Related References

- [[stage:WF5]]
- [[skill:baseline-repro]]
- [[source:schemas/skill_contracts.json#baseline-repro]]
- [[term:Gate Evidence]]
