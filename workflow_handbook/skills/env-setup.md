---
schema_version: "0.1"
page_id: "env-setup"
title: "env-setup"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/env-setup.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for env-setup. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 150
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "env-setup"
  - path: ".agents/skills/env-setup/SKILL.md"
    role: "skill_source"
references: ["skill:env-setup", "source:schemas/skill_contracts.json#env-setup", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/env-setup.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# env-setup

## Purpose

Internal Harness instruction source for env-setup. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$env-setup`
- `/env-setup`
- `env-setup`
- `environment refresh`
- `deps changed`
- `dependency refresh`

## Can Write

- `CLAUDE.md`
- `requirements.txt`
- `requirements-dev.txt`
- `environment.yml`
- `environment.yaml`
- `pyproject.toml`
- `scripts/`
- `configs/`

## Final Outputs

- `guidance: CLAUDE.md`
- `operational_scope: requirements.txt`
- `operational_scope: requirements-dev.txt`
- `operational_scope: environment.yml`
- `operational_scope: environment.yaml`
- `operational_scope: pyproject.toml`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/deps-update-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/env-setup/SKILL.md`
- `.agents/skills/env-setup/references/environment-refresh.md`
- `.agents/skills/init-project/references/claude-maintenance.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `requirements.txt`
- `requirements-dev.txt`
- `environment.yml`
- `environment.yaml`
- `pyproject.toml`

## Must Prove

- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `gate_ledger`
- `dependency_file_change`
- `environment_section_write`
- `setup_command_run`

## Constraints

- `training_without_semantic_commit [advisory/notice; exception=not_required]`
- `direct_edit_auto_iterate [hard_invariant/block; exception=never]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:env-setup]]
- [[source:schemas/skill_contracts.json#env-setup]]
- [[term:Gate Evidence]]
