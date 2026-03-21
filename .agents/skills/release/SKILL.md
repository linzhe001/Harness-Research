---
name: release
description: Codex wrapper for WF10 release and submission packaging. Use when the user wants validation, packaging, or submission preparation according to the original workflow.
---

# Release

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/language-policy.md`
- `./references/release-checklist.md`
- `./references/release-manifest.md`
- `../../../PROJECT_STATE.json`
- `../../../iteration_log.json`
- `../../../CLAUDE.md`

## When To Use

Interpret natural-language requests as one of the canonical intents:
- `validate`
- `package`
- `submit`

## Required Work

### `validate`

- Check required scenes, checkpoints, rendered outputs, filenames, formats, and resolution.
- Follow `./references/release-manifest.md` for a first-pass file-level submission check.

### `package`

- Collect the chosen outputs, build the submission layout, include a README, and validate the package.
- Create `submission/manifest.json` according to `./references/release-manifest.md` before packaging.

### `submit`

- Only run the full train-package-validate chain if the user explicitly asks for it.

## Codex Adaptation

- Treat natural-language requests as the canonical `$release {validate|package|submit}` interface.
- Preserve the original validate-before-submit rule and checkpoint-tracking requirements.
- Do not overwrite existing packages without explicit confirmation.
- Use `../../../.agents/references/language-policy.md` for reply language and for localizing natural-language packaging summaries; keep manifest keys, file names, paths, commands, and intent labels in English.

## Execution Rule

Follow the local release prompt and language policy for validation and packaging behavior.
