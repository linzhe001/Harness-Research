# Codex Hooks for Harness

These hooks turn Harness workflow rules into Codex guardrails.

They enforce three contracts:

- Read Contract: high-risk skills must read their declared skill/reference/project files before write actions.
- Action Contract: sensitive workflow changes require a final Gate ledger.
- Boundary Contract: direct edits to tool-owned paths and known local-only artifacts are blocked.

## Default: Workspace-Local Install

Harness defaults to workspace-local hooks so the active policy follows the
current project and does not run in unrelated workspaces.

Codex loads workspace-local hooks from `<workspace>/.codex/hooks.json` when the
project `.codex/` layer is trusted. This repository keeps the versioned hook
template in `tooling/codex_hooks/hooks.json`; installation copies only the small
config files into `.codex/`.

```bash
python tooling/codex_hooks/install_hooks.py --workspace-root .
```

This creates:

```text
.codex/config.toml
.codex/hooks.json
```

The actual hook logic stays in the versioned source directory:

```text
tooling/codex_hooks/
```

Workspace-local `hooks.json` calls those scripts via:

```text
$(git rev-parse --show-toplevel)/tooling/codex_hooks/...
```

If `<workspace>/.codex` already exists as a file, move or remove that file first
so the installer can create the `.codex/` directory.

The installer ensures hooks are enabled in `.codex/config.toml`:

```toml
[features]
codex_hooks = true
```

Check the effective installation:

```bash
python tooling/codex_hooks/hook_status.py --workspace-root .
python tooling/codex_hooks/check_contracts.py --workspace-root . --hook-status
```

## Optional: User-Level Install

Use user-level hooks only when you intentionally want the same Harness hook
definition loaded from your WSL Codex home for every Codex session that uses
that home. From Windows, this directory is visible as:

```text
\\wsl.localhost\Ubuntu-22.04\home\linzhe\.codex
```

Install user-level hooks with:

```bash
python tooling/codex_hooks/install_hooks.py --workspace-root . --scope user
```

User-level installation writes or updates:

```text
~/.codex/config.toml
~/.codex/hooks.json
~/.codex/harness_hooks/
```

Specifically:

- `~/.codex/config.toml` gets `[features] codex_hooks = true`.
- `~/.codex/hooks.json` contains absolute commands pointing at
  `~/.codex/harness_hooks/*.py`.
- `~/.codex/harness_hooks/` stores copied runtime scripts:
  `harness_contracts.py`, `user_prompt_submit.py`,
  `pre_tool_use_policy.py`, `post_tool_use_markers.py`, and
  `require_gate_ledger.py`.

If both user-level and workspace-local hooks exist, Codex loads both matching
sources. To keep workspace-only behavior, do not keep an active
`~/.codex/hooks.json` Harness hook file.

## When Hooks Run

Hooks are active when all of these are true:

- Codex is running with `[features] codex_hooks = true` in its active config.
- A hooks definition exists in `hooks.json` or inline `[hooks]` config.
- The current lifecycle event matches the configured hook event and matcher.

Workspace-local hooks apply only to that workspace/config layer. User-level
hooks are loaded for all Codex sessions that use that `CODEX_HOME`. Harness
policy is only active in workspaces that include
`.agents/skill-contracts/contracts.json`; other workspaces pass through with no
Harness-specific block.

Restart the Codex session after changing hook config or copied runtime scripts.
Do not rely on a running Codex process to hot-reload hook changes.

Read-ledger proof depends on observable tool events in the current prompt turn.
Shell reads such as `cat`, `sed`, `nl`, `rg`, and `git show` are recorded when
they mention tracked read-set or daily context files. Direct read-tool aliases
such as `Read`, `View`, and `Open` are recorded only when the target path is part
of the tracked file set for the active contract or daily workspace context.
Reads that are not exposed to hooks cannot be treated as audited proof.

## Detection Policy

Skill detection is intentionally stricter than substring matching:

- Ordinary Harness workspace prompts that do not match a workflow skill still
  receive daily workspace context when `AGENTS.md` or `CLAUDE.md` exists, asking
  Codex to read those repository guidance files before repository-specific
  answers or tool use.
- Explicit triggers such as `$code-expert`, `/validate-run`, and `WF10` select
  the matching skill and make the Stop hook enforce the required read set.
- Path-like text and filenames are ignored for generic trigger matching, so a
  filename such as `Harness_Workflow_Implementation_Review.md` does not trigger
  `implement`.
- Ordinary code-change prompts can infer a code skill without explicit syntax:
  modification/fix/refactor prompts infer `code-debug`, while new implementation
  prompts infer `code-expert`.
- Code review prompts infer `code-review` when the user asks for review of code,
  diffs, changed files, or code-backed docs. The intent records a mode:
  `code_review_light`, `code_review_medium`, or `code_review_heavy`.
- Code-search and read-only prompts, such as asking where a file/function lives
  or asking for an explanation, do not trigger workflow Stop blocking.

The required read set is always enforced before write tools when a skill is
active. The Stop hook enforces missing reads only when the user explicitly
invoked a workflow skill, a mutating tool ran, or a sensitive write created a
pending Gate ledger requirement. `code-review` is stricter than ordinary
read-only search: review prompts require the review read set before finalizing,
because the report format, reviewer independence protocol, and tracing rules are
part of the review evidence.

When `code-review` is active, mutating tools are allowed only for local review
artifacts under `.agents/state/review_traces/code-review/`; source fixes must be
routed through `code-debug`.

## Runtime Files

Hooks write local state under `.harness_hooks/`:

- `session.json` records the active skill inferred from the user prompt.
- `read_ledger.json` records tracked files observed during the current prompt turn.
- `pending_actions.json` records whether a Gate ledger is required before final response and whether the one-time reminder has already been emitted.

These files are runtime state and must not be committed.

## Contract Source

The skill contracts live in:

```text
.agents/skill-contracts/contracts.json
.agents/skill-contracts/schema.json
```

Run:

```bash
python tooling/codex_hooks/check_contracts.py --workspace-root .
```

to validate that referenced Harness skill/reference files exist.

## Local Simulation

You can run a hook script with a synthetic event without starting Codex:

```bash
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit \
  --workspace-root . \
  --event-json '{"prompt":"run $validate-run"}'

python tooling/codex_hooks/simulate_hook.py PreToolUse \
  --workspace-root . \
  --event-json '{"toolName":"local_shell","input":{"cmd":"git add plan.markdown"}}'
```

This is useful for validating policy changes before installing them into
`.codex/hooks.json` or `~/.codex/hooks.json`.
