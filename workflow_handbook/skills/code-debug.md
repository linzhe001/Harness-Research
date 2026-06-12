---
schema_version: "0.1"
page_id: "code-debug"
title: "code-debug"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/code-debug.md"
source_of_truth: true
status: "generated"
summary: "Read these first:"
nav:
  section: "skills"
  position: 180
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "code-debug"
  - path: ".agents/skills/code-debug/SKILL.md"
    role: "skill_source"
references: ["skill:code-debug", "source:schemas/skill_contracts.json#code-debug", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/code-debug.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# code-debug

## Purpose

Read these first:

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$code-debug`
- `/code-debug`
- `code-debug`
- `debug`
- `fix`

## Can Write

- `src/`
- `scripts/`
- `configs/`
- `project_map.json`
- `docs/20_facts/Codebase_Map.md`
- `.evidence/chains/`
- `.evidence/index.json`

## Final Outputs

- `implementation: src/`
- `implementation: scripts/`
- `implementation: configs/`

## Tool-Owned Outputs

- `tool_trace: .evidence/chains/`
- `tool_trace: .evidence/index.json`

## Must Read

- `.agents/references/code-style.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/language-policy.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/pre-training-rule.md`
- `.agents/references/sliced-commit-rule.md`
- `.agents/skills/code-debug/SKILL.md`
- `.agents/skills/code-debug/references/debug-modes.md`
- `AGENTS.md`
- `project_map.json`
- `CLAUDE.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Validate_Run_Report.md`
- `iteration_log.json`

## Must Prove

- `read_project_map_before_stable_code`
- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `semantic_commit_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `compile_doc_or_NOT_RUN`
- `stable_code_change`
- `project_map_write`
- `codebase_map_write`
- `codebase_map_docchain`
- `docs_site_boundary_report`

## Cannot Do

- `stable_code_without_project_map_read`
- `project_map_stale`
- `training_without_semantic_commit`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:code-debug]]
- [[source:schemas/skill_contracts.json#code-debug]]
- [[term:Gate Evidence]]
