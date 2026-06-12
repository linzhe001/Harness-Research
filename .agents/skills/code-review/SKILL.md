# Code Review

Use this Skill for review-only checks. Do not edit subject code, configs,
tests, current docs, or canonical state while this Skill is active.

## Read First

- `../../../.agents/references/code-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/project-map-rule.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `../../../.agents/references/contract-gating-rule.md`
- `./references/review-report.md`
- `project_map.json`, `AGENTS.md`, `CLAUDE.md` when present

## Modes

- `light`: targeted read-only inspection; concise line-referenced findings.
- `medium`: post-change review; capture git metadata, changed ranges, Codex
  review attempt, optional external model review, reconciliation, and report.
- `heavy`: gate/release/docs-supporting review; independent Codex plus
  external model attempts unless unavailable; unresolved critical findings
  block readiness claims.

Use `$code-debug` for ordinary fixes after review and `$harness-maintenance`
for hook, skill contract, routing, or permission-policy fixes.

## Required Work

1. Resolve mode and review scope: base ref, included/excluded paths, generated
   and runtime exclusions, staged/unstaged/committed surface.
2. Capture git metadata and changed line ranges using
   `./references/review-report.md`.
3. Read subject files from disk; use `project_map.json` for stable code
   responsibilities when present.
4. Prepare independent reviewer prompts with paths, constraints, and
   objectives, not executor interpretations.
5. Attempt Codex review through the available review surface, or record
   `codex_review_or_NOT_RUN`.
6. Attempt external model review only when configured. Provider-backed review
   must run through `tooling/model_api/harness_external_review.py`; hooks
   require an active `$code-review heavy` session. Prefer targeted prompts from
   `tooling/model_api/build_review_prompt.py --scope changed`; use agentic mode
   only for high-rigor local read-only review. Do not send full-repository
   bundles unless the operator accepts the cost.
7. Verify model findings against checked-out files and diff. A model finding is
   not a project fact until line-referenced and checked.
8. Reconcile as `accepted`, `rejected_with_reason`, `needs_human`, or
   `not_reproducible`.
9. For medium/heavy, write
   `.agents/state/review_traces/code-review/<YYYY-MM-DD>_runNN/review_report.md`.
10. Report Gate ledger for report generation, skipped reviewers, and affected
    workflow gates.

## Output

For light mode, lead with findings. For medium/heavy, include report path,
scope, git metadata, reviewer statuses, provider/model when used, reconciled
counts, unresolved findings, and Gate ledger.
