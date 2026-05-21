---
schema_version: "0.1"
page_id: "code-expert"
title: "code-expert"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/code-expert.md"
source_of_truth: true
status: "generated"
summary: "Codex wrapper for WF8 first-pass code generation. Use when the user wants implementation generated directly from `project_map.json`, `docs/20_facts/Codebase_Map.md`, the roadmap, and the original Claude skill contract."
nav:
  section: "skills"
  position: 170
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "code-expert"
  - path: ".agents/skills/code-expert/SKILL.md"
    role: "skill_source"
references: ["skill:code-expert", "source:schemas/skill_contracts.json#code-expert", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/code-expert.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# code-expert

## Purpose

Codex wrapper for WF8 first-pass code generation. Use when the user wants implementation generated directly from `project_map.json`, `docs/20_facts/Codebase_Map.md`, the roadmap, and the original Claude skill contract.

## Triggers

- `$code-expert`
- `/code-expert`
- `code-expert`
- `implement`
- `WF8`

## Can Write

- `src/`
- `scripts/`
- `configs/`
- `project_map.json`
- `docs/20_facts/Codebase_Map.md`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`
- `.evidence/chains/`
- `.evidence/index.json`

## Final Outputs

- `implementation: src/`
- `implementation: scripts/`
- `implementation: configs/`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`
- `tool_trace: .evidence/chains/`
- `tool_trace: .evidence/index.json`

## Must Read

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

## Must Prove

- `read_project_map_before_stable_code`
- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `semantic_commit_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `compile_doc_or_NOT_RUN`
- `stable_code_change`
- `project_map_write`
- `codebase_map_write`
- `canonical_state_edit`
- `docs_site_render`
- `codebase_map_docchain`

## Cannot Do

- `stable_code_without_project_map_read`
- `project_map_stale`
- `training_without_semantic_commit`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:code-expert]]
- [[source:schemas/skill_contracts.json#code-expert]]
- [[term:Gate Evidence]]
