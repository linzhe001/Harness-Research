# Auto-Iterate Tooling

This directory holds the repository-level auto-iterate assets so they do not
collide with a research project's own top-level `scripts/`, `config/`, and
`docs/` folders.

- `scripts/` contains the controller CLI, runtime adapter, and Python package.
- `config/` holds reusable templates plus the repo's shared local YAML defaults
  such as `controller.local.yaml` and `accounts.local.yaml`.
- `docs/` contains operator-facing static docs, templates, and the v7 plan/spec set.

Per-project runtime state is still written to the project root under
`.auto_iterate/`. Research artifacts such as `docs/auto_iterate_goal.md`,
`iteration_log.json`, and `PROJECT_STATE.json` remain project-owned files.
