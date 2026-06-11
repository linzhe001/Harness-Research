---
name: code-debug
description: Codex wrapper for post-WF8 repository implementation code modification and debugging. Use for planned iteration changes, bug fixes, or tightly scoped performance edits under src, scripts, configs, project_map, or Codebase_Map. Do not use for Codex hooks, skill contracts, skill routing, or permission policy; use harness-maintenance for those.
---

# Code Debug

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/ubiquitous-language.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/project-map-rule.md`
- `../../../.agents/references/pre-training-rule.md`
- `../../../.agents/references/sliced-commit-rule.md`
- `./references/debug-modes.md`
- `../../../project_map.json`
- `../../../CLAUDE.md`
- `../../../docs/20_facts/Project_Glossary.md` if it exists
- `../../../docs/20_facts/Codebase_Map.md` if it exists

## When To Use

Use this skill for post-WF8 implementation code changes:
- planned iteration changes
- bug fixes
- narrow performance tuning

Do not use this skill for Harness guardrail maintenance:
- Codex hook runtime or trust/status scripts
- skill contracts, skill routing, or trigger detection
- `.agents/skills/**` or `.claude/skills/**` edits
- permission policy or Stage write-scope changes

Use `$harness-maintenance` for those changes.

## Required Work

1. Resolve the operating mode from active iteration context or user request.
2. Read `project_map.json` before debugging stable code.
3. Read active iteration context from `.agents/state/current_iteration.json` when it exists.
4. Treat `.agents/state/` as a reserved local runtime directory, but do not assume an active context file exists.
5. Read the latest iteration report when a DEBUG decision triggered the work.
6. Apply the pre-edit checklist from `../../../.agents/references/code-style.md`.
7. Read `docs/20_facts/Project_Glossary.md` when present and preserve project vocabulary.
8. Read `docs/20_facts/Codebase_Map.md` when present and use it to locate
   stable files, module responsibilities, entry points, and maintenance owners.
9. Keep the fix inside the active slice, bug, or planned iteration scope.
   If the root cause crosses module boundaries, report the boundary issue
   instead of scattering patches across unrelated modules.
10. Add or update the smallest focused test or smoke command that catches the
   bug or planned behavior when practical; otherwise report the manual feedback
   step and `NOT_RUN` reason.
11. Make the smallest defensible change.
12. Validate changed Python files with `py_compile` and `ruff`.
13. Sync both `project_map.json` and `docs/20_facts/Codebase_Map.md` when
    stable files were added, removed, renamed, or when stable responsibilities,
    public interfaces, or dependencies changed.
14. If `docs/20_facts/Codebase_Map.md` changed, compile its Evidence Chain with
    `python tooling/evidence/compile_doc.py --workspace-root . --doc docs/20_facts/Codebase_Map.md --source project_map.json`
    plus any explicit stable source files needed to support the changed facts,
    or report `compile_doc_or_NOT_RUN`. Do not hand-edit `.evidence/**`.
15. Before committing, inspect the changed files, identify independent Commit
    Slices, and stage only the files or hunks for the completed slice. Commit
    each completed slice separately. If one cross-cutting commit is required,
    record why splitting would be unsafe.
16. Create the required semantic commit before handing the code back to training.
17. If `project_map.json` changed, run
    `python tooling/evidence/check_workflow_state.py --workspace-root .` and
    report the gate ledger.
18. If `docs/20_facts/Codebase_Map.md` was changed and the fix is otherwise
    validated, invoke `$docs-site` or report `docs_site_boundary_report`.
    Do not render after temporary draft edits.

## Codex Adaptation

- Treat natural-language requests about ordinary repository implementation code
  as the canonical `$code-debug` flow.
- Route hook, skill, contract, routing, and permission-policy requests to
  `$harness-maintenance`.
- Preserve the original minimal-change, validation, and semantic-commit requirements.
- Preserve sliced-commit behavior for daily changes: identify slices from the
  current diff and commit one completed slice at a time.
- Keep `project_map.json` synchronization for stable interface changes.
- Keep `docs/20_facts/Codebase_Map.md` synchronized with `project_map.json`
  when it exists.
- Use `../../../.agents/references/language-policy.md` for reply language and for any natural-language debugging summaries; keep commands, commit prefixes, paths, and identifiers in English.

## Execution Rule

Follow the local debugging contract and language policy instead of converting this skill into a general-purpose refactor tool.
Do not hide skipped validation or skipped project-map checks; report them as
`NOT_RUN` with the reason.
