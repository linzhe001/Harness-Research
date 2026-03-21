---
name: validate-run
description: Codex wrapper for WF7.5 validation. Use when the user wants the training chain reviewed and smoke-tested before entering WF8.
---

# Validate Run

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `./references/review-checklist.md`
- `../../../project_map.json`
- `../../../docs/Technical_Spec.md`
- `../../../CLAUDE.md`

## When To Use

Use this skill for WF7.5 when the user wants to verify the codebase is safe to enter the iteration loop.

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
5. Clean up temporary smoke-test artifacts.

## Codex Adaptation

- Treat natural-language requests as the canonical `$validate-run [config_path]` flow.
- Preserve the canonical two-part gate: semantic review plus smoke test.
- If the canonical workflow routes to a fix step, use `$code-debug`.

## Execution Rule

Follow the local validation sequence instead of reducing this stage to a quick smoke test only.
