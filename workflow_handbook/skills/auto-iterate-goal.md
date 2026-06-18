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
summary: "Internal Harness instruction source for auto-iterate-goal. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 340
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

Internal Harness instruction source for auto-iterate-goal. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$auto-iterate-goal`
- `/auto-iterate-goal`
- `auto iterate goal`
- `auto-iterate goal`
- `WF10 auto`

## Can Write

- `docs/auto_iterate_goal.md`

## Final Outputs

- `current_doc: docs/auto_iterate_goal.md`

## Tool-Owned Outputs

- none

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
- `docs/context/contracts.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/Validate_Run_Report.md`

## Must Prove

- `goal_validate_or_init`
- `context_gate_or_NOT_RUN`
- `automation_policy_respected`
- `pre_train_commit_or_debug_scope`
- `pre_eval_commit_or_NOT_CHANGED`
- `claim_delta_evidence_or_NOT_CHANGED`
- `gate_ledger`
- `docs_site_boundary_report`
- `WF10_auto_readiness`
- `goal_write`
- `docs_site_boundary_report`

## Constraints

- `start_auto_iterate_without_goal_validation [workflow_default/notice; exception=overlay_allowed]`
- `manual_edit_auto_iterate [hard_invariant/block; exception=never]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:auto-iterate-goal]]
- [[source:schemas/skill_contracts.json#auto-iterate-goal]]
- [[term:Gate Evidence]]
