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
summary: "Codex wrapper for WF5 baseline reproduction. Use when the user wants baseline adaptation, reproduction tracking, and `docs/Baseline_Report.md` following the original workflow contract."
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

Codex wrapper for WF5 baseline reproduction. Use when the user wants baseline adaptation, reproduction tracking, and `docs/Baseline_Report.md` following the original workflow contract.

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
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/Baseline_Report.md`
- `conclusion_evidence: docs/30_evidence/Baseline_Table.md`
- `approved_contract: docs/10_contract/`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

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

## Must Prove

- `check_protocol_drift_or_NOT_RUN`
- `check_dynamic_context_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `codebase_map_sync_when_baseline_layout_changes`
- `semantic_commit_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `baseline_report_write`
- `evidence_table_write`
- `codebase_map_write`
- `baseline_contract_readiness`
- `evaluation_contract_readiness`
- `canonical_state_edit`
- `stable_code_change`
- `docs_site_render`

## Cannot Do

- `training_without_semantic_commit`
- `approve_without_explicit_human_approval`
- `protocol_as_approved_contract`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:baseline-repro]]
- [[source:schemas/skill_contracts.json#baseline-repro]]
- [[term:Gate Evidence]]
