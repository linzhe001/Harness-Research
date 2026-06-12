---
schema_version: "0.1"
page_id: "doc-compiler"
title: "doc-compiler"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/doc-compiler.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for doc-compiler. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 10
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "doc-compiler"
  - path: ".agents/skills/doc-compiler/SKILL.md"
    role: "skill_source"
references: ["skill:doc-compiler", "source:schemas/skill_contracts.json#doc-compiler", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/doc-compiler.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# doc-compiler

## Purpose

Internal Harness instruction source for doc-compiler. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$doc-compiler`
- `/doc-compiler`
- `doc-compiler`
- `compile doc`
- `docchain`

## Can Write

- `docs/10_contract/`
- `docs/20_facts/`
- `docs/35_protocol/`
- `.evidence/chains/`
- `.evidence/index.json`

## Final Outputs

- `approved_contract: docs/10_contract/`
- `fact_doc: docs/20_facts/`
- `current_doc: docs/35_protocol/`

## Tool-Owned Outputs

- `tool_trace: .evidence/chains/`
- `tool_trace: .evidence/index.json`

## Must Read

- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/doc-compiler/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/10_contract/Project_Contract.md`
- `docs/20_facts/Project_Facts.md`
- `docs/35_protocol/Research_Protocol.md`

## Must Prove

- `compile_doc_or_NOT_RUN`
- `check_docchain_gates_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `current_doc_write`
- `contract_doc_write`
- `protocol_doc_write`
- `docs_site_boundary_report`

## Cannot Do

- `manual_edit_evidence_chain`
- `current_doc_without_docchain`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:doc-compiler]]
- [[source:schemas/skill_contracts.json#doc-compiler]]
- [[term:Gate Evidence]]
