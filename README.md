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
| `bootstrap.sh` | Automated setup script |

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

### Prerequisites

The user should have already run:

```bash
cd /path/to/my-research-project
git clone <harness-repo-url> harness-tmp
```

Or the harness files are already present in a subdirectory.

### Step-by-Step Setup

Execute these steps **in order**. Each step includes verification.

#### Step 1: Move framework files to project root

If the harness repo was cloned into a subdirectory (e.g., `harness-tmp/`):

```bash
# Move all framework files to the project root
# IMPORTANT: Move hidden dirs (.claude, .agents, .vscode) and all top-level files
cp -r harness-tmp/.claude .
cp -r harness-tmp/.agents .
cp -r harness-tmp/.vscode .
cp harness-tmp/CLAUDE.md.template .
cp harness-tmp/AGENTS.md.template .
cp harness-tmp/settings.local.json.template .
cp harness-tmp/bootstrap.sh .
cp harness-tmp/README.md .
chmod +x bootstrap.sh
```

#### Step 2: Convert harness clone to bare repo at `.harness`

```bash
# Convert the cloned .git to a bare repo for harness tracking
mv harness-tmp/.git .harness

# Remove the now-empty clone directory
rm -rf harness-tmp

# Configure the bare repo
git --git-dir=.harness --work-tree=. config core.bare false
git --git-dir=.harness --work-tree=. config status.showUntrackedFiles no

# Verify: should show framework files as tracked, clean status
git --git-dir=.harness --work-tree=. status
git --git-dir=.harness --work-tree=. log --oneline
```

#### Step 3: Run bootstrap

```bash
bash bootstrap.sh
```

This will:
- Copy `CLAUDE.md.template` → `CLAUDE.md` (if not exists)
- Copy `AGENTS.md.template` → `AGENTS.md` (if not exists)
- Copy `settings.local.json.template` → `.claude/settings.local.json` (if not exists)
- Create project directories: `src/`, `scripts/`, `configs/`, `baselines/`, `experiments/`, `docs/`, `tests/`
- Initialize research `.git` repo
- Generate `.gitignore` for the research repo (excludes harness files)

#### Step 4: Configure research repo

```bash
# Set the research project's remote (user provides the URL)
git remote add origin <research-repo-url>

# Initial commit for research repo
git add CLAUDE.md AGENTS.md .gitignore
git commit -m "init: project scaffold"
```

#### Step 5: Set up shell alias

Add to user's `~/.bashrc` or `~/.zshrc`:

```bash
alias hgit='git --git-dir=.harness --work-tree=.'
```

#### Step 6: Fill in project details

Either manually replace `{{placeholders}}` in `CLAUDE.md`, or run:
- Claude Code: `/orchestrator init`
- Codex: `$orchestrator init`

### Verification Checklist

After setup, confirm:

```bash
# Research repo: tracks project files only
git status                # clean, .gitignore present
git log --oneline         # has initial commit

# Harness repo: tracks framework files only
hgit status               # clean
hgit log --oneline        # has framework commits
hgit remote -v            # points to harness-research-loop repo

# No cross-contamination
git ls-files | head -5    # should show CLAUDE.md, AGENTS.md, .gitignore — NOT .claude/
hgit ls-files | head -5   # should show .agents/*, .claude/* — NOT CLAUDE.md
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
# Framework files (.claude/skills/*, .agents/*) are updated
# CLAUDE.md (research-specific) is untouched
```

If `CLAUDE.md.template` has new sections, manually diff and merge:

```bash
diff CLAUDE.md.template CLAUDE.md
```

---

## File Ownership Summary

| File | Tracked by | Purpose |
|------|-----------|---------|
| `.claude/skills/**` | harness (hgit) | Skill definitions |
| `.claude/rules/**` | harness (hgit) | Auto-triggered rules |
| `.agents/skills/**` | harness (hgit) | Codex agent definitions |
| `.agents/references/**` | harness (hgit) | Shared constraints |
| `*.template` | harness (hgit) | Project templates |
| `bootstrap.sh` | harness (hgit) | Setup automation |
| `README.md` | harness (hgit) | This file |
| `.gitignore` (harness) | harness (hgit) | Excludes research files |
| `CLAUDE.md` | research (git) | Project-specific config |
| `AGENTS.md` | research (git) | Project-specific config |
| `src/`, `scripts/`, etc. | research (git) | Research code |
| `PROJECT_STATE.json` | research (git) | Workflow state |
| `.gitignore` (research) | research (git) | Excludes harness files |
