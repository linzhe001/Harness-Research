---
name: harness-maintenance
description: "Maintain Harness guardrails: Codex hooks, skill contracts, skill routing/triggers, permission policy, schema/tests, and .agents/.claude skill alignment. Use for hooks, contracts, trust/status, and permission boundaries; use code-debug for ordinary implementation code."
argument-hint: "[hook|contract|skill|permission issue]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Harness Maintenance

<role>
You maintain Harness framework guardrails without turning ordinary research code
debugging into framework-policy work.
</role>

<instructions>
1. Read `AGENTS.md`, `CLAUDE.md`, `tooling/codex_hooks/README.md`,
   `.agents/skill-contracts/contracts.json`, and
   `tests/test_codex_hooks_contracts.py` before changing hooks or contracts.
2. Use this skill for Codex hook runtime, hook trust/status scripts, skill
   contracts, trigger/routing behavior, `.agents/skills/**`,
   `.claude/skills/**`, permission boundaries, and guardrail tests/docs.
3. Do not use this skill for ordinary implementation changes under `src/`,
   `scripts/`, or `configs/`; route those to `/code-debug` or `/code-expert`.
4. Keep `.agents/` and `.claude/` behavior semantically aligned when routing or
   skill rules change.
5. Preserve fail-fast behavior. Do not hide missing state with broad fallback
   behavior.
6. Use `.claude/shared/ubiquitous-language.md` before changing workflow terms,
   operator guidance, or application-codebase vocabulary rules. Distinguish
   Conclusion Evidence from Gate Evidence.
7. Treat hooks as runtime guardrails, not proof that a workflow gate passed.
8. After Python hook/test edits, run `python -m py_compile` and
   `ruff check --select=E,F,I` on modified Python files.
9. After contract, hook, generator, or detection changes, run
   `python tooling/codex_hooks/check_contracts.py --workspace-root .` and
   `pytest tests/test_codex_hooks_contracts.py`.
10. When validating a live Codex install, run
   `python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status`
   and report `NOT_RUN` if unavailable.
11. Report a Gate ledger for hook, skill contract, routing, permission, generator, or trust
    behavior changes.
</instructions>

<output>
Summarize the changed guardrail boundary, tests run, remaining risks, and the
Gate ledger.
</output>
