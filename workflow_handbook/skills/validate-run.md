---
schema_version: "0.1"
page_id: "validate-run"
title: "validate-run"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/validate-run.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for validate-run. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 210
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "validate-run"
  - path: ".agents/skills/validate-run/SKILL.md"
    role: "skill_source"
references: ["skill:validate-run", "source:schemas/skill_contracts.json#validate-run", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/validate-run.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# validate-run

## Purpose

Internal Harness instruction source for validate-run. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$validate-run`
- `/validate-run`
- `validate-run`
- `smoke test`
- `WF9`

## Can Write

- `docs/Validate_Run_Report.md`
- `docs/30_evidence/Validation_Table.md`
- `PROJECT_STATE.json`

## Final Outputs

- `current_doc: docs/Validate_Run_Report.md`
- `conclusion_evidence: docs/30_evidence/Validation_Table.md`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/run-artifact-contract.md`
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

## Must Prove

- `semantic_review`
- `smoke_test_or_NOT_RUN`
- `write_validate_report`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `validate_run_verdict_gate`
- `WF10_readiness`
- `validate_report_write`
- `evidence_table_write`
- `docs_site_boundary_report`
- `validate_run_verdict`

## Constraints

- `WF9_PASS_without_semantic_review [workflow_default/ledger; exception=overlay_allowed]`
- `WF9_PASS_without_smoke_evidence [workflow_default/ledger; exception=overlay_allowed]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:validate-run]]
- [[source:schemas/skill_contracts.json#validate-run]]
- [[term:Gate Evidence]]
