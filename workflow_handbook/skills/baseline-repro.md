---
schema_version: "0.1"
page_id: "baseline-repro"
title: "baseline-repro"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/baseline-repro.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for baseline-repro. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 100
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "baseline-repro"
  - path: ".agents/skills/baseline-repro/SKILL.md"
    role: "skill_source"
references: ["skill:baseline-repro", "source:schemas/skill_contracts.json#baseline-repro", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/baseline-repro.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# baseline-repro

## Purpose

Internal Harness instruction source for baseline-repro. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$baseline-repro`
- `/baseline-repro`
- `baseline-repro`
- `baseline repro`
- `WF5`

## Can Write

- `docs/Baseline_Report.md`
- `docs/30_evidence/Baseline_Table.md`
- `docs/10_contract/`
- `docs/20_facts/Codebase_Map.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `CLAUDE.md`
- `baselines/`
- `configs/`
- `scripts/`
- `src/`

## Final Outputs

- `current_doc: docs/Baseline_Report.md`
- `conclusion_evidence: docs/30_evidence/Baseline_Table.md`
- `approved_contract: docs/10_contract/`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/pre-training-rule.md`
- `.agents/references/run-artifact-contract.md`
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

## Must Prove

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

## Constraints

- `training_without_semantic_commit [advisory/notice; exception=not_required]`
- `approve_without_explicit_human_approval [hard_invariant/block; exception=never]`
- `protocol_as_approved_contract [hard_invariant/block; exception=never]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:baseline-repro]]
- [[source:schemas/skill_contracts.json#baseline-repro]]
- [[term:Gate Evidence]]
