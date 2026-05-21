# Project Map Rule

## Type

- `always_on` for stable implementation work
- `skill_scoped` for `$build-plan`, `$code-expert`, and `$code-debug`

## Purpose

Keep `project_map.json` as the machine-readable stable implementation map for
durable repository files. It describes file layout and interfaces; it does not
replace the WF6 architecture decision in `docs/Technical_Spec.md`.

When `docs/20_facts/Codebase_Map.md` exists, keep it synchronized as the
operator-facing current fact document for the same stable codebase structure.
`project_map.json` remains the machine-readable source; `Codebase_Map.md` is
for fast human orientation.

## Scope

This rule applies when work touches stable files such as:

- `src/**/*.py`
- stable `baselines/` entries
- durable `configs/**/*.yaml`, `configs/**/*.yml`, `configs/**/*.json`
- durable `scripts/**/*.py`, `scripts/**/*.sh`
- `tests/**/*.py` when they define stable interfaces or expectations

This rule does not require updates for volatile assets such as:

- per-iteration run scripts
- one-off ablation utilities
- temporary experiment configs
- `experiments/**`

## Stable vs Volatile Policy

`project_map.json` tracks only stable implementation files.

### Stable

- `src/**/*.py`
- baseline directories tracked as durable references
- core entry scripts listed in `CLAUDE.md`
- durable configs referenced by the main workflow

### Volatile

- `scripts/run_*.sh`
- `scripts/run_ablation_*.py`
- temporary configs used for one or two experiments
- everything under `experiments/`

Practical test:

- if a file defines long-lived interfaces or architecture, treat it as stable
- if a file is disposable iteration scaffolding, treat it as volatile

## Trigger

Apply this rule whenever you:

- add a stable file
- delete a stable file
- rename a stable file
- change exports
- change function signatures
- change tensor shapes
- change module responsibilities or dependencies in a durable way

Do not apply this rule for pure internal refactors that preserve the documented interface.

## Required Actions

1. Read `project_map.json` before any non-trivial stable-code change.
2. Decide whether the touched file is stable or volatile.
3. If the file is stable and its interface or presence changed, update
   `project_map.json`.
4. If `docs/20_facts/Codebase_Map.md` exists and the stable codebase structure,
   responsibility, public interface, entry point, or dependency changed, update
   it in the same Commit Slice.
5. If `docs/20_facts/Codebase_Map.md` changed, run
   `python tooling/evidence/compile_doc.py --workspace-root . --doc docs/20_facts/Codebase_Map.md --source project_map.json`
   plus any explicit stable source files needed to support the changed facts,
   or report `compile_doc_or_NOT_RUN`. Evidence artifacts under `.evidence/**`
   are tool-owned; do not edit them by hand.
6. After the Markdown is finalized for the current slice, invoke `$docs-site`
   or report `docs_site_render_or_NOT_RUN`. Do not render after temporary draft
   edits.
7. Keep the detail level policy consistent:
   - `src/`: `exports`, `io`, `dependencies`
   - `baselines/`: brief baseline metadata only
   - stable `configs/`, `scripts/`, `docs/`: concise `description`
   - `experiments/`: minimal purpose-only coverage
8. For non-trivial code changes, route implementation through the appropriate workflow skill:
   - `$code-expert` for first-pass WF8 implementation
   - `$code-debug` for post-WF8 changes and fixes
9. After Python edits, run:
   - `python -m py_compile <modified files>`
   - `ruff check --select=E,F,I <modified files>`

## Forbidden Actions

- Do not add volatile experiment assets to `project_map.json`.
- Do not leave a stable file addition, deletion, rename, or interface change undocumented in `project_map.json`.
- Do not leave `docs/20_facts/Codebase_Map.md` stale when it exists and the
  stable codebase map changed.
- Do not treat `project_map.json` as a run log or experiment diary.

## Verification

A change satisfies this rule when:

- `project_map.json` still matches the stable file tree
- `docs/20_facts/Codebase_Map.md` matches the stable file tree when present
- the latest `Codebase_Map.md` Evidence Chain exists or `compile_doc_or_NOT_RUN`
  is recorded with a reason
- `docs/_site/**` was refreshed from Markdown by `$docs-site` or
  `docs_site_render_or_NOT_RUN` is recorded with a reason
- any changed stable node has updated metadata where needed
- modified Python files pass `py_compile`
- modified Python files pass `ruff check --select=E,F,I`

## Escalation

- If a stable-file change is not reflected in `project_map.json`, the task is not complete.
- If `docs/20_facts/Codebase_Map.md` exists and a stable-file change is not
  reflected there, the task is not complete.
- If there is uncertainty about stable vs volatile classification, prefer pausing to classify explicitly rather than silently skipping the update.
