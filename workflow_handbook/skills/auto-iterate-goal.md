---
schema_version: "0.1"
page_id: "auto-iterate-goal"
title: "auto-iterate-goal"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-iterate-goal.md"
source_of_truth: true
status: "generated"
summary: "Generate or validate the auto-iterate goal file before launching WF10 auto-iterate"
nav:
  section: "skills"
  position: 230
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-iterate-goal"
  - path: ".agents/skills/auto-iterate-goal/SKILL.md"
    role: "skill_source"
references: ["skill:auto-iterate-goal", "source:schemas/skill_contracts.json#auto-iterate-goal", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-iterate-goal.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-iterate-goal

## Purpose

Generate or validate the auto-iterate goal file before launching WF10 auto-iterate

## Triggers

- `$auto-iterate-goal`
- `/auto-iterate-goal`
- `auto iterate goal`
- `auto-iterate goal`
- `WF10 auto`

## Can Write

- `docs/auto_iterate_goal.md`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/auto_iterate_goal.md`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/auto-iterate-goal/SKILL.md`
- `.agents/skills/evaluate/references/stage-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/auto_iterate_goal.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/Validate_Run_Report.md`

## Must Prove

- `goal_validate_or_init`
- `context_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF10_auto_readiness`
- `goal_write`
- `docs_site_render`

## Cannot Do

- `start_auto_iterate_without_goal_validation`
- `manual_edit_auto_iterate`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:auto-iterate-goal]]
- [[source:schemas/skill_contracts.json#auto-iterate-goal]]
- [[term:Gate Evidence]]
