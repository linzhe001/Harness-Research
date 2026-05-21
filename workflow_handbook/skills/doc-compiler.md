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
summary: "Compile current project documents from explicit evidence chains. Use when refreshing contract, fact, protocol, or release docs that need auditable evidence."
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

Compile current project documents from explicit evidence chains. Use when refreshing contract, fact, protocol, or release docs that need auditable evidence.

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
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `approved_contract: docs/10_contract/`
- `fact_doc: docs/20_facts/`
- `current_doc: docs/35_protocol/`

## Tool-Owned Outputs

- `tool_trace: .evidence/chains/`
- `tool_trace: .evidence/index.json`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

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
- `docs_site_render_or_NOT_RUN`
- `current_doc_write`
- `contract_doc_write`
- `protocol_doc_write`
- `docs_site_render`

## Cannot Do

- `manual_edit_evidence_chain`
- `current_doc_without_docchain`

## Exit Condition

Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:doc-compiler]]
- [[source:schemas/skill_contracts.json#doc-compiler]]
- [[term:Gate Evidence]]
