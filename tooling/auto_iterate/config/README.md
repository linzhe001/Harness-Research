# Auto-Iterate Config

This directory holds the YAML inputs used to launch the local auto-iterate
controller for this repository.

- `controller.local.yaml`: the live local controller policy. Create it from the
  template when bootstrapping a workspace.
- `accounts.local.yaml`: the live local Codex account pool. Create it from the
  template and keep machine-specific `CODEX_HOME` paths here.
- `templates/`: reusable examples and presets; do not treat them as the active
  local config by default.

The `*.local.yaml` files are intended to stay local to a workspace unless you
explicitly choose to version them.

Recommended usage:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh resume \
  --config tooling/auto_iterate/config/controller.local.yaml \
  --accounts tooling/auto_iterate/config/accounts.local.yaml
```
