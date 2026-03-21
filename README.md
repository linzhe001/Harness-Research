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
git clone <harness-repo-url> harness-tmp
```

### Step-by-Step Setup

Execute these steps **in order**. Detect which option the user used and follow the corresponding path.

#### Step 1: Arrange files and create `.harness`

**If Option A** (`git clone <url> .` — files are already at project root):

```bash
# .git is currently the harness repo — rename it to .harness
mv .git .harness
```

**If Option B** (`git clone <url> harness-tmp` — files are in a subdirectory):

```bash
# Copy framework files to project root
cp -r harness-tmp/.claude .
cp -r harness-tmp/.agents .
cp -r harness-tmp/.vscode .
cp harness-tmp/CLAUDE.md.template .
cp harness-tmp/AGENTS.md.template .
cp harness-tmp/settings.local.json.template .
cp harness-tmp/README.md .

# Move harness .git to .harness
mv harness-tmp/.git .harness

# Remove the now-empty clone directory
rm -rf harness-tmp
```

**Then, for both options**, configure `.harness`:

```bash
git --git-dir=.harness --work-tree=. config core.bare false
git --git-dir=.harness --work-tree=. config status.showUntrackedFiles no
```

Verify:

```bash
git --git-dir=.harness --work-tree=. status        # should be clean
git --git-dir=.harness --work-tree=. log --oneline  # should show harness commits
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

#### Step 5: Create research `.gitignore`

The research repo must ignore all harness-managed files. Create `.gitignore` with this exact content:

```gitignore
# === Harness framework (managed by hgit) ===
.harness
.claude/
.agents/
.vscode/
*.template
README.md

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
```

#### Step 6: Initial commit for research repo

```bash
git add CLAUDE.md AGENTS.md .gitignore
git commit -m "init: project scaffold"
```

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

Replace `{{placeholders}}` in `CLAUDE.md` with actual project information, or run:
- Claude Code: `/orchestrator init`
- Codex: `$orchestrator init`

### Verification Checklist

After all steps are complete, run these checks:

```bash
# 1. Research repo — should only track project files
git status                # clean
git log --oneline         # shows "init: project scaffold"
git ls-files              # should list: CLAUDE.md, AGENTS.md, .gitignore
                          # should NOT list: .claude/*, .agents/*

# 2. Harness repo — should only track framework files
hgit status               # clean (or use: git --git-dir=.harness --work-tree=. status)
hgit log --oneline        # shows harness framework commits
hgit remote -v            # points to harness-research-loop repo
hgit ls-files | head -5   # should list: .agents/*, .claude/*
                          # should NOT list: CLAUDE.md, AGENTS.md

# 3. No cross-contamination
# Editing src/foo.py → only visible in `git status`, NOT in `hgit status`
# Editing .claude/skills/iterate/SKILL.md → only visible in `hgit status`, NOT in `git status`
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
