---
schema_version: "0.1"
page_id: "deep-check"
title: "deep-check"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/deep-check.md"
source_of_truth: true
status: "generated"
summary: "Codex design-review gate for WF6 architecture decisions. Use when the user wants a skeptical Go/No-Go review of the technical spec before implementation planning or heavy implementation starts."
nav:
  section: "skills"
  position: 120
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "deep-check"
  - path: ".agents/skills/deep-check/SKILL.md"
    role: "skill_source"
references: ["skill:deep-check", "source:schemas/skill_contracts.json#deep-check", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/deep-check.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# deep-check

## Purpose

Codex design-review gate for WF6 architecture decisions. Use when the user wants a skeptical Go/No-Go review of the technical spec before implementation planning or heavy implementation starts.

## Triggers

- `$deep-check`
- `/deep-check`
- `deep-check`
- `deep check`
- `sanity check`
- `design review`

## Can Write

- `docs/Sanity_Check_Log.md`
- `docs/35_protocol/`
- `docs/10_contract/`

## Final Outputs

- `current_doc: docs/Sanity_Check_Log.md`
- `current_doc: docs/35_protocol/`
- `approved_contract: docs/10_contract/`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/references/language-policy.md`
- `.agents/skills/deep-check/SKILL.md`
- `.agents/skills/deep-check/references/sanity-check.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/Technical_Spec.md`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`
- `docs/35_protocol/Research_Protocol.md`

## Must Prove

- `codex_review_or_NOT_RUN`
- `external_model_review_or_NOT_RUN`
- `check_protocol_drift_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `sanity_check_write`
- `review_trace_write`
- `contract_conflict`
- `docs_site_boundary_report`

## Cannot Do

- `protocol_as_approved_contract`
- `approve_without_explicit_human_approval`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:deep-check]]
- [[source:schemas/skill_contracts.json#deep-check]]
- [[term:Gate Evidence]]
