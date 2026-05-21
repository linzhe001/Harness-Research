---
name: code-expert
description: Codex wrapper for WF8 first-pass code generation. Use when the user wants implementation generated directly from `project_map.json`, `docs/20_facts/Codebase_Map.md`, the roadmap, and the original Claude skill contract.
---

# Code Expert

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/ubiquitous-language.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/project-map-rule.md`
- `../../../.agents/references/sliced-commit-rule.md`
- `./references/generation-order.md`
- `../../../PROJECT_STATE.json`
- `../../../project_map.json`
- `../../../docs/Implementation_Roadmap.md`
- `../../../docs/20_facts/Project_Glossary.md` if it exists
- `../../../docs/20_facts/Codebase_Map.md` if it exists
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists

## When To Use

Use this skill for WF8 first-pass code generation only.

## Required Work

1. Read `project_map.json`, `docs/Implementation_Roadmap.md`, `PROJECT_STATE.json`, contracts when present, and the style/rule files before editing.
2. Apply the pre-edit checklist from `../../../.agents/references/code-style.md`.
3. Select the current roadmap slice. Do not implement unrelated slices or
   broaden public APIs beyond the slice trace without recording the boundary
   change and updating `project_map.json`.
4. Read `docs/20_facts/Project_Glossary.md` when present. New identifiers,
   config keys, metric keys, test names, and error messages must use existing
   glossary terms or record proposed terms for review.
5. Read `docs/20_facts/Codebase_Map.md` when present and use it as the
   operator-facing map of stable files, module responsibilities, entry points,
   and maintenance owners.
6. Write or update the first focused test or smoke check before implementation
   when the slice is automatable. If it cannot be automated, record the manual
   feedback step and `NOT_RUN` reason.
7. Complete one roadmap slice at a time. After a slice is implemented,
   validated, and any required `project_map.json` update is complete, create a
   semantic commit for that Commit Slice before moving to the next independent
   slice. If the environment cannot commit, report `NOT_RUN` with the reason.
8. Generate code in dependency order, following the canonical sequence:
   - `src/utils/`
   - `src/models/`
   - `src/data/`
   - `src/losses/`
   - `scripts/`
   - `tests/`
9. After each stable-file creation, deletion, rename, responsibility change,
   public interface change, or dependency change, sync both `project_map.json`
   and `docs/20_facts/Codebase_Map.md` when the latter exists.
10. Validate modified Python files with:
   - `python -m py_compile`
   - `ruff check --select=E,F,I`
11. If `docs/20_facts/Codebase_Map.md` changed, compile its Evidence Chain with
    `python tooling/evidence/compile_doc.py --workspace-root . --doc docs/20_facts/Codebase_Map.md --source project_map.json`
    plus any explicit stable source files needed to support the changed facts,
    or report `compile_doc_or_NOT_RUN`. Do not hand-edit `.evidence/**`.
12. Update `PROJECT_STATE.json` on full success.
13. Run `python tooling/evidence/check_workflow_state.py --workspace-root .`
   when `PROJECT_STATE.json` or `project_map.json` changed, and report the gate
   ledger.
14. If `docs/20_facts/Codebase_Map.md` was changed and the slice is otherwise
    validated, invoke `$docs-site` or report `docs_site_render_or_NOT_RUN`.
    Do not render after temporary draft edits.

## Routing Rule

- If the request is a narrow bug fix, planned iteration change, or post-WF8 edit, use `$code-debug` instead.

## Codex Adaptation

- Treat natural-language requests as the canonical `$code-expert [target or all]` flow.
- Preserve the dependency-ordered generation style and the requirement to read `project_map.json` and the roadmap before editing.
- Preserve vertical-slice scope and TDD/smoke feedback from the roadmap.
- Preserve sliced-commit behavior: one completed and validated roadmap slice
  should become one semantic commit before the next independent slice starts.
- Keep the canonical validation pattern and project-map synchronization.
- Use `../../../.agents/references/language-policy.md` for reply language and for any natural-language summaries; keep paths, schema keys, commands, and code identifiers in English.

## Execution Rule

Follow the local prompt and language policy as the source of truth for WF8 code generation behavior.
Do not report the implementation as complete unless validation and required
project-map/workflow-state checks are listed with PASS, FAIL, or NOT_RUN.
