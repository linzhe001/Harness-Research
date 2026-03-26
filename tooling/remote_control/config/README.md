# Remote Control Config

This directory holds the local operator inputs used by the Harness remote
control wrapper and the patched `cc-connect` integration for this repository.

- `cc_connect.local.toml`: the live local `cc-connect` starter config for this
  repo. It is pre-wired for `codex` + Feishu and mirrors the account paths from
  `tooling/auto_iterate/config/accounts.local.yaml`.
- `remote_control.local.yaml`: the live local wrapper defaults used by
  `tooling/remote_control/scripts/harness_remote.py`.
- `templates/`: reusable examples and presets; do not treat them as the active
  local config by default.

Git usage:

- `*.local.toml` and `*.local.yaml` are local-only files and should not be
  committed.
- Start from `templates/cc_connect.local.example.toml`, then write your own
  `cc_connect.local.toml`.
- See `../BUILD_AND_LOCAL_SETUP.zh-CN.md` for the full local workflow.

Recommended usage:

```bash
tooling/remote_control/bin/cc-connect -config tooling/remote_control/config/cc_connect.local.toml
```

Notes:

- If you change `tooling/auto_iterate/config/accounts.local.yaml`, also update
  the matching `CODEX_HOME` values in `cc_connect.local.toml`.
- For first boot, `allow_from = "*"` is acceptable. Once the bot is reachable,
  send `/whoami` in Feishu and replace it with your own `open_id`.
