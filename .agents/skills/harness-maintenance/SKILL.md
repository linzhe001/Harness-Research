---
name: harness-maintenance
description: "Maintain Harness framework guardrails: Codex hooks, skill contracts, skill routing/triggers, permission policy docs, schema/tests, and .agents/.claude skill alignment. Use when modifying tooling/codex_hooks, .agents/skill-contracts, .agents/skills, .claude/skills, hook detection, hook trust/status, or permission boundaries."
---

# Harness Maintenance

## References

Read these first:
- `../../../AGENTS.md`
- `../../../CLAUDE.md`
- `../../../tooling/codex_hooks/README.md`
- `../../../.agents/skill-contracts/contracts.json`
- `../../../tests/test_codex_hooks_contracts.py`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/ubiquitous-language.md` when workflow terms or operator-facing docs change
- `../../../tooling/codex_hooks/Stage_Permission_Elevation_Guide.md` when permission behavior is involved and the file exists

## When To Use

Use this skill for Harness framework maintenance:
- Codex hook runtime and hook installation/status scripts
- skill contracts, trigger detection, and routing behavior
- `.agents/skills/**` and `.claude/skills/**` alignment
- permission boundaries, trust/status checks, and external review wrapper policy
- ubiquitous language, operator handbook, and generated Stage Cards
- tests that validate hook, contract, skill routing, or permission behavior

Do not use this skill for ordinary research project implementation under `src/`, `scripts/`, or `configs/`; route that through `$code-debug` or `$code-expert`.

## Required Work

1. Re-read the affected hook, contract, skill, schema, and test files before editing.
2. Keep `.agents/` and `.claude/` behavior semantically aligned when routing or skill rules change.
3. Keep hook scripts as runtime guardrails, not proof that a research gate passed.
4. Preserve fail-fast behavior and avoid broad fallbacks.
5. Use precise Harness terminology. Do not use bare `Evidence` when
   `Conclusion Evidence`, `Evidence Chain`, `Gate Evidence`, or
   `Execution Evidence` is meant.
6. Update focused tests for hook, contract, detection, generator, or permission behavior changes.
7. Run `python tooling/codex_hooks/check_contracts.py --workspace-root .` after contract or hook changes.
8. Run `pytest tests/test_codex_hooks_contracts.py` after hook detection, policy, generator, or status changes.
9. Run `python -m py_compile <modified python files>` and `ruff check --select=E,F,I <modified python files>` after Python edits.
10. Do not hand-edit `.evidence/**` or `.auto_iterate/**`; use owning tools or controller.
11. Report a Gate ledger for hook, skill contract, routing, permission, generator, or trust behavior changes.

## Codex Adaptation

Treat natural-language requests about hook behavior, skill trigger/routing, contract scope, permissions, or Harness framework policy as `$harness-maintenance` work. Keep final replies in the user's language while preserving paths, commands, schema keys, and workflow IDs in English.
