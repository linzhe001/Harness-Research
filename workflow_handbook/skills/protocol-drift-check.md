---
schema_version: "0.1"
page_id: "protocol-drift-check"
title: "protocol-drift-check"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/protocol-drift-check.md"
source_of_truth: true
status: "generated"
summary: "Check whether dynamic research protocol drafts are stale before baseline, iteration, final experiment, or release gates."
nav:
  section: "skills"
  position: 50
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "protocol-drift-check"
  - path: ".agents/skills/protocol-drift-check/SKILL.md"
    role: "skill_source"
references: ["skill:protocol-drift-check", "source:schemas/skill_contracts.json#protocol-drift-check", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/protocol-drift-check.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# protocol-drift-check

## Purpose

Check whether dynamic research protocol drafts are stale before baseline, iteration, final experiment, or release gates.

## Triggers

- `$protocol-drift-check`
- `/protocol-drift-check`
- `protocol drift`
- `drift check`

## Can Write

- `docs/35_protocol/`
- `docs/10_contract/`
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/35_protocol/`
- `approved_contract: docs/10_contract/`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Must Read

- `.agents/references/evidence-chain-rule.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/language-policy.md`
- `.agents/skills/protocol-drift-check/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/30_evidence/Open_Questions.md`
- `docs/35_protocol/Research_Protocol.md`
- `docs/35_protocol/Protocol_Changelog.md`

## Must Prove

- `check_protocol_drift_or_NOT_RUN`
- `docchain_gate_when_current_docs_change`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `protocol_readiness`
- `WF10_readiness`
- `WF11_readiness`
- `WF12_readiness`
- `docs_site_render`

## Cannot Do

- `ignore_unresolved_protocol_drift`
- `protocol_as_approved_contract`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:protocol-drift-check]]
- [[source:schemas/skill_contracts.json#protocol-drift-check]]
- [[term:Gate Evidence]]
