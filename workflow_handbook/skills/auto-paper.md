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
summary: "Use this Skill as the auto-paper orchestrator, not a direct polishing tool. It routes phases, checks artifacts, and keeps paper-writing state separate from auto-iterate experiment state."
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

Use this Skill as the auto-paper orchestrator, not a direct polishing tool. It routes phases, checks artifacts, and keeps paper-writing state separate from auto-iterate experiment state.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

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
