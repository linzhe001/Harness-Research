# Setup Instructions (for AI Agents)

This guide is for bootstrapping a research project that uses this framework in a
same-worktree dual-repo layout.

## Goal

Set up one directory with two separate git histories:

- harness repo: `.harness`, operated via `hgit`, owns framework files
- research repo: normal `.git`, operated via `git`, owns project files

The two repos share one worktree, but they must not track the same files.

## Bootstrap Preflight

Before moving files around, identify which directory plays which role:

- **target workspace**: the repo that should actually run harness
- **framework source**: the place you copied Harness Research from
- **baseline/reference repo**: an older project used only for comparison

Only bootstrap the **target workspace**. Do not accidentally initialize the
framework source clone or a baseline repo as the live workspace.

Practical example from a real bring-up:

- `Aegis/` was the target workspace
- `Harness-Research/` was the framework source tree
- `MARS/` was only a baseline reference repo

Quick preflight checklist:

- `pwd` is the intended live workspace root
- this directory is the one that should own `.git`, `CLAUDE.md`, `AGENTS.md`,
  `docs/auto_iterate_goal.md`, and runtime folders such as `.cc-connect/`
- any baseline repo stays as a sibling reference directory, not the live root
- any copied framework source directory is treated as bootstrap input only

## Documentation Map

Framework-wide docs:

- `Harness_Update_Guide.md` may exist as a local-only day-2 pull/push and
  rebuild note. It is intentionally ignored and must not be added to git.

Remote-control docs:

- [tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md](./tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md) as the canonical operator guide

## Framework Contents

| Path | Purpose |
|------|---------|
| `.claude/skills/` | Claude Code skill definitions (21 skills) |
| `.claude/rules/` | Auto-triggered rules (pre-training, project-map, deps-update) |
| `.claude/shared/` | Shared references (code style, language policy, documentation rules) |
| `.claude/Workflow_Guide.md` | Full workflow documentation for Claude Code |
| `.agents/skills/` | Codex agent skill definitions (22 skills) |
| `.agents/references/` | Shared behavior constraints for Codex |
| `CLAUDE.md.template` | Project CLAUDE.md template with `{{placeholders}}` |
| `AGENTS.md.template` | Project AGENTS.md template with `{{placeholders}}` |
| `OPERATOR_CONTEXT.md.template` | Optional operator preference template; project-owned after copy |
| `templates/docs/` | Optional dynamic-context document templates for project docs |
| `schemas/` | Evidence-chain JSON schemas for compiled docs |
| `settings.local.json.template` | Claude Code permissions template |
| `tooling/evidence/` | Lightweight evidence-chain validation tools |
| `tooling/auto_iterate/scripts/` | V7 auto-iterate controller, runtime adapter, CLI |
| `tooling/auto_iterate/scripts/auto_iterate/` | Controller package (state, lock, events, goal, postcondition, recovery) |
| `tooling/auto_iterate/config/templates/` | Controller and account configuration examples |
| `tooling/auto_iterate/docs/` | Goal template, remote control guide |
| `tooling/remote_control/scripts/` | Harness remote wrapper and patched `cc-connect` build helper |
| `tooling/remote_control/cc_connect_src/` | Bundled patched `cc-connect` source tree for local builds |
| `tooling/remote_control/config/templates/` | Remote control / Feishu / Codex config templates |
| `tooling/remote_control/` docs | Local build, Feishu setup, and remote control usage notes |
| `media/` | Harness-level branding and documentation assets used by root docs |
| `tests/` | Controller test suite and fixtures |

## Workflow Stages

```
WF1(survey) → WF2(idea-debate) → WF3(refine-idea) → WF4(data) → WF5(baseline)
→ WF6(arch) → WF7(plan) → WF8(code) → WF9(validate) → WF10(iterate) → WF11(final-exp) → WF12(release)
```

The core iteration loop (WF10) follows four phases per round:

```
plan (hypothesis) → code (implement) → run (train + metrics) → eval (decision)
```

Decision vocabulary: **NEXT_ROUND** (loop), **DEBUG** (fix + loop), **CONTINUE** (advance to WF11), **PIVOT** (roll back to WF2 idea debate/refinement), **ABORT** (terminate).

## Ownership Model

### Harness-owned files (`hgit`)

- `.claude/**`
- `.agents/**`
- `*.template`
- `tooling/auto_iterate/**`
- `tooling/remote_control/**`
- `media/**`
- root `README.md`
- root `.gitignore`

### Research-owned files (`git`)

- `CLAUDE.md`
- `AGENTS.md`
- `MEMORY.md`
- `OPERATOR_CONTEXT.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `project_map.json`
- `src/`, `scripts/`, `configs/`, `docs/`, `tests/`
- `.evidence/**`
- `docs/auto_iterate_goal.md`
- `docs/iterations/**`
- `docs/90_legacy/**` for archived superseded docs
- project-specific figures/screenshots under research-owned paths such as `docs/media/`, `docs/figures/`, or `experiments/`

### Media placement

Use the root `media/` directory only for harness-owned assets referenced by
framework docs such as the root `README.md`.

If a research project needs its own figures, plots, screenshots, or diagrams,
store them inside research-owned paths such as `docs/media/`, `docs/figures/`,
`experiments/`, or another project directory tracked by the research repo.

In same-worktree dual-repo mode, the research repo should hide the root
`media/` directory through `.git/info/exclude` and should not commit those
framework assets.

### Local operator inputs

These files are convenient to keep under the harness tree, but they are
machine-local inputs rather than framework templates:

- `tooling/auto_iterate/config/controller.local.yaml`
- `tooling/auto_iterate/config/accounts.local.yaml`
- `tooling/remote_control/config/cc_connect.local.toml`
- `tooling/remote_control/config/remote_control.local.yaml`

Teams can either keep these files uncommitted or version shared defaults. This
repository chooses to version the two auto-iterate defaults above and annotate
the machine-specific fields inline. Remote control `.local` files should remain
local-only because they commonly contain Feishu credentials, operator IDs, or
machine-specific `CODEX_HOME` paths.

### Local toolchains and built binaries (never commit)

- `tooling/remote_control/vendor/go/**`
- `tooling/remote_control/vendor/bin/cc-connect*`

These are local build artifacts. Commit source, templates, and docs instead.

### Runtime-only files (never commit)

- `.auto_iterate/**`
- `.evidence/protocol_compiler/**`
- `.evidence/review_packets/**`
- `.evidence/chains/**` only when generated by a local draft run and not
  intended for project history; docchains referenced by current docs should be
  committed with those docs
- `.pytest_cache/**`
- `wandb/**`
- checkpoints and other generated binary artifacts

## Important Rule About Ignore Files

There can be multiple ignore mechanisms in the same worktree, but there should
not be two different root `.gitignore` files.

Use this split:

- the root `.gitignore` is harness-owned and exists to keep research files out
  of `hgit`
- the research repo hides harness-owned files via `.git/info/exclude`
- root framework paths such as `media/`, `README.md`, and `tooling/` belong in
  the research repo's `.git/info/exclude`, not in a second competing root
  `.gitignore`
- if the research repo needs shared ignore rules for its own generated files,
  put a `.gitignore` inside a research-owned subdirectory such as `data/`,
  `experiments/`, or `artifacts/`

In other words:

- yes: one root `.gitignore` plus research-side `.git/info/exclude`
- yes: extra subdirectory `.gitignore` files inside research-owned paths
- no: two competing root `.gitignore` files at the same project root

That split matters now that the harness repo also ships:

- `tooling/auto_iterate/**`
- `tooling/remote_control/**`

Practical note from real bootstrap: because the root `.gitignore` sits at the
shared project root, both git histories read it. If normal `git status` stops
showing research files such as `CLAUDE.md`, `AGENTS.md`, `docs/`, `src/`, or
`configs/`, the root `.gitignore` is too aggressive for dual-repo use. In that
case:

- keep the root `.gitignore` limited to rules that are safe for both repos
- move harness-only "hide research files from `hgit`" rules into
  `.harness/info/exclude`
- continue using `.git/info/exclude` to hide harness-owned files from the
  research repo

## Bootstrap

### 1. Put the harness worktree at the project root

This guide assumes the current repository contents are already present on the
machine and should become the harness worktree at the project root.

Preferred flow:

```bash
cd /path/to/current-harness-worktree
mv .git .harness
```

If the current repository contents were unpacked into a subdirectory instead:

```bash
cd /path/to/my-project
FRAMEWORK_DIR="Harness-Research"

rsync -a "$FRAMEWORK_DIR"/ ./ --exclude .git
mv "$FRAMEWORK_DIR/.git" .harness
rm -rf "$FRAMEWORK_DIR"
```

Then configure the harness repo:

```bash
git --git-dir=.harness --work-tree=. config core.bare false
git --git-dir=.harness --work-tree=. config status.showUntrackedFiles no
```

Optional shell alias:

```bash
alias hgit='git --git-dir=.harness --work-tree=.'
```

## 2. Initialize the research repo

If the project does not already have a normal git repo:

```bash
git init
```

## 3. Create project-owned files from templates

Only copy when the target file does not already exist:

```bash
[ ! -f CLAUDE.md ] && cp CLAUDE.md.template CLAUDE.md
[ ! -f AGENTS.md ] && cp AGENTS.md.template AGENTS.md
[ ! -f MEMORY.md ] && cp MEMORY.md.template MEMORY.md
# Optional: copy only when the operator will fill explicit stable preferences.
# [ ! -f OPERATOR_CONTEXT.md ] && cp OPERATOR_CONTEXT.md.template OPERATOR_CONTEXT.md
[ ! -f .claude/settings.local.json ] && cp settings.local.json.template .claude/settings.local.json
```

## 4. Create the research-side exclude file

Append harness-managed paths to `.git/info/exclude`:

```bash
cat >> .git/info/exclude <<'EOF'
# Harness-managed framework
.harness/
.claude/
.agents/
.vscode/
tooling/
media/
templates/
schemas/
README.md
AI_AGENT_SETUP.md
Harness_Update_Guide.md
.gitignore
*.template
settings.local.json.template
EOF
```

Notes:

- keep project-specific overview docs under `docs/` instead of replacing the harness root `README.md`
- keep harness branding and shared documentation assets in the root `media/` directory, but place project-specific figures under research-owned paths such as `docs/media/` or `docs/figures/`
- if the project needs shared ignore rules for its own generated files, prefer subdirectory `.gitignore` files inside research-owned paths such as `experiments/`, `data/`, or `artifacts/`

### 4b. Recommended: add harness-side exclude rules for research-owned paths

If the root `.gitignore` no longer hides research-owned files from `hgit`,
mirror those rules into `.harness/info/exclude` instead:

```bash
cat >> .harness/info/exclude <<'EOF'
# Research-owned files hidden from harness git
/CLAUDE.md
/AGENTS.md
/MEMORY.md
/OPERATOR_CONTEXT.md
/PROJECT_STATE.json
/iteration_log.json
/project_map.json
/src/
/scripts/
/configs/
/baselines/
/experiments/
/docs/
/.evidence/
/tests/
EOF
```

This keeps normal `git status` honest while still preventing `hgit status`
noise.

## 5. Create project directories

```bash
mkdir -p src scripts configs baselines experiments tests
mkdir -p docs docs/iterations docs/90_legacy
mkdir -p docs/10_contract docs/20_facts docs/30_evidence docs/35_protocol
mkdir -p docs/40_iterations/auto docs/50_memory .evidence/chains .evidence/schemas
mkdir -p .claude/iterations
mkdir -p .agents/state/iterations
```

Optional dynamic-context bootstrap:

```bash
python tooling/evidence/init_context.py --workspace-root . --set-state
```

Equivalent manual bootstrap:

```bash
cp -n templates/docs/00_START_HERE.md docs/00_START_HERE.md
cp -n templates/docs/10_contract/*.md docs/10_contract/
cp -n templates/docs/20_facts/*.md docs/20_facts/
cp -n templates/docs/30_evidence/*.md docs/30_evidence/
cp -n templates/docs/35_protocol/*.md docs/35_protocol/
cp -n templates/docs/40_iterations/latest.md docs/40_iterations/latest.md
cp -n templates/docs/50_memory/*.md docs/50_memory/
cp -n schemas/* .evidence/schemas/
```

These files are research-owned after copy. In older projects, it is fine to
keep using flat docs such as `docs/Feasibility_Report.md` until the project
opts into the dynamic context layout.

Before unattended WF10 auto-iteration in a dynamic-context project, check the
contract gate. The auto-iterate controller also runs the all-in-one WF10
dynamic-context preflight before launching unless `--skip-dynamic-preflight` is
used:

```bash
python tooling/evidence/compile_protocol.py --workspace-root .
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
python tooling/evidence/check_context_gates.py --workspace-root . --stage wf10-auto
python tooling/evidence/check_protocol_drift.py --workspace-root . --stage wf10
python tooling/evidence/build_review_packet.py --workspace-root . --stage wf10
```

`compile_protocol.py` writes a review packet under
`.evidence/protocol_compiler/<build_id>/` by default. Apply it to
`docs/35_protocol/**` only after review with `--apply --overwrite`.
`check_dynamic_context.py` is the preferred all-in-one gate command; the
individual commands remain useful for diagnosing a specific failed gate.
`build_review_packet.py` writes a short approval packet under
`.evidence/review_packets/<stage>/<build_id>/`.
If the human reviewer explicitly approves a contract, record the approval with
`approve_contract.py` instead of hand-editing the two approval records:

```bash
python tooling/evidence/approve_contract.py \
  --workspace-root . \
  --contract evaluation_contract \
  --approved-by "<human reviewer>" \
  --approval-source ".evidence/review_packets/wf10/<build_id>/review_packet.md"
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
```

Use `--allow-draft` only when the operator explicitly accepts running the
current auto-iteration with a draft Evaluation Contract. The controller exposes
the equivalent start option as `--allow-draft-contract`. Use
`--allow-review-required` only when the operator explicitly accepts running with
a protocol review gap.

To compile an auditable docchain for a current document:

```bash
python tooling/evidence/compile_doc.py \
  --workspace-root . \
  --doc docs/10_contract/Project_Contract.md \
  --source PROJECT_STATE.json docs/30_evidence/Evidence_Index.md
```

Then validate the generated chain directory:

```bash
python tooling/evidence/validate_docchain.py .evidence/chains/<doc_id>/<build_id>
```

Before treating current contract/fact/protocol docs as ready, run the docchain
gate:

```bash
python tooling/evidence/check_docchain_gates.py --workspace-root .
```

Use `--allow-missing-draft` only during early bootstrap when draft templates
still have `Evidence chain: N/A`.

Evidence outputs are versioned audit artifacts. Do not hand-edit old
`.evidence/chains/<doc>/<build>/` directories. Rerun `compile_doc.py` when the
Markdown, explicit source artifacts, fact markers, fact confidence, or support
relation changes; rerun `compile_protocol.py` when evidence tables or open
questions change; rerun `check_dynamic_context.py --review-packet` before human
approval, WF10 auto-iteration, WF11, and WF12.

Do not create `.auto_iterate/` by hand. It is controller-owned runtime state
and should appear only after the first auto-iterate `start`.

## 6. Bootstrap auto-iterate project files

The harness repo owns the controller code, remote-control wrapper, and reusable
templates. The project should create one research goal file plus a local
controller YAML. The Codex account YAML is generated from Cockpit-managed
accounts; do not create manual `.codex-acc*` homes.

```bash
[ ! -f docs/auto_iterate_goal.md ] && cp tooling/auto_iterate/docs/auto_iterate_goal_template.md docs/auto_iterate_goal.md
[ ! -f tooling/auto_iterate/config/controller.local.yaml ] && cp tooling/auto_iterate/config/templates/auto_iterate_controller.example.yaml tooling/auto_iterate/config/controller.local.yaml
tooling/auto_iterate/scripts/project_cockpit_codex_accounts.py \
  --accounts-yaml tooling/auto_iterate/config/accounts.local.yaml
```

Keep this boundary:

- edit `docs/auto_iterate_goal.md` in the research repo
- edit `tooling/auto_iterate/config/*.local.yaml` as local operator inputs for
  this workspace
- refresh `accounts.local.yaml` with
  `tooling/auto_iterate/scripts/project_cockpit_codex_accounts.py` after adding
  or reauthenticating Cockpit Codex accounts
- do not edit templates under `tooling/auto_iterate/config/templates/`
- do not create `.auto_iterate/` by hand
- do not commit `.auto_iterate/`
- if your project wants shared defaults, it is acceptable to version
  `controller.local.yaml` and `accounts.local.yaml`

## 6b. Optional: bootstrap remote control local files

If the project will use Feishu / remote-control features, create local-only
config files from templates:

```bash
[ ! -f tooling/remote_control/config/remote_control.local.yaml ] && cp tooling/remote_control/config/templates/remote_control.example.yaml tooling/remote_control/config/remote_control.local.yaml
[ ! -f tooling/remote_control/config/cc_connect.local.toml ] && cp tooling/remote_control/config/templates/cc_connect.local.example.toml tooling/remote_control/config/cc_connect.local.toml
```

Important distinction:

- `tooling/remote_control/config/templates/` is the template source directory
- `tooling/remote_control/config/cc_connect.local.toml` is the live
  `cc-connect` runtime config
- `tooling/remote_control/config/remote_control.local.yaml` is the lightweight
  wrapper config for `harness_remote.py`

On a fresh framework clone, `tooling/remote_control/config/` may contain only
`README.md` and `templates/`. That is normal. The two `.local` files appear
only after workspace bootstrap.

When filling `cc_connect.local.toml` for a same-worktree project, derive the
workspace values from the current repository root instead of editing random
absolute paths by hand:

```bash
CURRENT_WORKSPACE="$(pwd)"
WORKSPACE_NAME="$(basename "$CURRENT_WORKSPACE")"
WORKSPACE_PARENT="$(dirname "$CURRENT_WORKSPACE")"
```

Choose one of these layouts:

### Single-workspace: default to the current repository

Use this when the bot should always operate on the current repository and you do
not want to bind each chat channel manually.

- omit `[[projects]].mode`
- omit `[[projects]].base_dir`
- set `projects.agent.options.work_dir = "$CURRENT_WORKSPACE"`
- set custom command `work_dir = "$CURRENT_WORKSPACE"` for `/ai` and `/home`
- if practical, keep `[[projects]].name` aligned with `"$WORKSPACE_NAME"`

This is the simplest setup for one local repo and avoids the "No workspace
found for this channel" prompt during direct chat.

### Multi-workspace: one bot can switch between many repos

Use this when one bot instance should serve multiple workspaces under the same
parent directory.

- `[[projects]].mode = "multi-workspace"`
- `[[projects]].base_dir = "$WORKSPACE_PARENT"`
- `[[commands]]` entries such as `/ai` and `/home` may still use `work_dir = "$CURRENT_WORKSPACE"`
- if practical, keep `[[projects]].name` aligned with `"$WORKSPACE_NAME"` so bindings are easier to reason about

Important distinction in `multi-workspace` mode:

- `base_dir` is the parent directory that contains candidate workspaces
- `work_dir` on custom commands is the concrete workspace root for that command
- do not set `projects.agent.options.work_dir`; workspace routing comes from channel binding plus `base_dir`

After first boot in a chat channel, bind that channel to the current workspace:

```bash
/workspace bind <workspace-name>
```

For example, if `CURRENT_WORKSPACE=/path/to/PCLR_compare`, run:

```bash
/workspace bind PCLR_compare
```

Without that binding, direct natural-language chat to the agent may answer with
"No workspace found for this channel" even if `/ai` and `/home` already work,
because those custom commands can have their own fixed `work_dir`.

The patched `cc-connect` source is already bundled in this repository under:

- `tooling/remote_control/cc_connect_src/`

Setup and local builds use only the contents of this repository.

Keep this boundary:

- edit `tooling/remote_control/config/*.local.*` only for your own machine
- do not commit Feishu credentials, operator IDs, or `CODEX_HOME` values
- do not commit generated Codex credential projection directories such as
  `~/.cache/auto_iterate/codex/`
- do not commit `tooling/remote_control/vendor/go/`
- do not commit built binaries under `tooling/remote_control/vendor/bin/`
- do not use `git add -f` to force-add ignored local config or local binaries

Field roles to verify in `cc_connect.local.toml`:

- `app_id` / `app_secret`: Feishu app credentials
- `allow_from`: the allowed Feishu user `open_id` list for normal access
- `admin_from`: the Feishu user `open_id` list allowed to run privileged
  commands

If you do not yet know the real operator `open_id`, it is safer to leave
`admin_from` empty temporarily than to guess a value and lock yourself out.

You can verify that the main local files are ignored before continuing:

```bash
git check-ignore -v tooling/remote_control/config/cc_connect.local.toml
git check-ignore -v tooling/remote_control/config/remote_control.local.yaml
git status --short --ignored tooling/remote_control/config tooling/remote_control/vendor
```

If you need a local patched `cc-connect`, build it with:

```bash
tooling/remote_control/scripts/build_patched_cc_connect.sh
```

If `go` is not available on `PATH`, unpack Go 1.25 under
`tooling/remote_control/vendor/go/` and rerun the build. The build helper
prefers `tooling/remote_control/vendor/go/bin/go` automatically.

Then start it with:

```bash
tooling/remote_control/bin/cc-connect \
  -config tooling/remote_control/config/cc_connect.local.toml
```

If you want repo-managed local shortcuts for shared Codex sessions, install them with:

```bash
tooling/remote_control/scripts/install_user_commands.sh --shell-init
```

This installs `codex_all` and `cw` into `~/.local/bin/` and adds the minimal
PATH snippet needed for new shells.

The installer only writes shell init when your existing `~/.bashrc` / `~/.profile`
does not already contain related command or PATH setup.

If `tooling/remote_control/config/cc_connect.local.toml` already exists on your
machine, edit it in place instead of overwriting it. The workspace migration
checklist lives in
`tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md` section `1.4`.

For the full repo-local flow, including build, install, `source ~/.bashrc`,
verification, and startup order, see
`tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md` section `1.8`.

If you change `cc_connect.local.toml`, restart `cc-connect` so the live process
reloads the new project name, ACL, and workspace settings.

Minimal remote-control verification:

```bash
tooling/remote_control/bin/cc-connect -version
tooling/remote_control/bin/cc-connect share list --config tooling/remote_control/config/cc_connect.local.toml
tooling/remote_control/bin/cw list
tooling/remote_control/bin/codex_all help
```

`cc-connect -version` only proves that some binary starts. The shared-session
stack required by `cw` and `codex_all` is only validated once `share list`,
`cw list`, and `codex_all help` all succeed.

See:

- `tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md`

## 7. Fill in project details

Replace placeholders in `CLAUDE.md` and `AGENTS.md`, or use the workflow init command:

- Claude Code: `/orchestrator init`
- Codex: `$orchestrator init`

## 8. Initial research commit

Commit only research-owned files:

```bash
git add CLAUDE.md AGENTS.md MEMORY.md OPERATOR_CONTEXT.md
git add PROJECT_STATE.json project_map.json docs/ .evidence/index.json .evidence/chains/ .evidence/schemas/ configs/ src/ scripts/ tests/ 2>/dev/null || true
git commit -m "init: project scaffold"
```

Do not add harness-owned paths such as `.claude/`, `.agents/`, `tooling/`, `media/`, `README.md`, or `.gitignore`.

## Daily Dual-Repo Management

For day-2 update flow, conflict handling, and post-pull checks, use the local
`Harness_Update_Guide.md` note when present. It is intentionally ignored and
must not be added to git.

If remote control was already used before a project rename or config rewrite,
existing channel bindings may still live under the old project key in
`~/.cc-connect/workspace_bindings.json`. Rebind the channel after restart if the
bot still resolves to an old workspace or says no workspace is bound.

### Research changes

Use normal `git`:

```bash
git add src/ docs/ configs/ scripts/
git commit -m "feat: update research code"
```

### Harness/framework changes

Use `hgit`:

```bash
hgit pull origin main
hgit status
```

### Auto-iterate usage

Run the harness-managed controller from the project root so it operates on the
research worktree:

```bash
tooling/auto_iterate/scripts/project_cockpit_codex_accounts.py \
  --accounts-yaml tooling/auto_iterate/config/accounts.local.yaml

tooling/auto_iterate/scripts/auto_iterate_ctl.sh start \
  --goal docs/auto_iterate_goal.md \
  --config tooling/auto_iterate/config/controller.local.yaml \
  --accounts tooling/auto_iterate/config/accounts.local.yaml
```

If you need to point the controller at a different workspace for testing, use
the Python CLI directly:

```bash
python3 tooling/auto_iterate/scripts/auto_iterate_ctl.py \
  --workspace-root /path/to/other-workspace \
  status --json
```

### Auto-iterate bring-up notes

Practical notes from a successful bring-up:

- do not create `.auto_iterate/` by hand; `tooling/auto_iterate/scripts/auto_iterate_ctl.sh start`
  creates and owns the runtime directory, including `state.json`,
  `events.jsonl`, `runtime/`, and the goal snapshot
- create `docs/iterations/` during bootstrap so per-iteration reports and notes
  have a stable home from day 1
- create `docs/90_legacy/` during bootstrap so refreshed docs can archive old
  versions instead of keeping stale Markdown in the root docs view
- keep `docs/auto_iterate_goal.md` research-owned; keep
  `tooling/auto_iterate/config/*.local.yaml` as local operator inputs; keep
  `.auto_iterate/` runtime-only and out of git
- use Cockpit-managed Codex accounts as the credential source, then project
  each account into its own generated WSL `CODEX_HOME`
- never point multiple controller accounts at the same Cockpit current
  `~/.codex/auth.json`; that only follows the currently selected account and
  does not provide real account switching
- if an auth flow keeps failing, reauthenticate in Cockpit and rerun the
  projection script instead of creating hand-managed `.codex-acc*` directories
- for current Codex CLI versions, the harness runtime should invoke
  `codex exec --full-auto ...`; the older `--approval-mode full-auto` form is
  not accepted by newer CLIs
- Codex has runtime guardrails such as sandbox mode, approval policy,
  execpolicy `.rules`, and hooks when the installed CLI supports/configures
  them. Treat those as outer guards only: they can block or remind around tool
  use, but Harness readiness still depends on `tooling/evidence/*.py`, the
  controller preflight, and explicit human approval records.
- Optional Harness Codex hooks live in `tooling/codex_hooks/`. Prefer
  workspace-local installation:
  `python tooling/codex_hooks/install_hooks.py --workspace-root .`. That writes
  only `.codex/config.toml` and `.codex/hooks.json`; hook logic stays in
  `tooling/codex_hooks/`. Check the effective state with
  `python tooling/codex_hooks/hook_status.py --workspace-root .`. Harness hook
  state is written to `.harness_hooks/` and should never be committed.
- `--dry-run` validates controller plumbing but does not satisfy the plan-stage
  postcondition that a new iteration entry exists; `plan did not create a new
  iteration entry` is expected in a dry-run smoke test
- the first real `start` should happen only after the workspace has a stable
  research contract, at minimum `CLAUDE.md`, `AGENTS.md`, and
  `docs/auto_iterate_goal.md`, and ideally `PROJECT_STATE.json`,
  `iteration_log.json`, and `project_map.json`
- the machine running `codex exec` needs outbound network access; otherwise the
  controller may be healthy while the Codex subprocess still fails during
  websocket/login startup
- interrupted bring-up can leave `.auto_iterate/state.json` stuck in `running`;
  normalize or clean runtime state before the next real launch

Recommended local account projection:

```bash
tooling/auto_iterate/scripts/project_cockpit_codex_accounts.py \
  --accounts-yaml tooling/auto_iterate/config/accounts.local.yaml
```

This writes one generated `CODEX_HOME` per Cockpit account under
`~/.cache/auto_iterate/codex/` and updates the account registry:

```yaml
accounts:
  - id: codex_acc1
    codex_home: /home/<user>/.cache/auto_iterate/codex/codex_acc1
    enabled: true
    priority: 100
    cooldown_sec: 1800
    tags: [cockpit, team]

  - id: codex_acc2
    codex_home: /home/<user>/.cache/auto_iterate/codex/codex_acc2
    enabled: true
    priority: 90
    cooldown_sec: 1800
    tags: [cockpit, plus]
```

### Tracking a live auto-iterate run

Use these views while the controller is running:

```bash
# Overall controller state.
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json

# Phase timeline.
tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail --lines 30

# Detailed phase log (replace with the newest stderr file if the round changes).
tail -f .auto_iterate/runtime/round1_plan.stderr.log

# Canonical research output: the newest planned / training / completed iteration.
jq '.iterations[-1]' iteration_log.json
```

What each artifact answers:

- `.auto_iterate/state.json`: current loop id, phase, round, selected account
- `.auto_iterate/events.jsonl`: phase transitions and failures
- `.auto_iterate/runtime/*.stderr.log`: what Codex is actively doing inside a phase
- `iteration_log.json`: the actual experiment hypothesis, config diff, metrics,
  and lessons once a phase successfully writes back to the project state

## File Ownership Summary

| File | Tracked by | Purpose |
|------|-----------|---------|
| `.claude/skills/**` | harness (`hgit`) | Skill definitions |
| `.claude/rules/**` | harness (`hgit`) | Auto-triggered rules |
| `.claude/shared/**` | harness (`hgit`) | Shared references |
| `.claude/Workflow_Guide.md` | harness (`hgit`) | Workflow documentation |
| `.agents/skills/**` | harness (`hgit`) | Codex agent definitions |
| `.agents/references/**` | harness (`hgit`) | Shared constraints |
| `*.template` | harness (`hgit`) | Project templates |
| `tooling/auto_iterate/**` | harness (`hgit`) | Controller, runtime adapter, docs, examples |
| `README.md` | harness (`hgit`) | Harness overview and links |
| `.gitignore` | harness (`hgit`) | Harness-side ignore rules for research files |
| `.git/info/exclude` | research-local (`git`) | Research-side ignore rules for harness files |
| `CLAUDE.md` | research (`git`) | Project-specific config |
| `AGENTS.md` | research (`git`) | Project-specific config |
| `src/`, `scripts/`, `configs/` | research (`git`) | Research code |
| `docs/auto_iterate_goal.md` | research (`git`) | Project goal source consumed by auto-iterate |
| `configs/auto_iterate_*.yaml` | research (`git`) | Project-specific auto-iterate config copied from examples |
| `PROJECT_STATE.json` | research (`git`) | Workflow stage state |
| `iteration_log.json` | research (`git`) | Experiment history |
| `project_map.json` | research (`git`) | Code architecture map |
| `.auto_iterate/` | ignored runtime state | Controller state, lock, events, runtime logs |

## Verification

Run these checks after bootstrap:

```bash
# Harness repo should see framework files only.
git --git-dir=.harness --work-tree=. status

# Research repo should not list harness-owned files as untracked.
git status

# Research repo should ignore harness-owned paths.
git check-ignore -v .claude/ .agents/ tooling/ README.md AI_AGENT_SETUP.md Harness_Update_Guide.md .gitignore

# Auto-iterate project inputs should exist before the first start.
test -f docs/auto_iterate_goal.md
test -f tooling/auto_iterate/config/controller.local.yaml
test -f tooling/auto_iterate/config/accounts.local.yaml
test -d ~/.cache/auto_iterate/codex
test -d docs/iterations
```

Expected outcome:

- `hgit status` is clean or only shows intentional framework edits
- `git status` is clean or only shows research files
- `tooling/auto_iterate/**` stays harness-managed
- `tooling/auto_iterate/config/*.local.yaml` exist as local operator inputs
- `accounts.local.yaml` points at Cockpit-generated `~/.cache/auto_iterate/codex/*`
  homes, not manual `.codex-acc*` directories
- `.auto_iterate/**` remains runtime-only and uncommitted
