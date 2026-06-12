---
schema_version: "0.1"
page_id: "code-review"
title: "code-review"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/code-review.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for code-review. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 200
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "code-review"
  - path: ".agents/skills/code-review/SKILL.md"
    role: "skill_source"
references: ["skill:code-review", "source:schemas/skill_contracts.json#code-review", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/code-review.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# code-review

## Purpose

Internal Harness instruction source for code-review. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$code-review`
- `/code-review`
- `code-review`
- `code review`
- `review code`
- `codex review`
- `deepseek review`
- `external model review`
- `cross review`
- `代码审查`
- `代码 review`
- `代码检查`
- `交叉验证`

## Can Write

- `.agents/state/review_traces/code-review/`

## Final Outputs

- `review_trace: .agents/state/review_traces/code-review/`

## Tool-Owned Outputs

- none

## Must Read

- `.agents/references/code-style.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/language-policy.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/review-tracing.md`
- `.agents/references/reviewer-independence.md`
- `.agents/skills/code-review/SKILL.md`
- `.agents/skills/code-review/references/review-report.md`
- `AGENTS.md`
- `CLAUDE.md`
- `project_map.json`
- `docs/Implementation_Roadmap.md`
- `docs/Validate_Run_Report.md`
- `iteration_log.json`
- `.agents/state/current_iteration.json`

## Must Prove

- `collect_review_scope`
- `git_metadata_snapshot`
- `changed_line_map`
- `codex_review_or_NOT_RUN`
- `external_model_review_or_NOT_RUN`
- `reconcile_review_findings`
- `write_review_report_or_NOT_RUN`
- `gate_ledger`
- `post_code_change_review`
- `code_review_report_write`
- `docs_or_evidence_chain_review`
- `heavy_review`

## Cannot Do

- `modify_subject_files_during_code_review`
- `review_without_line_references`
- `unverified_model_finding_as_fact`
- `heavy_review_without_trace`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:code-review]]
- [[source:schemas/skill_contracts.json#code-review]]
- [[term:Gate Evidence]]
