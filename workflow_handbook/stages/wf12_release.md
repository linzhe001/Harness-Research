---
schema_version: "0.1"
page_id: "wf12_release"
title: "WF12 Release"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf12_release.md"
source_of_truth: true
status: "generated"
summary: "Prepare release artifacts while keeping claims inside the approved boundary."
nav:
  section: "stages"
  position: 120
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "release"
  - path: ".agents/skills/release/SKILL.md"
    role: "skill_source"
references: ["stage:WF12", "skill:release", "source:schemas/skill_contracts.json#release", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf12_release.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF12 Release

## Purpose

Prepare release artifacts while keeping claims inside the approved boundary.

## How To Run

`$release` after WF11 and release readiness gates are satisfied.

## Completion Effect

`submission/**`, release docs, and final Gate Evidence are ready for explicit submit approval.

## Contract Detail

Codex wrapper for WF12 release and submission packaging. Use when the user wants validation, packaging, or submission preparation according to the original workflow.

## Inputs

- `$release`
- `/release`
- `release`
- `submit`
- `package`
- `WF12`

## Outputs

- `release_package: submission/`
- `current_doc: docs/60_release/`
- `canonical_state: PROJECT_STATE.json`
- `operational_scope: docs/`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Required Reads

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/release/SKILL.md`
- `.agents/skills/release/references/release-checklist.md`
- `.agents/skills/release/references/release-manifest.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `CLAUDE.md`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

## Gates

- `check_dynamic_context_wf12_or_NOT_RUN`
- `release_manifest_validation`
- `claim_boundary_check`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF12_readiness`
- `release_claim`
- `submission_package_write`
- `docs_site_render`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:release]]

## Related References

- [[stage:WF12]]
- [[skill:release]]
- [[source:schemas/skill_contracts.json#release]]
- [[term:Gate Evidence]]
