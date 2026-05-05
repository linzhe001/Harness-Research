---
name: code-review
description: Review code, docs-supporting code, and git diffs with line-referenced findings, git metadata, Codex review, optional DeepSeek cross-check, and a reconciled report.
---

# Code Review

## References

Read these first:
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/project-map-rule.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `../../../.agents/references/contract-gating-rule.md`
- `./references/review-report.md`
- `../../../project_map.json` when it exists
- `../../../AGENTS.md` when it exists
- `../../../CLAUDE.md` when it exists

## When To Use

Use this skill for review-only checks of code or code-backed docs:
- light review during codebase understanding or targeted code search
- medium review after code changes, before handoff
- heavy review when stage docs, evidence chains, release claims, or gate packets
  depend on the changed code

Use `$code-debug` for fixes after the review. Do not modify subject code while
this skill is active.

## Modes

- `light`: targeted read-only inspection. External model review is optional.
  Inline findings are acceptable, but every concrete bug claim still needs a
  file and line reference.
- `medium`: post-change review. Collect git metadata, changed line ranges,
  attempt Codex review, attempt DeepSeek review when available, reconcile
  findings, and write a local review report.
- `heavy`: docs/evidence/gate review. Use independent Codex and DeepSeek review
  attempts unless unavailable, save review traces, reconcile findings, and do
  not treat generated docs or gate evidence as ready while unresolved critical
  findings remain.

## Required Work

1. Resolve mode from the user request and current workflow phase.
2. Define review scope before reading deeply:
   - base ref or working tree
   - included paths
   - excluded generated/runtime paths
   - whether staged, unstaged, or committed changes are in scope
3. Capture git metadata and changed line ranges using the commands in
   `./references/review-report.md`.
4. Read the relevant subject files from disk. For stable code, use
   `project_map.json` when present to find responsibilities and interfaces.
5. Prepare independent reviewer prompts. Follow
   `../../../.agents/references/reviewer-independence.md`; pass paths,
   constraints, and objectives, not the executor's interpretation.
6. Attempt Codex review through the current environment's exposed Codex review
   surface, such as a built-in review command, MCP tool, or configured reviewer
   command. Record `codex_review_or_NOT_RUN` when no such surface is available.
7. Attempt DeepSeek v4 Pro review when configured by the operator. Record
   `deepseek_review_or_NOT_RUN`; do not invent a result when the model is not
   available.
8. Verify reviewer findings against the checked-out files and diff. A model
   finding is not a project fact until it is line-referenced and checked.
9. Reconcile reviewer results into one findings table:
   - `accepted`
   - `rejected_with_reason`
   - `needs_human`
   - `not_reproducible`
10. For medium and heavy mode, write
    `.agents/state/review_traces/code-review/<YYYY-MM-DD>_runNN/review_report.md`
    using `./references/review-report.md`.
11. Report a Gate ledger for report generation, skipped reviewers, and any
    workflow gate affected by the review.

## Boundary Rules

- Do not edit reviewed source files, configs, tests, current docs, or canonical
  state from this skill.
- Review output belongs in `.agents/state/review_traces/code-review/` unless the
  user explicitly asks for another artifact.
- Do not manually write `.evidence/**`; use the evidence tooling or
  `$doc-compiler` when a current doc or evidence chain must change.
- Do not report PASS/ready for heavy review when any accepted critical finding
  remains unresolved.

## Output

For light mode, respond with concise findings and `NOT_RUN` entries for skipped
reviewers when relevant.

For medium/heavy mode, include:
- review report path
- git `HEAD` and base ref or working-tree scope
- changed files and line ranges reviewed
- Codex and DeepSeek statuses
- reconciled critical/warning/info counts
- unresolved findings
- Gate ledger
