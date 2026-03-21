---
name: env-setup
description: Codex wrapper for environment creation and refresh. Use when the user wants the environment detected, created, or synchronized into the legacy `CLAUDE.md` format.
---

# Env Setup

## References

Read these first:
- `../../../.agents/references/deps-update-rule.md`
- `./references/environment-refresh.md`
- `../../../CLAUDE.md` if it exists
- `../init-project/references/claude-maintenance.md`

## When To Use

Interpret natural-language requests as one of:
- `create`
- `refresh`

## Required Work

### `create`

1. Gather environment name and dependency source.
2. Create the environment when explicitly requested.
3. Install dependencies.
4. Check wandb installation and login if relevant.
5. Run the refresh logic afterward.

### `refresh`

1. Detect Python, PyTorch, CUDA, GPU, relevant dependencies, conda env name, and wandb status.
2. Use the shell commands listed in `./references/environment-refresh.md` for the first-pass machine summary.
3. Update the runtime environment facts in the `## Environment` section of `CLAUDE.md`.
4. Preserve `### Dataset Paths` inside that section unless dataset addresses are intentionally being refreshed from project state.
5. Preserve the rest of `CLAUDE.md` exactly.
6. Follow `../init-project/references/claude-maintenance.md` for section-safe final writes.

## Codex Adaptation

- Treat natural-language requests as the canonical `$env-setup {create|refresh}` interface.
- If the canonical prompt wants `AskUserQuestion`, ask the user directly only for missing setup choices.
- Preserve the rule that refresh mode updates runtime environment facts while keeping dataset addresses intact unless the workflow explicitly refreshes them.

## Execution Rule

Follow the local prompt for environment detection and CLAUDE.md synchronization.
