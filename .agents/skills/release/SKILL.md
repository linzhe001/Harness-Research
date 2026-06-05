---
name: release
description: Codex wrapper for WF12 release and submission packaging. Use when the user wants validation, packaging, or submission preparation according to the original workflow.
---

# Release

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/evidence-chain-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `./references/release-checklist.md`
- `./references/release-manifest.md`
- `../../../PROJECT_STATE.json`
- `../../../iteration_log.json`
- `../../../CLAUDE.md`
- `../../../docs/10_contract/Project_Contract.md` if it exists
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists
- `../../../docs/10_contract/Claim_Boundary.md` if it exists

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
- Ensure package README and release claims respect `docs/10_contract/Claim_Boundary.md`.
  Dynamic-context release claims require an approved Claim Boundary; legacy or
  standard projects must cite the fallback release/evaluation evidence instead
  of treating missing contracts as approval.

### `submit`

- Only run the full train-package-validate chain if the user explicitly asks for it.
- Before any final release claim, run or report the `check_dynamic_context.py
  --stage wf12 --review-packet` gate and list the result in the gate ledger.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_render_or_NOT_RUN`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Codex Adaptation

- Treat natural-language requests as the canonical `$release {validate|package|submit}` interface.
- Preserve the original validate-before-submit rule and checkpoint-tracking requirements.
- Do not overwrite existing packages without explicit confirmation.
- Include evidence sources for package contents, chosen checkpoints, manifests, and validation commands.
- Use `../../../.agents/references/language-policy.md` for reply language and for localizing natural-language packaging summaries; keep manifest keys, file names, paths, commands, and intent labels in English.

## Execution Rule

Follow the local release prompt and language policy for validation and packaging behavior.
Release readiness must cite the dynamic-context/docchain gate result or report
`NOT_RUN`; packaging alone is not claim approval.

## Supervisor CLI

For a recorded WF12 approval gate, use:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment release --goal "package release artifacts" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh approve --request-id <id> --decision approve --approved-by "<human>"
tooling/workflow_supervisor/scripts/workflow_ctl.sh resume --request-id <id> --json
```

The supervisor requires an explicit `validate`, `package`, or `submit` action,
runs `check_dynamic_context.py --stage wf12 --review-packet`, and only then
creates an exact scoped `APPROVE_ACTION` when dynamic context is active and
Project Contract, Evaluation Contract, and Claim Boundary approvals are
confirmed. It records approval and reruns the gate; it does not package or
submit by itself.
