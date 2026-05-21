---
schema_version: "0.1"
page_id: "wf9_validate_run"
title: "WF9 Validate Run"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf9_validate_run.md"
source_of_truth: true
status: "generated"
summary: "Validate the implementation before structured iteration."
nav:
  section: "stages"
  position: 90
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "validate-run"
  - path: ".agents/skills/validate-run/SKILL.md"
    role: "skill_source"
references: ["stage:WF9", "skill:validate-run", "source:schemas/skill_contracts.json#validate-run", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf9_validate_run.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF9 Validate Run

## Purpose

Validate the implementation before structured iteration.

## How To Run

`$validate-run` with the acceptance commands and expected behavior.

## Completion Effect

`docs/Validate_Run_Report.md` records PASS, REVIEW, or FAIL with Gate Evidence.

## Contract Detail

Codex wrapper for WF9 validation. Use when the user wants the training chain reviewed and smoke-tested before entering WF10.

## Inputs

- `$validate-run`
- `/validate-run`
- `validate-run`
- `smoke test`
- `WF9`

## Outputs

- `current_doc: docs/Validate_Run_Report.md`
- `conclusion_evidence: docs/30_evidence/Validation_Table.md`
- `canonical_state: PROJECT_STATE.json`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Required Reads

- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/skills/validate-run/SKILL.md`
- `.agents/skills/validate-run/references/review-checklist.md`
- `.agents/skills/validate-run/references/validate-run-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `CLAUDE.md`
- `docs/Implementation_Roadmap.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Technical_Spec.md`
- `docs/Baseline_Report.md`
- `docs/30_evidence/Validation_Table.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`

## Gates

- `semantic_review`
- `smoke_test_or_NOT_RUN`
- `write_validate_report`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF10_readiness`
- `validate_report_write`
- `evidence_table_write`
- `docs_site_render`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:validate-run]]

## Related References

- [[stage:WF9]]
- [[skill:validate-run]]
- [[source:schemas/skill_contracts.json#validate-run]]
- [[term:Gate Evidence]]
