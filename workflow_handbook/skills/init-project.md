---
schema_version: "0.1"
page_id: "init-project"
title: "init-project"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/init-project.md"
source_of_truth: true
status: "generated"
summary: "WF0/bootstrap wrapper for staged `CLAUDE.md` generation and updates. Use when the user wants the compact project snapshot initialized or refreshed while preserving the original staged template behavior."
nav:
  section: "skills"
  position: 140
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "init-project"
  - path: ".agents/skills/init-project/SKILL.md"
    role: "skill_source"
references: ["skill:init-project", "source:schemas/skill_contracts.json#init-project", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/init-project.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# init-project

## Purpose

WF0/bootstrap wrapper for staged `CLAUDE.md` generation and updates. Use when the user wants the compact project snapshot initialized or refreshed while preserving the original staged template behavior.

## Triggers

- `$init`
- `$init-project`
- `/init`
- `/init-project`
- `init-project`
- `init project`
- `WF0`
- `bootstrap init`
- `operator context init`
- `update CLAUDE`
- `CLAUDE update`

## Can Write

- `CLAUDE.md`
- `AGENTS.md`
- `OPERATOR_CONTEXT.md`
- `PROJECT_STATE.json`
- `docs/`
- `.evidence/`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `guidance: CLAUDE.md`
- `guidance: AGENTS.md`
- `guidance: OPERATOR_CONTEXT.md`

## Tool-Owned Outputs

- `tool_trace: .evidence/`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

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
- `OPERATOR_CONTEXT.md`
- `docs/Feasibility_Report.md`
- `docs/Dataset_Stats.md`
- `docs/Baseline_Report.md`
- `project_map.json`

## Must Prove

- `context_gate_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `dynamic_context_init`
- `CLAUDE_write`
- `operator_context_write`
- `canonical_state_edit`
- `docs_site_render`

## Cannot Do

- `direct_edit_evidence`
- `direct_edit_auto_iterate`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:init-project]]
- [[source:schemas/skill_contracts.json#init-project]]
- [[term:Gate Evidence]]
