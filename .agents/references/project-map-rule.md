# Project Map Rule

## Type

- `always_on` for stable architecture work
- `skill_scoped` for `$build-plan`, `$code-expert`, and `$code-debug`

## Purpose

Keep `project_map.json` as the single stable architecture map for the repository.

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

`project_map.json` tracks only stable architecture files.

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
3. If the file is stable and its interface or presence changed, update `project_map.json`.
4. Keep the detail level policy consistent:
   - `src/`: `exports`, `io`, `dependencies`
   - `baselines/`: brief baseline metadata only
   - stable `configs/`, `scripts/`, `docs/`: concise `description`
   - `experiments/`: minimal purpose-only coverage
5. For non-trivial code changes, route implementation through the appropriate workflow skill:
   - `$code-expert` for first-pass WF7 implementation
   - `$code-debug` for post-WF7 changes and fixes
6. After Python edits, run:
   - `python -m py_compile <modified files>`
   - `ruff check --select=E,F,I <modified files>`

## Forbidden Actions

- Do not add volatile experiment assets to `project_map.json`.
- Do not leave a stable file addition, deletion, rename, or interface change undocumented in `project_map.json`.
- Do not treat `project_map.json` as a run log or experiment diary.

## Verification

A change satisfies this rule when:

- `project_map.json` still matches the stable file tree
- any changed stable node has updated metadata where needed
- modified Python files pass `py_compile`
- modified Python files pass `ruff check --select=E,F,I`

## Escalation

- If a stable-file change is not reflected in `project_map.json`, the task is not complete.
- If there is uncertainty about stable vs volatile classification, prefer pausing to classify explicitly rather than silently skipping the update.
