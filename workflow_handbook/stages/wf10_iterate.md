---
schema_version: "0.1"
page_id: "wf10_iterate"
title: "WF10 Iterate"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf10_iterate.md"
source_of_truth: true
status: "generated"
summary: "Run the Ralph-style loop: plan, code, run, evaluate, and decide the next round."
nav:
  section: "stages"
  position: 100
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "iterate"
  - path: ".agents/skills/iterate/SKILL.md"
    role: "skill_source"
references: ["stage:WF10", "skill:iterate", "source:schemas/skill_contracts.json#iterate", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf10_iterate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF10 Iterate

## Purpose

Run the Ralph-style loop: plan, code, run, evaluate, and decide the next round.

## How To Run

`$iterate plan`, `$iterate run`, and `$iterate eval`.

## Completion Effect

`iteration_log.json` and `docs/40_iterations/**` capture runs, lessons, and decisions.

## Contract Detail

Codex wrapper for WF10 structured iteration. Use when the user wants to run `plan`, `code`, `run`, `eval`, `ablate`, `status`, or `log` while preserving the original iteration schema and workflow logic.

## Inputs

- `$iterate`
- `/iterate`
- `iterate`
- `NEXT_ROUND`
- `DEBUG`
- `CONTINUE`
- `PIVOT`
- `ABORT`
- `WF10`

## Outputs

- `current_doc: docs/40_iterations/`
- `current_doc: docs/50_memory/`
- `canonical_state: iteration_log.json`
- `canonical_state: MEMORY.md`
- `legacy_compat: docs/iterations/ -> docs/40_iterations/`

## Required Reads

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

## Gates

- `iteration_log_update`
- `decision_vocabulary`
- `lesson_quality_check_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `iteration_log_write`
- `iteration_report_write`
- `lesson_promotion`
- `WF11_handoff`
- `docs_site_boundary_report`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:iterate]]

## Related References

- [[stage:WF10]]
- [[skill:iterate]]
- [[source:schemas/skill_contracts.json#iterate]]
- [[term:Gate Evidence]]
