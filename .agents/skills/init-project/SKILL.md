---
name: init-project
description: Codex wrapper for staged `CLAUDE.md` generation and updates. Use when the user wants the compact project snapshot initialized or refreshed while preserving the original staged template behavior.
---

# Init Project

## References

Read these first:
- `./references/claude-md-template.md`
- `./references/claude-maintenance.md`
- `../../../PROJECT_STATE.json` if it exists
- `../../../CLAUDE.md` if it exists

## When To Use

Interpret natural-language requests as one of:
- `init`
- `update`
- `deps-changed`

## Required Work

### `init`

1. Gather project name and, if already known, an environment name.
2. If no runnable environment exists yet, create the minimal `CLAUDE.md` with an explicit placeholder that WF5 baseline-repro owns first environment creation.
3. Create the minimal `CLAUDE.md` using the canonical template.
4. Use `./references/claude-maintenance.md` when editing individual sections instead of rewriting the whole file.

### `update`

1. Read `PROJECT_STATE.json` and the stage artifacts.
2. Fill only the sections whose source artifacts are now known:
   - idea
   - tech stack
   - environment and dataset paths
   - baseline reference
   - project structure
   - core artifacts
   - entry scripts
3. Preserve `## Custom`.
4. At WF4, dataset paths must be refreshed into `CLAUDE.md` immediately.
5. At WF5, environment facts must stop being placeholders and be replaced with the first runnable environment.
6. Update the current stage line.
7. Use `./references/claude-maintenance.md` for section-safe updates.
8. Render data-backed section bodies according to `./references/claude-maintenance.md` before writing them into `CLAUDE.md`.

### `deps-changed`

- Refresh only the environment section, equivalent to `$env-setup refresh`.

## Codex Adaptation

- Treat natural-language requests as the canonical `$init-project {init|update|deps-changed}` interface.
- Ask the user directly only for essential missing inputs.
- Preserve the staged fill-in behavior, line-budget discipline, and `## Custom` preservation rule.
- Preserve the rule that environment creation belongs to WF5 baseline-repro unless the environment already exists.
- Keep `AGENTS.md` as Codex-native always-on guidance, but maintain `CLAUDE.md` for compatibility exactly as the canonical prompt expects.

## Execution Rule

Follow the local prompt and template rather than replacing `CLAUDE.md` maintenance with a generic project summary.
