---
name: code-debug
description: Codex wrapper for post-WF7 code modification and debugging. Use when the user wants planned iteration changes, bug fixes, or tightly scoped performance edits while preserving the original workflow constraints.
---

# Code Debug

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/project-map-rule.md`
- `../../../.agents/references/pre-training-rule.md`
- `./references/debug-modes.md`
- `../../../project_map.json`
- `../../../CLAUDE.md`

## When To Use

Use this skill for all post-WF7 code changes:
- planned iteration changes
- bug fixes
- narrow performance tuning

## Required Work

1. Resolve the operating mode from active iteration context or user request.
2. Read `project_map.json` before debugging stable code.
3. Read active iteration context from `.agents/state/current_iteration.json` when it exists.
4. Treat `.agents/state/` as a reserved local runtime directory, but do not assume an active context file exists.
5. Read the latest iteration report when a DEBUG decision triggered the work.
6. Make the smallest defensible change.
7. Validate changed Python files with `py_compile` and `ruff`.
8. Sync `project_map.json` when stable interfaces changed.
9. Create the required semantic commit before handing the code back to training.

## Codex Adaptation

- Treat natural-language requests as the canonical `$code-debug` flow.
- Preserve the original minimal-change, validation, and semantic-commit requirements.
- Keep `project_map.json` synchronization for stable interface changes.
- Use `../../../.agents/references/language-policy.md` for reply language and for any natural-language debugging summaries; keep commands, commit prefixes, paths, and identifiers in English.

## Execution Rule

Follow the local debugging contract and language policy instead of converting this skill into a general-purpose refactor tool.
