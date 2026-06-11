---
schema_version: "0.1"
page_id: "auto-paper-harden"
title: "auto-paper-harden"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-paper-harden.md"
source_of_truth: true
status: "generated"
summary: "Run the auto-paper harden phase. Use for final manuscript audit, artifact completeness, claim support, logic transfer, revision quality, LaTeX guard, compile report, and reviewer-risk gate routing."
nav:
  section: "skills"
  position: 300
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-paper-harden"
  - path: ".agents/skills/auto-paper-harden/SKILL.md"
    role: "skill_source"
references: ["skill:auto-paper-harden", "source:schemas/skill_contracts.json#auto-paper-harden", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-paper-harden.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-paper-harden

## Purpose

Run the auto-paper harden phase. Use for final manuscript audit, artifact completeness, claim support, logic transfer, revision quality, LaTeX guard, compile report, and reviewer-risk gate routing.

## Triggers

- `$auto-paper-harden`
- `/auto-paper-harden`
- `auto-paper harden`
- `auto paper harden`
- `submission hardening`
- `final gate ledger`

## Can Write

- `auto_paper_output/`

## Final Outputs

- `current_doc: auto_paper_output/`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/language-policy.md`
- `.agents/references/documentation-style.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/skills/auto-paper-harden/SKILL.md`
- `.agents/skills/auto-paper/SKILL.md`
- `.agents/skills/auto-paper/references/auto-paper-loop.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/citation-support-bank.md`
- `.agents/skills/auto-paper/references/latex-source-control.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `auto_paper_output/`
- `docs/10_contract/Claim_Boundary.md`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `auto_paper_harden`
- `human_gate`
- `docs_site_boundary_report`

## Cannot Do

- `direct_edit_auto_iterate`
- `manual_edit_auto_iterate`
- `direct_edit_evidence`
- `manual_edit_evidence_chain`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:auto-paper-harden]]
- [[source:schemas/skill_contracts.json#auto-paper-harden]]
- [[term:Gate Evidence]]
