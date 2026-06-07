---
schema_version: "0.1"
page_id: "wf0_init"
title: "WF0 Init"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf0_init.md"
source_of_truth: true
status: "generated"
summary: "Initialize or refresh the workspace guidance and workflow state."
nav:
  section: "stages"
  position: 0
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "init-project"
  - path: ".agents/skills/init-project/SKILL.md"
    role: "skill_source"
references: ["stage:WF0", "skill:init-project", "source:schemas/skill_contracts.json#init-project", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf0_init.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF0 Init

## Purpose

Initialize or refresh the workspace guidance and workflow state.

## How To Run

`$init-project` for guidance setup, or `$orchestrator` for state checks.

## Completion Effect

`AGENTS.md`, `CLAUDE.md`, `PROJECT_STATE.json`, and optional scaffold are ready.

## Contract Detail

WF0/bootstrap wrapper for staged `CLAUDE.md` generation and updates. Use when the user wants the compact project snapshot initialized or refreshed while preserving the original staged template behavior.

## Inputs

- `$init`
- `$init-project`
- `/init`
- `/init-project`
- `init-project`
- `update-from-grill`
- `$init-project update-from-grill`
- `/init-project update-from-grill`
- `grill_draft_ready`
- `init project`
- `WF0`
- `bootstrap init`
- `operator context init`
- `update CLAUDE`
- `CLAUDE update`

## Outputs

- `guidance: CLAUDE.md`
- `guidance: AGENTS.md`
- `guidance: README.md`
- `guidance: OPERATOR_CONTEXT.md`
- `canonical_state: PROJECT_STATE.json`
- `operational_scope: docs/`
- `tool_trace: .evidence/`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Required Reads

- `.agents/references/context-layering-policy.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/init-project/SKILL.md`
- `.agents/skills/init-project/references/claude-md-template.md`
- `.agents/skills/init-project/references/claude-maintenance.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `CLAUDE.md`
- `README.md`
- `OPERATOR_CONTEXT.md`
- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `.workflow_supervisor/readiness.json`
- `docs/Feasibility_Report.md`
- `docs/Dataset_Stats.md`
- `docs/Baseline_Report.md`
- `project_map.json`

## Gates

- `grill_handoff_read_or_NOT_RUN`
- `context_gate_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `dynamic_context_init`
- `CLAUDE_write`
- `AGENTS_write`
- `README_write`
- `grill_handoff_guidance_write`
- `operator_context_write`
- `canonical_state_edit`
- `docs_site_render`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:init-project]]

## Related References

- [[stage:WF0]]
- [[skill:init-project]]
- [[source:schemas/skill_contracts.json#init-project]]
- [[term:Gate Evidence]]
