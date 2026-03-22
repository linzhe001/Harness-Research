# Harness Research Loop

A structured 10-stage research workflow framework for CV/ML projects, designed to work with **Claude Code** and **Codex** as AI research assistants.

## What This Is

This repo contains the **framework only** — skills, rules, templates, and workflow definitions. It does **not** contain any research code. Each research project has its own separate git repo; this framework is layered on top via a dual-repo setup.

### Framework Contents

| Path | Purpose |
|------|---------|
| `.claude/skills/` | Claude Code skill definitions (18 skills) |
| `.claude/rules/` | Auto-triggered rules (pre-training, project-map, deps-update) |
| `.claude/shared/` | Shared references (code style) |
| `.claude/Workflow_Guide.md` | Full workflow documentation for Claude Code |
| `.agents/skills/` | Codex agent skill definitions (18 skills) |
| `.agents/references/` | Shared behavior constraints for Codex |
| `CLAUDE.md.template` | Project CLAUDE.md template with `{{placeholders}}` |
| `AGENTS.md.template` | Project AGENTS.md template with `{{placeholders}}` |
| `settings.local.json.template` | Claude Code permissions template |

### Workflow Stages

```
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline)
→ WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
```

---

## Setup Instructions (for AI Agents)

> **Context**: The user has cloned this repo into their research project directory.
> The goal is to establish a **dual-repo** structure where:
> - **Harness repo** (`.harness`, bare) tracks framework files — updated via `hgit`
> - **Research repo** (`.git`, normal) tracks project code — updated via `git`
>
> Both repos coexist in the **same directory**. They track different files and never conflict.

### Prerequisites

The user should have already run one of:

```bash
# Option A (recommended): Clone directly into an EMPTY project directory
mkdir /path/to/my-research-project && cd /path/to/my-research-project
git clone <harness-repo-url> .
```

```bash
# Option B: Clone into a subdirectory (if project dir is not empty)
cd /path/to/my-research-project
git clone <harness-repo-url> <clone-dir>
# <clone-dir> can be any name: harness-tmp, Harness-Research, etc.
```

### Detecting Which Option Was Used

Before starting setup, determine the clone method:

```bash
# If .claude/ and .agents/ exist at project root AND .git/ exists → Option A
# If a subdirectory contains .claude/, .agents/, and .git/ → Option B
#   Identify the clone directory name (e.g., harness-tmp, Harness-Research)
```

### Step-by-Step Setup

Execute these steps **in order**.

#### Step 1: Arrange files and create `.harness`

**If Option A** (`git clone <url> .` — files are already at project root):

```bash
# .git is currently the harness repo — rename it to .harness
mv .git .harness
```

**If Option B** (clone is in a subdirectory — replace `$CLONE_DIR` with the actual name):

```bash
CLONE_DIR="harness-tmp"  # ← set to actual clone directory name

# Copy framework files to project root
cp -r "$CLONE_DIR/.claude" .
cp -r "$CLONE_DIR/.agents" .
cp "$CLONE_DIR/CLAUDE.md.template" .
cp "$CLONE_DIR/AGENTS.md.template" .
cp "$CLONE_DIR/settings.local.json.template" .
cp "$CLONE_DIR/README.md" .

# Move harness .git to .harness
mv "$CLONE_DIR/.git" .harness

# ⚠️ CRITICAL: Remove the clone directory — it is now dead weight
rm -rf "$CLONE_DIR"
```

> **Warning**: The clone directory MUST be deleted after extracting `.harness`. If it remains, it wastes disk space with duplicate files and confuses project structure.
>
> **If `rm -rf` fails due to insufficient permissions**: Do NOT silently skip this step. Ask the user for permission to delete the directory, explaining that it contains only duplicate framework files and is safe to remove. Never proceed to the next step with the clone directory still present.

**Then, for both options**, configure `.harness`:

```bash
git --git-dir=.harness --work-tree=. config core.bare false
git --git-dir=.harness --work-tree=. config status.showUntrackedFiles no
```

**Verify Step 1 is complete:**

```bash
# .harness exists and works
git --git-dir=.harness --work-tree=. status        # should be clean
git --git-dir=.harness --work-tree=. log --oneline  # should show harness commits

# Clone directory is gone (Option B only)
# If this directory still exists, delete it now: rm -rf <clone-dir>
ls -d harness-tmp Harness-Research 2>/dev/null && echo "ERROR: clone dir not cleaned up!" || echo "OK: no leftover clone dir"
```

#### Step 2: Generate project files from templates

Copy each template to its actual filename. **Only copy if the target does not already exist** (never overwrite existing project files):

```bash
# CLAUDE.md — project configuration (will be filled with project details later)
[ ! -f CLAUDE.md ] && cp CLAUDE.md.template CLAUDE.md

# AGENTS.md — Codex agent configuration
[ ! -f AGENTS.md ] && cp AGENTS.md.template AGENTS.md

# .claude/settings.local.json — Claude Code permissions
[ ! -f .claude/settings.local.json ] && cp settings.local.json.template .claude/settings.local.json
```

#### Step 3: Create project directory structure

```bash
mkdir -p src scripts configs baselines experiments docs docs/iterations tests
mkdir -p .claude/iterations
mkdir -p .agents/state/iterations
```

#### Step 4: Initialize research repo

```bash
git init
```

#### Step 4.5: Handle pre-existing files (if any)

If the project directory already contains files from a previous project or data downloads, decide how to handle them **before** creating `.gitignore`:

- **Data directories** (datasets, large binaries): Add to `.gitignore` under a `# === Project-specific ignores ===` section
- **Previous code/docs**: Move to a clearly named directory (e.g., `legacy/`) and add to `.gitignore`, or incorporate into the new project structure
- **Do not** leave orphan directories unaccounted for — every non-framework directory should be either tracked by git or explicitly ignored

#### Step 5: Create research `.gitignore`

The research repo must ignore all harness-managed files. Create `.gitignore` with this exact content:

```gitignore
# === Harness framework (managed by hgit) ===
.harness
.claude/
.agents/
.vscode/
*.template

# === Build / Runtime ===
__pycache__/
*.pyc
*.egg-info/
*.so
build/
dist/

# === Experiments (large binary files) ===
experiments/checkpoints/
*.ckpt
*.pth
*.pt
wandb/

# === System ===
.DS_Store
*.swp
*~

# === Project-specific ignores ===
# Add any pre-existing directories or files that should not be tracked here
```

> **Important**: Do **not** ignore `README.md` in the research repo. The bootstrap `README.md` copied from Harness is removed in Step 9, and the project will typically create its own `README.md` later. That project README should be tracked by normal `git`, not ignored.

#### Step 6: Initial commit for research repo

```bash
git add CLAUDE.md AGENTS.md .gitignore
git add PROJECT_STATE.json project_map.json docs/ scripts/ configs/ src/ tests/ 2>/dev/null || true
git commit -m "init: project scaffold"
```

If stable scaffold files already exist when bootstrap happens, they should be tracked in the same initial commit instead of being left as long-lived untracked files.

After bootstrap, whenever the workflow creates new stable project files, add them to the research repo promptly. In practice, this usually means:

```bash
git add PROJECT_STATE.json project_map.json docs/ scripts/ configs/ src/ tests/
```

Do not leave canonical state files, stable docs, or stable scripts/configs untracked just because they were generated after the first commit.

If the user has a remote URL for the research repo:

```bash
git remote add origin <research-repo-url>
```

#### Step 7: Set up `hgit` shell alias

Check if the alias already exists. If not, add it to the user's shell config:

```bash
# Add to ~/.bashrc or ~/.zshrc:
alias hgit='git --git-dir=.harness --work-tree=.'
```

Remind the user to run `source ~/.bashrc` (or restart the shell) for the alias to take effect.

#### Step 8: Fill in project details

Replace `{{placeholders}}` in `CLAUDE.md` and `AGENTS.md` with actual project information.

**Placeholders to fill** (gather this info from the user before starting):

| Placeholder | Where |
|-------------|-------|
| `{{PROJECT_NAME}}` | CLAUDE.md, AGENTS.md |
| `{{PROJECT_DESCRIPTION}}` | CLAUDE.md, AGENTS.md |
| `{{ENV_NAME}}` | CLAUDE.md |
| `{{PYTHON_VERSION}}` | CLAUDE.md |
| `{{TORCH_VERSION}}` | CLAUDE.md |
| `{{CUDA_VERSION}}` | CLAUDE.md |
| `{{GPU_INFO}}` | CLAUDE.md |
| `{{COMPETITION_URL}}` | CLAUDE.md |
| `{{DATASET_PAPER_URL}}` | CLAUDE.md |
| `{{BASELINE_CODE_URL}}` | CLAUDE.md |
| `{{METRICS}}` | CLAUDE.md |
| `{{DATA_FORMAT}}` | CLAUDE.md |
| `{{DEADLINE}}` | CLAUDE.md |

Alternatively, run an interactive fill:
- Claude Code: `/orchestrator init`
- Codex: `$orchestrator init`

#### Step 9: Remove bootstrap-only README/template copies

After initialization is complete and the real project files are in place, the copied bootstrap refs are no longer needed in the worktree:

```bash
rm -f README.md CLAUDE.md.template AGENTS.md.template settings.local.json.template
```

This avoids confusing the Harness setup README with the research project's own README.

When the project later creates its own `README.md`, that new file belongs to the research repo and should be tracked by normal `git`.

These files remain available in `.harness` and can be inspected at any time:

```bash
hgit show HEAD:README.md
hgit show HEAD:CLAUDE.md.template
hgit show HEAD:AGENTS.md.template
hgit show HEAD:settings.local.json.template
```

### Verification Checklist

After all steps are complete, run **every** check below. Do not skip any.

```bash
# 1. No leftover clone directory
ls -d harness-tmp Harness-Research 2>/dev/null && echo "FAIL: clone dir exists" || echo "PASS"

# 2. Research repo — should only track project files
git status                # clean
git log --oneline         # shows "init: project scaffold"
git ls-files              # should at minimum list: CLAUDE.md, AGENTS.md, .gitignore
                          # should also list stable scaffold files when present:
                          # PROJECT_STATE.json, project_map.json, docs/, scripts/, configs/, src/, tests/
                          # should NOT list: .claude/*, .agents/*

# 3. Harness repo — should only track framework files
hgit status               # clean (or use: git --git-dir=.harness --work-tree=. status)
hgit log --oneline        # shows harness framework commits
hgit remote -v            # points to harness-research-loop repo
hgit ls-files | head -5   # should list: .agents/*, .claude/*
                          # should NOT list: CLAUDE.md, AGENTS.md

# 4. No cross-contamination
# Editing src/foo.py → only visible in `git status`, NOT in `hgit status`
# Editing .claude/skills/iterate/SKILL.md → only visible in `hgit status`, NOT in `git status`

# 5. CLAUDE.md has no remaining placeholders
grep -c '{{' CLAUDE.md && echo "FAIL: unfilled placeholders" || echo "PASS"

# 6. hgit alias works
type hgit &>/dev/null && echo "PASS" || echo "FAIL: hgit alias not set"
```

---

## Daily Usage

```bash
# Research code changes → normal git
git add src/models/my_model.py
git commit -m "train(research): add depth-guided loss"
git push

# Harness framework updates → hgit
hgit pull origin main                    # pull framework updates
hgit add .claude/skills/iterate/SKILL.md # or push local improvements
hgit commit -m "feat: add ablation sub-command"
hgit push origin main
```

## Updating Framework in Existing Projects

```bash
cd /path/to/existing-project
hgit pull origin main
# Framework files (.claude/skills/*, .agents/*) are updated automatically
# CLAUDE.md (research-specific) is untouched — harness repo does not track it
```

If `CLAUDE.md.template` has new sections you want to adopt:

```bash
diff CLAUDE.md.template CLAUDE.md
# Manually merge relevant new sections into your project's CLAUDE.md
```

---

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
| `README.md` | harness (`hgit`) | This file |
| `.gitignore` (harness) | harness (`hgit`) | Excludes research files from harness |
| `CLAUDE.md` | research (`git`) | Project-specific config |
| `AGENTS.md` | research (`git`) | Project-specific config |
| `.gitignore` (research) | research (`git`) | Excludes harness files from research |
| `src/`, `scripts/`, `configs/` | research (`git`) | Research code |
| `PROJECT_STATE.json` | research (`git`) | Workflow stage state |
| `iteration_log.json` | research (`git`) | Experiment history |
| `project_map.json` | research (`git`) | Code architecture map |
