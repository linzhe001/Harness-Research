---
name: validate-run
description: Codex wrapper for WF9 validation. Use when the user wants the training chain reviewed and smoke-tested before entering WF10.
---

# Validate Run

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `./references/review-checklist.md`
- `./references/validate-run-report.md`
- `../../../project_map.json`
- `../../../docs/Technical_Spec.md`
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists
- `../../../CLAUDE.md`

## When To Use

Use this skill for WF9 when the user wants to verify the codebase is safe to enter the iteration loop.

## Required Work

1. Read the new implementation, baseline references, and technical spec.
2. Run the canonical semantic review:
   - data pipeline equivalence
   - model and rendering equivalence
   - loss equivalence
   - metric equivalence
   - common ML bug checks
3. Run the canonical smoke test:
   - 100-step training
   - checkpoint save and load
   - evaluation run
   - wandb check
   - `git_snapshot` check
4. Classify the result as:
   - `PASS`
   - `REVIEW`
   - `FAIL`
5. Write `docs/Validate_Run_Report.md` with evidence sources, raw log paths, review trace paths, commands, and verdict.
6. Clean up temporary smoke-test artifacts.
7. Report a gate ledger for semantic review, smoke test, report write, and any
   workflow-state check run before WF10 readiness.

## Codex Adaptation

- Treat natural-language requests as the canonical `$validate-run [config_path]` flow.
- Preserve the canonical two-part gate: semantic review plus smoke test.
- If the canonical workflow routes to a fix step, use `$code-debug`.
- Use `../../../.agents/references/language-policy.md` for reply language and for localizing natural-language review notes and verdict summaries; keep checklist item names, commands, status labels, and identifiers in English.

## Execution Rule

Follow the local validation sequence and language policy instead of reducing this stage to a quick smoke test only.
Do not report WF9 as PASS unless the semantic review and smoke-test evidence are
listed with commands/log paths or explicitly marked `NOT_RUN`.
