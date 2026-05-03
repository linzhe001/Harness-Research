# Auto-Iterate Tooling

This directory holds the repository-level auto-iterate assets so they do not
collide with a research project's own top-level `scripts/`, `config/`, and
`docs/` folders.

- `scripts/` contains the controller CLI, runtime adapter, and Python package.
- `config/` holds reusable templates plus the repo's shared local YAML defaults
  such as `controller.local.yaml` and `accounts.local.yaml`.
- `docs/` contains operator-facing static docs, templates, and the v7 plan/spec set.
- `scripts/project_cockpit_codex_accounts.py` projects Cockpit-managed Codex
  accounts into per-account `CODEX_HOME` directories for unattended controller
  runs. The framework no longer uses hand-created `.codex-acc*` homes.

Per-project runtime state is still written to the project root under
`.auto_iterate/`. Research artifacts such as `docs/auto_iterate_goal.md`,
`iteration_log.json`, and `PROJECT_STATE.json` remain project-owned files.

`start` runs the WF10 dynamic-context preflight through
`tooling/evidence/check_dynamic_context.py --stage wf10 --review-packet` when
that tooling exists in the workspace. The result is recorded in
`.auto_iterate/dynamic_context_preflight.json`; use
`--allow-draft-contract` only after explicit operator acceptance, and
`--skip-dynamic-preflight` only for legacy or manually gated runs.

Before starting or resuming long WF10 runs, refresh the local account registry:

```bash
tooling/auto_iterate/scripts/project_cockpit_codex_accounts.py \
  --accounts-yaml tooling/auto_iterate/config/accounts.local.yaml
```

Then launch with `--accounts tooling/auto_iterate/config/accounts.local.yaml`.
