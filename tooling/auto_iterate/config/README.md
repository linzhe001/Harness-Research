# Auto-Iterate Config

This directory holds the YAML inputs used to launch the local auto-iterate
controller for a specific workspace.

## What Lives Here

- `controller.local.yaml`
  - the live local controller policy
  - create it from the template when bootstrapping a workspace
  - this repo also versions a shared default copy for convenience
- `accounts.local.yaml`
  - the live local Codex account pool
  - keep machine-specific `CODEX_HOME` paths here
  - this repo also versions a shared default copy with inline comments showing
    what to edit
- `templates/`
  - reusable examples and presets
  - do not treat templates as the active local config

By default these `*.local.yaml` files are local operator inputs. This repository
explicitly versions `controller.local.yaml` and `accounts.local.yaml` as shared
starting points, but the values still need to match the current machine and the
current workspace.

## Bootstrap Scope

First identify the directory roles correctly:

- **target workspace**: the repo that should actually run auto-iterate
- **framework source**: where Harness Research was copied from
- **baseline/reference repo**: an older project used only for comparison

Only the **target workspace** should own:

- `docs/auto_iterate_goal.md`
- `tooling/auto_iterate/config/controller.local.yaml`
- `tooling/auto_iterate/config/accounts.local.yaml`
- runtime state under `.auto_iterate/`

Do not point the controller at a framework source clone or a baseline repo by
mistake.

## Preflight Checklist

Before the first real `start`, verify all of these:

- `pwd` is the intended live workspace root
- `docs/auto_iterate_goal.md` exists and is no longer placeholder-only
- `CLAUDE.md` and `AGENTS.md` exist for the current workspace
- ideally `PROJECT_STATE.json`, `iteration_log.json`, and `project_map.json`
  also exist before the first unattended run
- every configured `CODEX_HOME` is a dedicated account home, not a shared
  multi-account directory
- each account passes `CODEX_HOME=/path/to/home codex login status`
- the machine that will run `codex exec` has outbound network access

Recommended account verification:

```bash
CODEX_HOME=/path/to/acc1 codex login status
CODEX_HOME=/path/to/acc2 codex login status
```

Recommended controller verification:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json
```

## `--dry-run` vs Real Start

`--dry-run` is only a controller plumbing smoke test.

It can verify that:

- the controller CLI starts
- config parsing works
- account resolution works
- the runtime can reach the stage launcher

It does **not** prove that a full plan round completed successfully.

In particular, `--dry-run` does not satisfy the normal plan-stage postcondition
that a new iteration entry was written. A message such as:

- `plan did not create a new iteration entry`

is expected during a dry-run smoke test.

## Recommended First-Run Flow

1. Validate the current workspace and goal file.
2. Verify each `CODEX_HOME` with `codex login status`.
3. Run `tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json`.
4. If needed, run one short `--dry-run` only to check controller plumbing.
5. Launch the first real run only after the workspace contract is stable.
6. If you interrupt a smoke test, inspect `.auto_iterate/state.json` before the
   next real launch.

Example real start:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh start \
  --goal docs/auto_iterate_goal.md \
  --config tooling/auto_iterate/config/controller.local.yaml \
  --accounts tooling/auto_iterate/config/accounts.local.yaml
```

Example resume:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh resume \
  --config tooling/auto_iterate/config/controller.local.yaml \
  --accounts tooling/auto_iterate/config/accounts.local.yaml
```

## Common Bring-Up Failures

### `plan did not create a new iteration entry`

Interpretation depends on context:

- during `--dry-run`: expected
- during a real run: usually means the plan phase never produced a valid new
  iteration record for the current workspace

Check:

- `docs/auto_iterate_goal.md` is specific enough to drive a real plan
- the workspace already has the expected research files
- the Codex subprocess actually launched and stayed alive long enough to write
  results

### Codex subprocess fails during websocket/login startup

This usually means the controller is fine, but the environment where
`codex exec` runs cannot reach the required network endpoints.

Symptoms often look like:

- websocket connection failures
- login/session bootstrap failures
- the controller starts, but no usable iteration output appears

Fix the environment first; changing controller YAML alone will not solve this.

### `.auto_iterate/state.json` is stuck in `running`

This commonly happens after an interrupted smoke test or a killed subprocess.

Before the next real launch:

- inspect the runtime state
- normalize it to a paused/stopped state if needed
- or clean the stale runtime after confirming no real loop is still active

Do not treat stale `running` state as proof that an iteration is still healthy.
