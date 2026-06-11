---
schema_version: "0.1"
page_id: "build-plan"
title: "build-plan"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/build-plan.md"
source_of_truth: true
status: "generated"
summary: "Codex wrapper for WF7 implementation planning. Use after WF6 architecture design when the user wants `docs/Implementation_Roadmap.md`, `project_map.json`, and `docs/20_facts/Codebase_Map.md` built from the technical spec, baseline evidence, templates, and schemas."
nav:
  section: "skills"
  position: 160
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "build-plan"
  - path: ".agents/skills/build-plan/SKILL.md"
    role: "skill_source"
references: ["skill:build-plan", "source:schemas/skill_contracts.json#build-plan", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/build-plan.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# build-plan

## Purpose

Codex wrapper for WF7 implementation planning. Use after WF6 architecture design when the user wants `docs/Implementation_Roadmap.md`, `project_map.json`, and `docs/20_facts/Codebase_Map.md` built from the technical spec, baseline evidence, templates, and schemas.

## Triggers

- `$build-plan`
- `/build-plan`
- `build plan`
- `implementation roadmap`
- `WF7`

## Can Write

- `project_map.json`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Implementation_Roadmap.md`

## Final Outputs

- `current_doc: docs/Implementation_Roadmap.md`
- `fact_doc: docs/20_facts/Project_Glossary.md`
- `fact_doc: docs/20_facts/Codebase_Map.md`

## Tool-Owned Outputs

- none

## Must Read

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

## Must Prove

- `write_implementation_roadmap`
- `update_project_map`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `project_map_write`
- `project_glossary_write`
- `codebase_map_write`
- `canonical_state_edit`
- `docs_site_boundary_report`

## Cannot Do

- `architecture_decision_in_build_plan`
- `project_map_stale`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:build-plan]]
- [[source:schemas/skill_contracts.json#build-plan]]
- [[term:Gate Evidence]]
