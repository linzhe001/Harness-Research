---
schema_version: "0.1"
page_id: "harness-maintenance"
title: "harness-maintenance"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/harness-maintenance.md"
source_of_truth: true
status: "generated"
summary: "Read these first:"
nav:
  section: "skills"
  position: 190
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "harness-maintenance"
  - path: ".agents/skills/harness-maintenance/SKILL.md"
    role: "skill_source"
references: ["skill:harness-maintenance", "source:schemas/skill_contracts.json#harness-maintenance", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/harness-maintenance.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# harness-maintenance

## Purpose

Read these first:

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$harness-maintenance`
- `/harness-maintenance`
- `harness-maintenance`
- `harness maintenance`
- `hook maintenance`
- `hook detection`
- `hook trigger`
- `hook routing`
- `skill maintenance`
- `skill contract`
- `skill detection`
- `skill routing`
- `skill trigger`
- `ubiquitous language`
- `operator handbook`
- `stage card`
- `stage card generator`
- `prompt routing`
- `prompt trigger`
- `prompt detection`
- `prompt classification`
- `workflow vocabulary`
- `workflow terms`
- `workflow language`
- `permission policy`
- `permission boundary`
- `hook判断`
- `hook触发`
- `hook的判断`
- `hook的触发`
- `hook的路由`
- `hook 的判断`

## Can Write

- `.agents/skills/`
- `.agents/references/`
- `.claude/Workflow_Guide.md`
- `.claude/skills/`
- `.claude/rules/`
- `.claude/shared/`
- `tooling/codex_hooks/`
- `tooling/intent_router/`
- `tooling/evidence/`
- `tooling/model_api/`
- `tooling/.tests/`
- `templates/`
- `schemas/`
- `docs/`
- `workflow_handbook/`
- `.gitignore`
- `AGENTS.md`
- `AGENTS.md.template`
- `CLAUDE.md`
- `CLAUDE.md.template`
- `README.md`
- `AI_AGENT_SETUP.md`
- `tooling/workflow_supervisor/`
- `tooling/grill/`

## Final Outputs

- `current_doc: tooling/codex_hooks/README.md`
- `current_doc: tooling/codex_hooks/Lightweight_Hook_Policy_Guide.md`
- `current_doc: workflow_handbook/`
- `current_doc: README.md`
- `current_doc: AI_AGENT_SETUP.md`
- `guidance: AGENTS.md`
- `guidance: AGENTS.md.template`
- `guidance: CLAUDE.md`
- `guidance: CLAUDE.md.template`
- `guidance: .agents/skills/`
- `guidance: .agents/references/`
- `guidance: .claude/Workflow_Guide.md`
- `guidance: .claude/skills/`
- `guidance: .claude/rules/`
- `guidance: .claude/shared/`
- `guidance: templates/`
- `implementation: tooling/workflow_supervisor/`
- `implementation: tooling/grill/`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/code-style.md`
- `.agents/references/language-policy.md`
- `.agents/references/ubiquitous-language.md`
- `tooling/codex_hooks/README.md`
- `schemas/skill_contracts.json`
- `schemas/skill_contracts.schema.json`
- `tooling/.tests/test_codex_hooks_contracts.py`
- `.agents/skills/harness-maintenance/SKILL.md`
- `AGENTS.md`
- `CLAUDE.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/rules/harness_external_review.rules`
- `tooling/codex_hooks/Lightweight_Hook_Policy_Guide.md`

## Must Prove

- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `gate_ledger`
- `hook_runtime_change`
- `hook_contract_change`
- `skill_contract_change`
- `skill_routing_change`
- `permission_policy_change`

## Cannot Do

- `direct_edit_auto_iterate`
- `direct_edit_evidence`
- `manual_edit_auto_iterate`
- `manual_edit_evidence_chain`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:harness-maintenance]]
- [[source:schemas/skill_contracts.json#harness-maintenance]]
- [[term:Gate Evidence]]
