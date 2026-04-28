# {project_name}

<!-- Idea: will be filled by /init-project update after WF1 completes -->

## Environment
```bash
# created or confirmed during WF5 baseline-repro
conda activate {env_name or "<pending>"}
```
- Runtime environment will be finalized during WF5 baseline-repro.
- Before WF5, keep this section as a placeholder instead of inventing versions.

## Tech Stack
<!-- will be filled by /init-project update after WF2 completes -->
- GPU: {gpu_name} x{count} ({vram}GB)

### Dataset Paths
<!-- dataset paths will be filled from PROJECT_STATE.json when known -->

## Project Structure
<!-- will be filled by /init-project update after WF6 completes -->

## Core Artifacts
<!-- will be filled by /init-project update after WF6 completes -->

## Language Policy
- `interaction_language`: Match the language of the latest substantive user input unless the user explicitly requests another language.
- `artifact_language`: Use the same language as `interaction_language` for natural-language sections in generated docs and reports unless the user asks otherwise.
- Keep file names, paths, commands, code identifiers, JSON/YAML keys, schema fields, workflow IDs, metric keys, and placeholder tokens in English.
- Treat English wording in templates and examples as structural guidance only; localize headings and narrative text unless a field is explicitly marked English-only.

## Entry Scripts
<!-- will be filled by /init-project update after WF7 first experiment -->
<!-- once locked, iteration phase only allows modifying these files; creating new training/eval scripts is prohibited -->

## Global Rule: project_map.json Maintenance
Any skill must sync-update `project_map.json` after **creating, deleting, or renaming** files.
See `.claude/rules/project-map.md` for detailed rules.

## Global Rule: Code Style
- Before editing `src/`, `scripts/`, `tests/`, durable configs, or supporting utilities, read `.claude/shared/code-style.md` and apply its Pre-Edit Checklist.
- Keep code changes small, readable, and fail-fast; avoid unrelated refactors and broad fallback behavior.
- After Python edits, run `python -m py_compile` and `ruff check --select=E,F,I` on modified files when feasible.

## Global Rule: Documentation Style
- Before writing docs, read `.claude/shared/documentation-evidence-rule.md` and re-read relevant source artifacts from disk.
- Also read `.claude/shared/documentation-style.md`.
- Keep docs concise and human-readable; prefer ASCII flow diagrams for workflows.
- Before refreshing an existing `docs/*.md`, move the old version into `docs/legacy/`.

## Workflow
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline) → WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
WF8 iteration loop: /iterate plan → /iterate code → /iterate run → /iterate eval → (NEXT_ROUND→repeat | DEBUG→debug round | CONTINUE→WF9 | PIVOT→WF2 | ABORT→stop)
Current stage: {current_stage or "not initialized"}

## Custom
<!-- user-added content goes here; preserved during updates -->
