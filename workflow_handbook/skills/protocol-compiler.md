---
schema_version: "0.1"
page_id: "protocol-compiler"
title: "protocol-compiler"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/protocol-compiler.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for protocol-compiler. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 40
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "protocol-compiler"
  - path: ".agents/skills/protocol-compiler/SKILL.md"
    role: "skill_source"
references: ["skill:protocol-compiler", "source:schemas/skill_contracts.json#protocol-compiler", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/protocol-compiler.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# protocol-compiler

## Purpose

Internal Harness instruction source for protocol-compiler. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$protocol-compiler`
- `/protocol-compiler`
- `protocol compiler`
- `compile protocol`

## Can Write

- `.evidence/protocol_compiler/`
- `docs/context/protocol.md`

## Final Outputs

- `current_doc: docs/context/protocol.md`

## Tool-Owned Outputs

- `tool_trace: .evidence/protocol_compiler/`

## Must Read

- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/language-policy.md`
- `.agents/skills/protocol-compiler/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/context/evidence.md`
- `docs/context/protocol.md`
- `docs/30_evidence/Evidence_Index.md`
- `docs/30_evidence/Open_Questions.md`
- `docs/35_protocol/Research_Protocol.md`

## Must Prove

- `compile_protocol_or_NOT_RUN`
- `protocol_review_or_NOT_RUN`
- `docchain_gate_when_current_docs_change`
- `gate_ledger`
- `docs_site_boundary_report`
- `protocol_apply`
- `protocol_doc_write`
- `contract_readiness`
- `docs_site_boundary_report`

## Constraints

- `protocol_as_approved_contract [hard_invariant/block; exception=never]`
- `manual_edit_evidence_chain [hard_invariant/block; exception=never]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:protocol-compiler]]
- [[source:schemas/skill_contracts.json#protocol-compiler]]
- [[term:Gate Evidence]]
