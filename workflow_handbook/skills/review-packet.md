---
schema_version: "0.1"
page_id: "review-packet"
title: "review-packet"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/review-packet.md"
source_of_truth: true
status: "generated"
summary: "Build concise human review packets for dynamic-context contracts, protocol readiness, and release gates."
nav:
  section: "skills"
  position: 30
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "review-packet"
  - path: ".agents/skills/review-packet/SKILL.md"
    role: "skill_source"
references: ["skill:review-packet", "source:schemas/skill_contracts.json#review-packet", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/review-packet.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# review-packet

## Purpose

Build concise human review packets for dynamic-context contracts, protocol readiness, and release gates.

## Triggers

- `$review-packet`
- `/review-packet`
- `review packet`
- `approve contract`
- `human approval`

## Can Write

- `.evidence/review_packets/`
- `docs/10_contract/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `approved_contract: docs/10_contract/`

## Tool-Owned Outputs

- `tool_trace: .evidence/review_packets/`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/language-policy.md`
- `.agents/skills/review-packet/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

## Must Prove

- `check_dynamic_context_or_NOT_RUN`
- `build_review_packet_or_NOT_RUN`
- `approval_tool_only_after_explicit_human_approval`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `contract_approval`
- `review_packet_build`
- `WF10_readiness`
- `WF11_readiness`
- `WF12_readiness`
- `docs_site_render`

## Cannot Do

- `approve_without_explicit_human_approval`
- `packet_as_approval`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:review-packet]]
- [[source:schemas/skill_contracts.json#review-packet]]
- [[term:Gate Evidence]]
