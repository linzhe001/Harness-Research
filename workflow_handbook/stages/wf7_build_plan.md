---
schema_version: "0.1"
page_id: "wf7_build_plan"
title: "WF7 Build Plan"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf7_build_plan.md"
source_of_truth: true
status: "generated"
summary: "Convert the architecture into bounded implementation slices."
nav:
  section: "stages"
  position: 70
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "build-plan"
  - path: ".agents/skills/build-plan/SKILL.md"
    role: "skill_source"
references: ["stage:WF7", "skill:build-plan", "source:schemas/skill_contracts.json#build-plan", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf7_build_plan.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF7 Build Plan

## Purpose

Convert the architecture into bounded implementation slices.

## How To Run

`$build-plan` after the technical spec is stable enough to slice.

## Completion Effect

`docs/Implementation_Roadmap.md`, `project_map.json`, and codebase map guidance align.

## Contract Detail

Codex wrapper for WF7 implementation planning. Use after WF6 architecture design when the user wants `docs/Implementation_Roadmap.md`, `project_map.json`, and `docs/20_facts/Codebase_Map.md` built from the technical spec, baseline evidence, templates, and schemas.

## Inputs

- `$build-plan`
- `/build-plan`
- `build plan`
- `implementation roadmap`
- `WF7`

## Outputs

- `current_doc: docs/Implementation_Roadmap.md`
- `fact_doc: docs/20_facts/Project_Glossary.md`
- `fact_doc: docs/20_facts/Codebase_Map.md`
- `canonical_state: project_map.json`
- `canonical_state: PROJECT_STATE.json`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Required Reads

- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/sliced-commit-rule.md`
- `.agents/skills/build-plan/SKILL.md`
- `.agents/skills/build-plan/references/implementation-roadmap.md`
- `.agents/skills/build-plan/references/project-map-schema.json`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Technical_Spec.md`
- `docs/Baseline_Report.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`

## Gates

- `write_implementation_roadmap`
- `update_project_map`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `project_map_write`
- `project_glossary_write`
- `codebase_map_write`
- `canonical_state_edit`
- `docs_site_render`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:build-plan]]

## Related References

- [[stage:WF7]]
- [[skill:build-plan]]
- [[source:schemas/skill_contracts.json#build-plan]]
- [[term:Gate Evidence]]
