# Setup Instructions (for AI Agents)

This guide is for bootstrapping a research project that uses this framework in a
same-worktree dual-repo layout.

## Goal

Set up one directory with two separate git histories:

- harness repo: `.harness`, operated via `hgit`, owns framework files
- research repo: normal `.git`, operated via `git`, owns project files

The two repos share one worktree, but they must not track the same files.

## Framework Contents

| Path | Purpose |
|------|---------|
| `.claude/skills/` | Claude Code skill definitions (18 skills) |
| `.claude/rules/` | Auto-triggered rules (pre-training, project-map, deps-update) |
| `.claude/shared/` | Shared references (code style, language policy) |
| `.claude/Workflow_Guide.md` | Full workflow documentation for Claude Code |
| `.agents/skills/` | Codex agent skill definitions (18 skills) |
| `.agents/references/` | Shared behavior constraints for Codex |
| `CLAUDE.md.template` | Project CLAUDE.md template with `{{placeholders}}` |
| `AGENTS.md.template` | Project AGENTS.md template with `{{placeholders}}` |
| `settings.local.json.template` | Claude Code permissions template |
| `tooling/auto_iterate/scripts/` | V7 auto-iterate controller, runtime adapter, CLI |
| `tooling/auto_iterate/scripts/auto_iterate/` | Controller package (state, lock, events, goal, postcondition, recovery) |
| `tooling/auto_iterate/config/templates/` | Controller and account configuration examples |
| `tooling/auto_iterate/docs/` | Goal template, remote control guide |
| `tooling/remote_control/scripts/` | Harness remote wrapper and patched `cc-connect` build helper |
| `tooling/remote_control/config/templates/` | Remote control / Feishu / Codex config templates |
| `tooling/remote_control/` docs | Local build, Feishu setup, and remote control usage notes |
| `media/` | Harness-level branding and documentation assets used by root docs |
| `tests/` | Controller test suite and fixtures |

## Workflow Stages

```
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline)
→ WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
```

The core iteration loop (WF8) follows four stages per round:

```
plan (hypothesis) → code (implement) → run (train + metrics) → eval (decision)
```

Decision vocabulary: **NEXT_ROUND** (loop), **DEBUG** (fix + loop), **CONTINUE** (advance to WF9), **PIVOT** (roll back to WF2), **ABORT** (terminate).

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
- `PROJECT_STATE.json`
- `iteration_log.json`
- `project_map.json`
- `src/`, `scripts/`, `configs/`, `docs/`, `tests/`
- `docs/auto_iterate_goal.md`
- `docs/iterations/**`
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

## Bootstrap

### 1. Put the harness worktree at the project root

Preferred flow:

```bash
mkdir /path/to/my-project
cd /path/to/my-project
git clone <harness-repo-url> .
mv .git .harness
```

If the harness repo was cloned into a subdirectory instead:

```bash
cd /path/to/my-project
CLONE_DIR="Harness-Research"

rsync -a "$CLONE_DIR"/ ./ --exclude .git
mv "$CLONE_DIR/.git" .harness
rm -rf "$CLONE_DIR"
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

## 5. Create project directories

```bash
mkdir -p src scripts configs baselines experiments docs docs/iterations tests
mkdir -p .claude/iterations
mkdir -p .agents/state/iterations
```

Do not create `.auto_iterate/` by hand. It is controller-owned runtime state
and should appear only after the first auto-iterate `start`.

## 6. Bootstrap auto-iterate project files

The harness repo owns the controller code, remote-control wrapper, and reusable
templates. The project should create one research goal file plus local
controller/account YAMLs.

```bash
[ ! -f docs/auto_iterate_goal.md ] && cp tooling/auto_iterate/docs/auto_iterate_goal_template.md docs/auto_iterate_goal.md
[ ! -f tooling/auto_iterate/config/controller.local.yaml ] && cp tooling/auto_iterate/config/templates/auto_iterate_controller.example.yaml tooling/auto_iterate/config/controller.local.yaml
[ ! -f tooling/auto_iterate/config/accounts.local.yaml ] && cp tooling/auto_iterate/config/templates/auto_iterate_accounts.example.yaml tooling/auto_iterate/config/accounts.local.yaml
```

Keep this boundary:

- edit `docs/auto_iterate_goal.md` in the research repo
- edit `tooling/auto_iterate/config/*.local.yaml` as local operator inputs for
  this workspace
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

Keep this boundary:

- edit `tooling/remote_control/config/*.local.*` only for your own machine
- do not commit Feishu credentials, operator IDs, or `CODEX_HOME` values
- do not commit `tooling/remote_control/vendor/go/`
- do not commit built binaries under `tooling/remote_control/vendor/bin/`
- do not use `git add -f` to force-add ignored local config or local binaries

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

See:

- `tooling/remote_control/BUILD_AND_LOCAL_SETUP.zh-CN.md`
- `tooling/remote_control/FEISHU_MVP_SETUP.zh-CN.md`

## 7. Fill in project details

Replace placeholders in `CLAUDE.md` and `AGENTS.md`, or use the workflow init command:

- Claude Code: `/orchestrator init`
- Codex: `$orchestrator init`

## 8. Initial research commit

Commit only research-owned files:

```bash
git add CLAUDE.md AGENTS.md
git add PROJECT_STATE.json project_map.json docs/ configs/ src/ scripts/ tests/ 2>/dev/null || true
git commit -m "init: project scaffold"
```

Do not add harness-owned paths such as `.claude/`, `.agents/`, `tooling/`, `media/`, `README.md`, or `.gitignore`.

## Daily Dual-Repo Management

For the recommended day-2 update flow, conflict handling, and post-pull checks,
see [Harness_Update_Guide.md](Harness_Update_Guide.md).

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
- keep `docs/auto_iterate_goal.md` research-owned; keep
  `tooling/auto_iterate/config/*.local.yaml` as local operator inputs; keep
  `.auto_iterate/` runtime-only and out of git
- use one dedicated `CODEX_HOME` per controller account instead of sharing a
  single Codex home across multiple accounts
- if an auth flow keeps failing on an old `CODEX_HOME`, prefer creating a fresh
  directory over reusing a dirty one
- for current Codex CLI versions, the harness runtime should invoke
  `codex exec --full-auto ...`; the older `--approval-mode full-auto` form is
  not accepted by newer CLIs

Recommended local account layout:

```bash
mkdir -p ~/.codex-acc1 ~/.codex-acc2

CODEX_HOME=~/.codex-acc1 codex login --device-auth
CODEX_HOME=~/.codex-acc1 codex login status

CODEX_HOME=~/.codex-acc2 codex login --device-auth
CODEX_HOME=~/.codex-acc2 codex login status
```

Then point the project account registry at those homes:

```yaml
accounts:
  - id: codex_primary
    codex_home: /home/<user>/.codex-acc1
    enabled: true
    priority: 100
    cooldown_sec: 1800
    tags: [local, primary]

  - id: codex_secondary
    codex_home: /home/<user>/.codex-acc2
    enabled: true
    priority: 90
    cooldown_sec: 1800
    tags: [local, secondary]
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
test -d docs/iterations
```

Expected outcome:

- `hgit status` is clean or only shows intentional framework edits
- `git status` is clean or only shows research files
- `tooling/auto_iterate/**` stays harness-managed
- `tooling/auto_iterate/config/*.local.yaml` exist as local operator inputs
- `.auto_iterate/**` remains runtime-only and uncommitted
