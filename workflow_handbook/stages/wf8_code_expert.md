---
schema_version: "0.1"
page_id: "wf8_code_expert"
title: "WF8 Code Expert"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf8_code_expert.md"
source_of_truth: true
status: "generated"
summary: "Implement one bounded code slice under the current plan."
nav:
  section: "stages"
  position: 80
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "code-expert"
  - path: ".agents/skills/code-expert/SKILL.md"
    role: "skill_source"
references: ["stage:WF8", "skill:code-expert", "source:schemas/skill_contracts.json#code-expert", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf8_code_expert.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF8 Code Expert

## Purpose

Implement one bounded code slice under the current plan.

## How To Run

`$build` for first-pass implementation, or `$change` for later code deltas.

## Completion Effect

Changed code, focused validation, and map updates are ready for review.

## Contract Detail

Read these first:

## Trigger Visibility

Inputs below are internal contract triggers or readiness signals. For normal operation, start from the stage's visible alias in `How To Run`; the only human-facing `$` entries are `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Inputs

- `$code-expert`
- `/code-expert`
- `code-expert`
- `implement`
- `WF8`

## Outputs

- `implementation: src/`
- `implementation: scripts/`
- `implementation: configs/`
- `fact_doc: docs/20_facts/Codebase_Map.md`
- `canonical_state: project_map.json`
- `canonical_state: PROJECT_STATE.json`
- `tool_trace: .evidence/chains/`
- `tool_trace: .evidence/index.json`

## Required Reads

- `.agents/references/code-style.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/language-policy.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/pre-training-rule.md`
- `.agents/references/sliced-commit-rule.md`
- `.agents/skills/code-expert/SKILL.md`
- `.agents/skills/code-expert/references/generation-order.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `CLAUDE.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Implementation_Roadmap.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`

## Gates

- `read_project_map_before_stable_code`
- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `semantic_commit_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `compile_doc_or_NOT_RUN`
- `stable_code_change`
- `project_map_write`
- `codebase_map_write`
- `canonical_state_edit`
- `codebase_map_docchain`
- `docs_site_boundary_report`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:code-expert]]

## Related References

- [[stage:WF8]]
- [[skill:code-expert]]
- [[source:schemas/skill_contracts.json#code-expert]]
- [[term:Gate Evidence]]
