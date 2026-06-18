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
summary: "Internal Harness instruction source for auto-paper. Route through visible Harness aliases or hook contracts instead of invoking directly."
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

Internal Harness instruction source for auto-paper. Route through visible Harness aliases or hook contracts instead of invoking directly.

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

- `tool_trace: .auto_paper/`

## Must Read

- `.agents/references/language-policy.md`
- `.agents/references/documentation-style.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/research-supervision-patterns.md`
- `.agents/references/research-supervision/README.md`
- `.agents/references/research-supervision/phd-research-primer.md`
- `.agents/references/research-supervision/paper-and-figure-system.md`
- `.agents/references/research-supervision/paper-writing-layouts.md`
- `.agents/references/research-supervision/benchmark-evaluation-paper.md`
- `.agents/references/research-supervision/scientific-plotting.md`
- `.agents/references/research-supervision/pre-submission-review.md`
- `.agents/references/research-supervision/case-patterns.md`
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
- `iteration_log.json`
- `docs/context/contracts.md`
- `docs/context/experiments.md`
- `docs/30_evidence/Experiment_Evidence_Index.json`
- `docs/30_evidence/Experiment_Evidence_Index.md`
- `tooling/auto_paper/`
- `docs/10_contract/Claim_Boundary.md`
- `docs/45_discoveries/Discovery_Ledger.md`
- `docs/45_discoveries/Research_Wiki.md`

## Must Prove

- `smoke_test_or_NOT_RUN`
- `claim_delta_evidence_or_NOT_CHANGED`
- `experiments_context_update_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `auto_paper_gate`
- `latex_patch`
- `run_request_register_write`
- `claim_delta_evidence`
- `human_gate`
- `docs_site_boundary_report`

## Constraints

- `direct_edit_auto_iterate [hard_invariant/block; exception=never]`
- `manual_edit_auto_iterate [hard_invariant/block; exception=never]`
- `direct_edit_evidence [hard_invariant/block; exception=never]`
- `manual_edit_evidence_chain [hard_invariant/block; exception=never]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:auto-paper]]
- [[source:schemas/skill_contracts.json#auto-paper]]
- [[term:Gate Evidence]]
