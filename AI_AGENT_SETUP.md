# Setup Instructions (for AI Agents)

This guide is for bootstrapping a research project that uses this framework in a
same-worktree dual-repo layout.

## Goal

Set up one directory with two separate git histories:

- harness repo: `.harness`, operated via `hgit`, owns framework files
- research repo: normal `.git`, operated via `git`, owns project files

The two repos share one worktree, but they must not track the same files.

## Ownership Model

### Harness-owned files (`hgit`)

- `.claude/**`
- `.agents/**`
- `*.template`
- `tooling/auto_iterate/**`
- `auto_iterate_v7_plan/**`
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
- `configs/auto_iterate_controller.yaml`
- `configs/auto_iterate_accounts.yaml`

### Runtime-only files (never commit)

- `.auto_iterate/**`
- `.pytest_cache/**`
- `wandb/**`
- checkpoints and other generated binary artifacts

## Important Rule About Ignore Files

Do not try to maintain two different root `.gitignore` files.

In same-worktree dual-repo mode:

- the root `.gitignore` is harness-owned and exists to keep research files out of `hgit`
- the research repo should hide harness-owned files via `.git/info/exclude`

That split matters now that the harness repo also ships `tooling/auto_iterate/**`
and `auto_iterate_v7_plan/**`.

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
auto_iterate_v7_plan/
README.md
.gitignore
*.template
settings.local.json.template
EOF
```

Notes:

- keep project-specific overview docs under `docs/` instead of replacing the harness root `README.md`
- if the project needs shared ignore rules for its own generated files, prefer subdirectory `.gitignore` files inside research-owned paths such as `experiments/` or `data/`

## 5. Create project directories

```bash
mkdir -p src scripts configs baselines experiments docs docs/iterations tests
mkdir -p .claude/iterations
mkdir -p .agents/state/iterations
```

## 6. Bootstrap auto-iterate project files

The harness repo owns the controller code and example configs. The research repo
should own the actual project copies.

```bash
[ ! -f docs/auto_iterate_goal.md ] && cp tooling/auto_iterate/docs/auto_iterate_goal_template.md docs/auto_iterate_goal.md
[ ! -f configs/auto_iterate_controller.yaml ] && cp tooling/auto_iterate/config/auto_iterate_controller.example.yaml configs/auto_iterate_controller.yaml
[ ! -f configs/auto_iterate_accounts.yaml ] && cp tooling/auto_iterate/config/auto_iterate_accounts.example.yaml configs/auto_iterate_accounts.yaml
```

Keep this boundary:

- edit `docs/auto_iterate_goal.md` in the research repo
- edit `configs/auto_iterate_*.yaml` in the research repo
- do not edit example files under `tooling/auto_iterate/config/`
- do not commit `.auto_iterate/`

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

Do not add harness-owned paths such as `.claude/`, `.agents/`, `tooling/`, `README.md`, or `.gitignore`.

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
  --config configs/auto_iterate_controller.yaml \
  --accounts configs/auto_iterate_accounts.yaml
```

If you need to point the controller at a different workspace for testing, use
the Python CLI directly:

```bash
python3 tooling/auto_iterate/scripts/auto_iterate_ctl.py \
  --workspace-root /path/to/other-workspace \
  status --json
```

## Verification

Run these checks after bootstrap:

```bash
# Harness repo should see framework files only.
git --git-dir=.harness --work-tree=. status

# Research repo should not list harness-owned files as untracked.
git status

# Research repo should ignore harness-owned paths.
git check-ignore -v .claude/ .agents/ tooling/ auto_iterate_v7_plan/ README.md .gitignore

# Auto-iterate project inputs should be research-owned files.
test -f docs/auto_iterate_goal.md
test -f configs/auto_iterate_controller.yaml
test -f configs/auto_iterate_accounts.yaml
```

Expected outcome:

- `hgit status` is clean or only shows intentional framework edits
- `git status` is clean or only shows research files
- `tooling/auto_iterate/**` stays harness-managed
- `.auto_iterate/**` remains runtime-only and uncommitted
