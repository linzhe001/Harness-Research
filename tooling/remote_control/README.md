# Remote Control Wrapper

This directory contains a thin remote-control wrapper for Harness Research.

Current scope:

- Wrap `tooling/auto_iterate/scripts/auto_iterate_ctl.sh`
- Expose a stable `/ai ...`-style CLI for future Feishu integration
- Expose a workspace summary command for `/home` cards
- Provide text and JSON output modes

## Usage

Run from the workspace root:

```bash
python3 tooling/remote_control/scripts/harness_remote.py ai status
python3 tooling/remote_control/scripts/harness_remote.py ai status --json
python3 tooling/remote_control/scripts/harness_remote.py ai tail --lines 10
python3 tooling/remote_control/scripts/harness_remote.py ai pause
python3 tooling/remote_control/scripts/harness_remote.py ai resume
python3 tooling/remote_control/scripts/harness_remote.py ai logs --stream stdout --lines 20
python3 tooling/remote_control/scripts/harness_remote.py summary
python3 tooling/remote_control/scripts/harness_remote.py summary --json
python3 tooling/remote_control/scripts/harness_remote.py hint --context ai-paused
python3 tooling/remote_control/scripts/harness_remote.py hint --context workspace-switched --json
```

Or use the shell wrapper:

```bash
tooling/remote_control/scripts/harness_remote.sh ai status
```

## Config

Optional config file:

```text
tooling/remote_control/config/remote_control.local.yaml
```

If absent, the wrapper falls back to:

- `docs/auto_iterate_goal.md`
- `tooling/auto_iterate/config/controller.local.yaml`
- `tooling/auto_iterate/config/accounts.local.yaml`

See `config/README.md` and `config/templates/remote_control.example.yaml` for
the full layout and template.

## Tests

```bash
python3 -m unittest discover -s tooling/remote_control/tests
```

## cc-connect Integration

Recommended setup:

- use the bundled patched `cc-connect /home` card
- expose this wrapper through a custom `/ai` exec command

See:

- `cc_connect_src/`
- `config/cc_connect.local.toml`
- `config/templates/cc_connect.local.example.toml`
- `config/templates/cc_connect_commands.example.toml`
- `config/templates/cc_connect_feishu_codex.example.toml`
- `FEISHU_MVP_SETUP.zh-CN.md`
- `BUILD_AND_LOCAL_SETUP.zh-CN.md`

Recommended local workflow:

1. Copy `config/templates/cc_connect.local.example.toml` to `config/cc_connect.local.toml`
2. Fill Feishu credentials / `CODEX_HOME` / paths locally
3. Build patched `cc-connect` from `cc_connect_src/` with `scripts/build_patched_cc_connect.sh`
4. Start via `tooling/remote_control/bin/cc-connect`

Recommended command mapping:

- `/home` -> built-in `cc-connect` home card, which loads `summary --json`
- `/ai status` -> `harness_remote.sh ai status`
- `/ai tail` -> `harness_remote.sh ai tail`
- `/ai pause` -> `harness_remote.sh ai pause`
- `/ai resume` -> `harness_remote.sh ai resume`
- `/ai stop` -> `harness_remote.sh ai stop`
- `/help auto` -> built-in help card group for auto-iterate controls

You only need to register a single custom command:

```toml
[[commands]]
name = "ai"
description = "Harness auto-iterate remote wrapper"
exec = "tooling/remote_control/scripts/harness_remote.sh ai {{args}}"
work_dir = "/path/to/workspace"
```

Then chat commands like `/ai status` and `/ai pause` will flow through the
wrapper unchanged.
