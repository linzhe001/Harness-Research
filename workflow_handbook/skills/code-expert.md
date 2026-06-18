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
summary: "Internal Harness instruction source for code-expert. Route through visible Harness aliases or hook contracts instead of invoking directly."
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

Internal Harness instruction source for code-expert. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

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
- `.agents/references/contract-gating-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/language-policy.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/pre-training-rule.md`
- `.agents/references/sliced-commit-rule.md`
- `.agents/references/commit-checkpoint-rule.md`
- `.agents/references/research-supervision-patterns.md`
- `.agents/references/research-supervision/experiment-and-build-canvas.md`
- `.agents/references/research-supervision/ai-assisted-research-workflow.md`
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
- `docs_site_boundary_report`
- `compile_doc_or_NOT_RUN`
- `roadmap_implementation_completeness_gate`
- `stable_code_change`
- `project_map_write`
- `codebase_map_write`
- `canonical_state_edit`
- `codebase_map_docchain`
- `docs_site_boundary_report`
- `roadmap_implementation_completeness`

## Constraints

- `stable_code_without_project_map_read [ownership_boundary/notice; exception=owner_delegation_required]`
- `project_map_stale [ownership_boundary/notice; exception=owner_delegation_required]`
- `training_without_semantic_commit [advisory/notice; exception=not_required]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:code-expert]]
- [[source:schemas/skill_contracts.json#code-expert]]
- [[term:Gate Evidence]]
