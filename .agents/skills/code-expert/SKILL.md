---
name: code-expert
description: Codex wrapper for WF7 first-pass code generation. Use when the user wants implementation generated directly from `project_map.json`, the roadmap, and the original Claude skill contract.
---

# Code Expert

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/project-map-rule.md`
- `./references/generation-order.md`
- `../../../PROJECT_STATE.json`
- `../../../project_map.json`
- `../../../docs/Implementation_Roadmap.md`

## When To Use

Use this skill for WF7 first-pass code generation only.

## Required Work

1. Read `project_map.json`, `docs/Implementation_Roadmap.md`, `PROJECT_STATE.json`, and the style/rule files before editing.
2. Generate code in dependency order, following the canonical sequence:
   - `src/utils/`
   - `src/models/`
   - `src/data/`
   - `src/losses/`
   - `scripts/`
   - `tests/`
3. After each stable-file creation or interface change, sync `project_map.json`.
4. Validate modified Python files with:
   - `python -m py_compile`
   - `ruff check --select=E,F,I`
5. Update `PROJECT_STATE.json` on full success.

## Routing Rule

- If the request is a narrow bug fix, planned iteration change, or post-WF7 edit, use `$code-debug` instead.

## Codex Adaptation

- Treat natural-language requests as the canonical `$code-expert [target or all]` flow.
- Preserve the dependency-ordered generation style and the requirement to read `project_map.json` and the roadmap before editing.
- Keep the canonical validation pattern and project-map synchronization.
- Use `../../../.agents/references/language-policy.md` for reply language and for any natural-language summaries; keep paths, schema keys, commands, and code identifiers in English.

## Execution Rule

Follow the local prompt and language policy as the source of truth for WF7 code generation behavior.
