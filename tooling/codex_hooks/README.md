# Codex Hooks for Harness

These hooks turn Harness workflow rules into lightweight Codex guardrails.

The default policy is advisory: prompt routing supplies compact context, and
tool-time checks warn before risky work instead of stopping ordinary progress.
Hard blocks are reserved for boundaries where a tool call would create
unrecoverable or misleading state.

The hooks provide five layers:

- Route Context: infer a `candidate_skill` and inject one compact hint for the
  current turn.
- Workspace Capsule: inject stable repository guidance once per session.
- Tool Notices: warn once per turn for missing recommended reads, mixed owner
  writes, commit hygiene, or likely skill routing mismatches.
- Boundary Blocks: block direct edits to tool-owned paths and local-only
  artifacts.
- External Review Guard: require `$code-review heavy` route context before
  provider-backed review calls.

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
.codex/rules/harness_external_review.rules
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
hooks = true
```

Older Codex versions used `[features].codex_hooks`; current Codex versions use
`[features].hooks`. The installer migrates the old key when it updates config.

It also installs a narrow project-local Codex execpolicy rule that allows
network escalation without prompting only for:

```bash
python tooling/model_api/harness_external_review.py ...
```

The wrapper and PreToolUse hook still require `$code-review heavy` route context
before a provider-backed external review script can run. Restart Codex after
changing hooks or rules.

Current Codex versions require human review before newly installed hook commands
run. After installing or changing `.codex/hooks.json`, open `/hooks` in the
Codex TUI and trust the four Harness workspace hooks if the commands match this
file.

Check the effective installation:

```bash
python tooling/codex_hooks/hook_status.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status
python tooling/codex_hooks/check_contracts.py --workspace-root . --hook-status
python tooling/codex_hooks/check_contracts.py --workspace-root . --hook-status --trust-status
```

`--trust-status` asks the local Codex app-server for the same trust state shown
by `/hooks`. It exits non-zero when enabled hooks are still `untrusted` or
`modified`.

## Workflow Write Boundaries

Harness uses two different layers for write control:

```text
Codex sandbox
  -> coarse filesystem / network boundary

Harness hooks
  -> lightweight route hints, one-time notices, and narrow hard boundary checks
```

Recommended default:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = false
writable_roots = []

[features]
hooks = true
```

Use `workspace-write` for normal workflow work. Add a path to
`sandbox_workspace_write.writable_roots` or use `--add-dir` only when the work
must write outside the repo root. Avoid `danger-full-access` unless the
environment is already isolated and you explicitly want the Codex sandbox to
provide less protection.

The new hook model keeps prompt routing lightweight:

```text
UserPromptSubmit
  -> infer candidate_skill and intent
  -> inject one route hint plus an optional workspace capsule

PreToolUse
  -> hard-block only narrow boundary violations
  -> otherwise emit one-time notices for risky or under-contextualized actions

PostToolUse
  -> silently record reads, writes, and pending metadata

Stop
  -> clear pending metadata when a full Gate ledger is present
  -> do not block ordinary final responses by default
```

`candidate_skill` is the normal route hint. It tells the model which Harness
skill or stage is likely relevant, but it is advisory only. The legacy
`active_skill` field may still appear for old session compatibility and for
external-review tests; new prompt detection should not rely on it as a
permission state.

`schemas/skill_contracts.json` remains the source of truth for required reads,
declared writable paths, artifact outputs, forbidden actions, and human
approval metadata. Hooks use that data to produce targeted notices and stage
cards. Prompt inference does not open a broad stage write surface.

Tool-time policy is intentionally concrete:

- Missing recommended reads produce a notice, not a block.
- Mixed-owner writes or commits produce a notice, not a block.
- `git commit` produces a notice when
  `.agents/references/sliced-commit-rule.md` has not been read in the turn.
- Mutations that mention guardrail paths produce a route hint notice.
- Manual writes to `.evidence/**`, `.auto_iterate/**`, `docs/_views/**`, and
  `docs/_site/**` are blocked; use the owning tools.
- Known local-only and reference-only files are blocked from `git add`.
- Direct external review scripts are blocked; provider-backed review must use
  `tooling/model_api/harness_external_review.py`.
- External review output must stay under
  `.agents/state/review_traces/code-review/**`.

Generated view paths (`docs/_views/**` and `docs/_site/**`) are tool-owned like
`.evidence/**`. Stage skills may declare those outputs for documentation and
stage cards, but manual edits remain blocked. Renderer commands may run without
prompt-time activation; the tool-owned path block still prevents
manual tampering with generated views.

This keeps the operator-facing rule simple:

```text
Codex sandbox       = can this process write here?
Harness hook block  = would this tool call corrupt controlled state?
Harness hook notice = what context or route should the model consider first?
```

For operator-facing summaries, generate Stage Cards from the contract source:

```bash
python tooling/codex_hooks/generate_stage_cards.py --workspace-root . --output workflow_handbook/Workflow_Stage_Cards.md
```

Stage Cards are reading aids. Keep the versioned operator snapshot under
`workflow_handbook/`; `schemas/skill_contracts.json` remains
the source of truth for required reads, declared writable paths, required actions, and
forbidden actions.

Skill Contracts also declare `artifact_outputs`. This metadata explains where
durable results should land, without granting permission. Declared writable
paths answer "which paths belong to this stage or skill"; `Artifact Output`
answers "where should final docs, canonical state, tool traces, review traces,
implementation files, guidance, generated views, or release packages land."
Tool-owned outputs such as `.evidence/**`, `docs/_views/**`, and
`docs/_site/**` must set `requires_tool=true`, and direct manual writes to
`.evidence/**`, `.auto_iterate/**`, `docs/_views/**`, and `docs/_site/**`
remain blocked.

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

- `~/.codex/config.toml` gets `[features] hooks = true`.
- `~/.codex/hooks.json` contains absolute commands pointing at
  `~/.codex/harness_hooks/*.py`.
- `~/.codex/harness_hooks/` stores copied runtime scripts:
  `harness_contracts.py`, `user_prompt_submit.py`,
  `pre_tool_use_policy.py`, `post_tool_use_markers.py`, and
  `require_gate_ledger.py`.
- User-level installation does not install the external-review execpolicy
  network allow rule. If a previous Harness install wrote
  `~/.codex/rules/harness_external_review.rules`, the installer removes that
  specific rule so the network exception remains workspace-local.

If both user-level and workspace-local hooks exist, Codex loads both matching
sources. To keep workspace-only behavior, do not keep an active
`~/.codex/hooks.json` Harness hook file.

## When Hooks Run

Hooks are active when all of these are true:

- Codex is running with `[features] hooks = true` in its active config.
- A hooks definition exists in `hooks.json` or inline `[hooks]` config.
- The current lifecycle event matches the configured hook event and matcher.

Workspace-local hooks apply only to that workspace/config layer. User-level
hooks are loaded for all Codex sessions that use that `CODEX_HOME`. Harness
policy is only active in workspaces that include
`schemas/skill_contracts.json`; other workspaces pass through with no
Harness-specific block.

Restart the Codex session after changing hook config or copied runtime scripts.
Do not rely on a running Codex process to hot-reload hook changes.

Read-ledger tracking depends on observable tool events in the current prompt
turn. Shell reads such as `cat`, `sed`, `nl`, `rg`, and `git show` are recorded
when they mention tracked read-set or workspace capsule files. Direct read-tool
aliases such as `Read`, `View`, and `Open` are recorded only when the target
path is part of the recommended file set for the current route context.

`git commit` has an always-on sliced-commit notice in Harness workspaces. If the
current prompt turn has not read `.agents/references/sliced-commit-rule.md`,
the PreToolUse hook reminds the agent to identify independent Commit Slices,
stage only the current slice, validate or record `NOT_RUN`, and commit one
completed slice at a time. The notice does not block the commit.

## Detection Policy

Skill detection is intentionally stricter than substring matching:

- Ordinary Harness workspace prompts that do not match a workflow skill still
  receive the workspace capsule once per session when `AGENTS.md` or
  `CLAUDE.md` exists.
- Explicit skill syntax such as `$code-expert` and `/validate-run` records the
  matching skill as route context. Bare `WF<N>` and Decision vocabulary remain
  action-gated hints; questions stay advisory.
- Explicit skill prompts such as `$init-project`, `/validate-run`,
  `$survey-idea`, `$iterate status`, or `$docs-site render` do not unlock a
  prompt-time write surface. They make the intended route explicit so
  PreToolUse can offer targeted read and owner notices.
- Path-like text and filenames are ignored for generic trigger matching, so a
  filename such as `Harness_Workflow_Implementation_Review.md` does not trigger
  `implement`.
- Ordinary implementation code-change prompts can infer a code skill without
  explicit syntax: modification/fix/refactor prompts infer `code-debug`, while
  new implementation prompts infer `code-expert`.
- Guardrail maintenance prompts that mention hooks, hook trust/status, skill
  contracts, skill routing/triggers, permission policy, or
  `.agents/.claude` skill alignment infer `harness-maintenance` before generic
  `fix` or `debug` routing. This keeps hook/skill permission work out of
  `code-debug`.
- Code review prompts infer `code-review` when the user asks for review of code,
  diffs, changed files, or code-backed docs. The intent records a mode:
  `code_review_light`, `code_review_medium`, or `code_review_heavy`.
- Short continuation prompts such as `继续`, `continue`, or `resume` keep the
  previous route context only when both the previous and current hook events
  have the same non-empty Codex `session_id`. This prevents stale
  workspace-local sessions from leaking across independent conversations.
- Code-search and read-only prompts, such as asking where a file/function lives
  or asking for an explanation, receive context only; they do not create Stop
  requirements.

When the route context is `code-review`, mutating tools are allowed only for
local review artifacts under `.agents/state/review_traces/code-review/`; source
fixes should route through `code-debug`, while hook/skill/permission fixes
should route through `harness-maintenance`.
Pure local writes under `.agents/state/review_traces/code-review/` do not create
a pending Gate ledger requirement or approval requirement, even when the
working tree already has unrelated dirty source, docs, tests, config, or other
sensitive paths. If the current tool event attempts to write those subject
paths during `code-review`, the normal review-only boundary still blocks it.

## Runtime Files

Hooks write local state under `.harness_hooks/`:

- `session.json` records route context inferred from the user prompt.
- `notices.json` records notice fingerprints so the same advisory message is
  not repeated within a turn or session.
- `read_ledger.json` records tracked files observed during the current prompt turn.
- `read_ledgers/` stores session-scoped read ledgers; checks merge these with
  `read_ledger.json` so parallel tool reads cannot hide files already recorded
  in the same prompt turn.
- `pending_actions.json` records the last observed mutating tool metadata. Stop
  clears compatible pending state when a full Gate ledger is present, but does
  not block final responses by default.

Continuation prompts preserve the previous `session.json` route context and
`read_ledger.json` so a multi-turn review can continue without losing Harness
context. Non-continuation prompts still start a fresh session and reset the read
ledger.

These files are runtime state and must not be committed.

## External Review Network Guard

For heavy code review, external model calls should use:

```bash
python tooling/model_api/harness_external_review.py agentic --provider deepseek ...
```

Direct calls to `tooling/model_api/agentic_review.py` or
`tooling/model_api/external_chat.py` are blocked by the Harness PreToolUse hook
in Harness workspaces. The wrapper checks `.harness_hooks/session.json` and
continues only when the route context is `code-review` and the intent is
`code_review_heavy`.

## Contract Source

The skill contracts live in:

```text
schemas/skill_contracts.json
schemas/skill_contracts.schema.json
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
