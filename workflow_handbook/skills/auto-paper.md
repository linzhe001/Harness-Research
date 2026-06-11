---
schema_version: "0.1"
page_id: "auto-paper"
title: "auto-paper"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/auto-paper.md"
source_of_truth: true
status: "generated"
summary: "Orchestrate artifact-first academic paper writing for LaTeX manuscripts. Use when Codex is asked to run an auto-paper loop, rewrite or restructure a paper section, produce citation-supported manuscript edits, harden a submission, audit reviewer risk, or coordinate research to argument to citation to layout to patch to harden writing phases."
nav:
  section: "skills"
  position: 230
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "auto-paper"
  - path: ".agents/skills/auto-paper/SKILL.md"
    role: "skill_source"
references: ["skill:auto-paper", "source:schemas/skill_contracts.json#auto-paper", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/auto-paper.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# auto-paper

## Purpose

Orchestrate artifact-first academic paper writing for LaTeX manuscripts. Use when Codex is asked to run an auto-paper loop, rewrite or restructure a paper section, produce citation-supported manuscript edits, harden a submission, audit reviewer risk, or coordinate research to argument to citation to layout to patch to harden writing phases.

## Triggers

- `$auto-paper`
- `/auto-paper`
- `auto-paper`
- `auto paper`
- `paper writing workflow`
- `citation-supported rewrite`
- `submission hardening`
- `LaTeX paper rewrite`

## Can Write

- `auto_paper_log.json`
- `auto_paper_output/`
- `docs/auto_paper_goal.md`

## Final Outputs

- `current_doc: docs/auto_paper_goal.md`
- `current_doc: auto_paper_output/`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/language-policy.md`
- `.agents/references/documentation-style.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/skills/auto-paper/SKILL.md`
- `.agents/skills/auto-paper/references/auto-paper-loop.md`
- `.agents/skills/auto-paper/references/auto-iterate-boundary.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/writing-rationale-matrix.md`
- `.agents/skills/auto-paper/references/motivation-thread.md`
- `.agents/skills/auto-paper/references/citation-support-bank.md`
- `.agents/skills/auto-paper/references/latex-source-control.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `auto_paper_log.json`
- `docs/auto_paper_goal.md`
- `auto_paper_output/`
- `docs/10_contract/Claim_Boundary.md`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `auto_paper_gate`
- `latex_patch`
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

- [[skill:auto-paper]]
- [[source:schemas/skill_contracts.json#auto-paper]]
- [[term:Gate Evidence]]
