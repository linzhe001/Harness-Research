---
name: code-expert
description: Codex wrapper for WF8 first-pass code generation. Use when the user wants implementation generated directly from `project_map.json`, the roadmap, and the original Claude skill contract.
---

# Code Expert

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/project-map-rule.md`
- `./references/generation-order.md`
- `../../../PROJECT_STATE.json`
- `../../../project_map.json`
- `../../../docs/Implementation_Roadmap.md`
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists

## When To Use

Use this skill for WF8 first-pass code generation only.

## Required Work

1. Read `project_map.json`, `docs/Implementation_Roadmap.md`, `PROJECT_STATE.json`, contracts when present, and the style/rule files before editing.
2. Apply the pre-edit checklist from `../../../.agents/references/code-style.md`.
3. Generate code in dependency order, following the canonical sequence:
   - `src/utils/`
   - `src/models/`
   - `src/data/`
   - `src/losses/`
   - `scripts/`
   - `tests/`
4. After each stable-file creation or interface change, sync `project_map.json`.
5. Validate modified Python files with:
   - `python -m py_compile`
   - `ruff check --select=E,F,I`
6. Update `PROJECT_STATE.json` on full success.
7. Run `python tooling/evidence/check_workflow_state.py --workspace-root .`
   when `PROJECT_STATE.json` or `project_map.json` changed, and report the gate
   ledger.

## Routing Rule

- If the request is a narrow bug fix, planned iteration change, or post-WF8 edit, use `$code-debug` instead.

## Codex Adaptation

- Treat natural-language requests as the canonical `$code-expert [target or all]` flow.
- Preserve the dependency-ordered generation style and the requirement to read `project_map.json` and the roadmap before editing.
- Keep the canonical validation pattern and project-map synchronization.
- Use `../../../.agents/references/language-policy.md` for reply language and for any natural-language summaries; keep paths, schema keys, commands, and code identifiers in English.

## Execution Rule

Follow the local prompt and language policy as the source of truth for WF8 code generation behavior.
Do not report the implementation as complete unless validation and required
project-map/workflow-state checks are listed with PASS, FAIL, or NOT_RUN.
