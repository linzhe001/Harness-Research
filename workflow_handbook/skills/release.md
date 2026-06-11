---
schema_version: "0.1"
page_id: "release"
title: "release"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/release.md"
source_of_truth: true
status: "generated"
summary: "Codex wrapper for WF12 release and submission packaging. Use when the user wants validation, packaging, or submission preparation according to the original workflow."
nav:
  section: "skills"
  position: 360
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "release"
  - path: ".agents/skills/release/SKILL.md"
    role: "skill_source"
references: ["skill:release", "source:schemas/skill_contracts.json#release", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/release.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# release

## Purpose

Codex wrapper for WF12 release and submission packaging. Use when the user wants validation, packaging, or submission preparation according to the original workflow.

## Triggers

- `$release`
- `/release`
- `release`
- `submit`
- `package`
- `WF12`

## Can Write

- `submission/`
- `docs/`
- `PROJECT_STATE.json`

## Final Outputs

- `release_package: submission/`
- `current_doc: docs/60_release/`

## Tool-Owned Outputs

- none

## Must Read

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

## Must Prove

- `check_dynamic_context_wf12_or_NOT_RUN`
- `release_manifest_validation`
- `claim_boundary_check`
- `gate_ledger`
- `docs_site_boundary_report`
- `WF12_readiness`
- `release_claim`
- `submission_package_write`
- `docs_site_boundary_report`

## Cannot Do

- `release_claim_outside_claim_boundary`
- `submit_without_explicit_user_request`
- `overwrite_package_without_confirmation`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:release]]
- [[source:schemas/skill_contracts.json#release]]
- [[term:Gate Evidence]]
