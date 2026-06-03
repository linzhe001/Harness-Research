---
schema_version: "0.1"
page_id: "evaluate"
title: "evaluate"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/evaluate.md"
source_of_truth: true
status: "generated"
summary: "Codex wrapper for experiment analysis and decision-making. Use when the user wants metrics interpreted, a stage or iteration report written, and a NEXT_ROUND, DEBUG, CONTINUE, PIVOT, or ABORT recommendation."
nav:
  section: "skills"
  position: 130
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "evaluate"
  - path: ".agents/skills/evaluate/SKILL.md"
    role: "skill_source"
references: ["skill:evaluate", "source:schemas/skill_contracts.json#evaluate", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/evaluate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# evaluate

## Purpose

Codex wrapper for experiment analysis and decision-making. Use when the user wants metrics interpreted, a stage or iteration report written, and a NEXT_ROUND, DEBUG, CONTINUE, PIVOT, or ABORT recommendation.

## Triggers

- `$evaluate`
- `/evaluate`
- `evaluate`
- `eval results`
- `iteration eval`

## Can Write

- `iteration_log.json`
- `docs/40_iterations/`
- `docs/iterations/`
- `docs/50_memory/`
- `MEMORY.md`
- `docs/Stage_Report.md`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/40_iterations/`
- `current_doc: docs/50_memory/`
- `current_doc: docs/Stage_Report.md`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/references/language-policy.md`
- `.agents/skills/evaluate/SKILL.md`
- `.agents/skills/evaluate/references/stage-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/50_memory/Lessons.md`
- `MEMORY.md`

## Must Prove

- `decision_vocabulary`
- `lesson_quality_check_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `stage_report_write`
- `iteration_report_write`
- `lesson_promotion`
- `iteration_log_write`
- `docs_site_render`

## Cannot Do

- `stage_transition_from_iterate`
- `auto_observation_direct_to_MEMORY`
- `protocol_as_approved_contract`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:evaluate]]
- [[source:schemas/skill_contracts.json#evaluate]]
- [[term:Gate Evidence]]
