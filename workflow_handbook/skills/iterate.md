---
schema_version: "0.1"
page_id: "iterate"
title: "iterate"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/iterate.md"
source_of_truth: true
status: "generated"
summary: "Codex wrapper for WF10 structured iteration. Use when the user wants to run `plan`, `code`, `run`, `eval`, `ablate`, `status`, or `log` while preserving the original iteration schema and workflow logic."
nav:
  section: "skills"
  position: 220
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "iterate"
  - path: ".agents/skills/iterate/SKILL.md"
    role: "skill_source"
references: ["skill:iterate", "source:schemas/skill_contracts.json#iterate", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/iterate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# iterate

## Purpose

Codex wrapper for WF10 structured iteration. Use when the user wants to run `plan`, `code`, `run`, `eval`, `ablate`, `status`, or `log` while preserving the original iteration schema and workflow logic.

## Triggers

- `$iterate`
- `/iterate`
- `iterate`
- `NEXT_ROUND`
- `DEBUG`
- `CONTINUE`
- `PIVOT`
- `ABORT`
- `WF10`

## Can Write

- `iteration_log.json`
- `docs/40_iterations/`
- `docs/iterations/`
- `docs/50_memory/`
- `MEMORY.md`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/40_iterations/`
- `current_doc: docs/50_memory/`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/skills/iterate/SKILL.md`
- `.agents/skills/iterate/references/iteration-log-schema.json`
- `.agents/skills/iterate/references/iteration-context.md`
- `.agents/skills/iterate/references/iteration-constraints.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/50_memory/Lessons.md`
- `MEMORY.md`

## Must Prove

- `iteration_log_update`
- `decision_vocabulary`
- `lesson_quality_check_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `iteration_log_write`
- `iteration_report_write`
- `lesson_promotion`
- `WF11_handoff`
- `docs_site_render`

## Cannot Do

- `auto_observation_direct_to_MEMORY`
- `manual_edit_auto_iterate`
- `stage_transition_from_iterate`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:iterate]]
- [[source:schemas/skill_contracts.json#iterate]]
- [[term:Gate Evidence]]
