# Harness Update Guide

## Purpose

This guide explains how to pull the latest Harness Research updates in a
same-worktree dual-repo project.

In this layout:

- the harness repo lives in `.harness`
- the research repo lives in the normal `.git`
- both repos share the same project root as one worktree

That means framework files can appear at the project root while still belonging
to the harness repo.

## What Is Harness-Owned

When you update harness, the following paths are framework files managed by
`hgit`:

- `.claude/**`
- `.agents/**`
- `*.template`
- `tooling/auto_iterate/**`
- `auto_iterate_v7_plan/**`
- `README.md`
- `AI_AGENT_SETUP.md`
- `Harness_Update_Guide.md`
- the root `.gitignore`

Do not add these files to the research repo.

## Ignore Rules In Dual-Repo Mode

There is only one root `.gitignore` at the shared project root, and it is
harness-owned.

The research repo should not maintain a second competing root `.gitignore` for
framework files. Instead:

- use `.git/info/exclude` to hide harness-owned paths from the research repo
- use subdirectory `.gitignore` files only inside research-owned paths when the
  project needs shared ignore rules for its own generated files

Examples:

- good: `experiments/.gitignore`
- good: `data/.gitignore`
- avoid: editing the root `.gitignore` for research-only ignore rules

## Pull Workflow

### Preferred command

If you have the alias:

```bash
hgit pull --ff-only origin "$(hgit branch --show-current)"
```

If you do not:

```bash
BRANCH=$(git --git-dir=.harness --work-tree=. branch --show-current)
git --git-dir=.harness --work-tree=. pull --ff-only origin "$BRANCH"
```

If your harness branch is known to be `master`, this is enough:

```bash
git --git-dir=.harness --work-tree=. pull --ff-only origin master
```

### Recommended wrapper

If the project provides a wrapper script, use it:

```bash
scripts/update_harness.sh
```

That script should check that the harness worktree is clean before pulling.

## Before Pulling

Always inspect harness state first:

```bash
hgit status --short
```

If it is not clean, resolve that before `pull`.

Typical blocking files are:

- `README.md`
- `AI_AGENT_SETUP.md`
- root `.gitignore`
- `.claude/**`
- `.agents/**`

## After Pulling

### 1. Confirm harness is clean

```bash
hgit status --short
```

Expected result: empty output.

### 2. Treat updated root docs as framework docs

If any of these changed:

- `README.md`
- `AI_AGENT_SETUP.md`
- `Harness_Update_Guide.md`

read them as framework updates. Do not commit them into the research repo.

### 3. Compare templates with project-owned files

Harness updates do not automatically merge your project-specific files.

Check at least:

```bash
diff CLAUDE.md.template CLAUDE.md
diff AGENTS.md.template AGENTS.md
diff tooling/auto_iterate/docs/auto_iterate_goal_template.md docs/auto_iterate_goal.md
diff tooling/auto_iterate/config/auto_iterate_controller.example.yaml configs/auto_iterate_controller.yaml
diff tooling/auto_iterate/config/auto_iterate_accounts.example.yaml configs/auto_iterate_accounts.yaml
```

When templates add new sections or fields, merge them manually into the
research-owned files.

### 4. Check the research repo separately

```bash
git status --short
```

Harness-owned files should not show up there as files to add. If they do, hide
them via `.git/info/exclude` in the research repo instead of tracking them.

## Common Problems

### `hgit pull` says local changes would be overwritten

Inspect both staged and unstaged harness state:

```bash
git --git-dir=.harness --work-tree=. diff -- README.md AI_AGENT_SETUP.md Harness_Update_Guide.md .gitignore .claude .agents
git --git-dir=.harness --work-tree=. diff --cached -- README.md AI_AGENT_SETUP.md Harness_Update_Guide.md .gitignore .claude .agents
```

If those are just stale local harness changes, restore them to harness `HEAD`
before retrying:

```bash
git --git-dir=.harness --work-tree=. restore \
  --staged --worktree --source=HEAD --ignore-skip-worktree-bits \
  README.md AI_AGENT_SETUP.md Harness_Update_Guide.md .gitignore .claude .agents
```

Then run the pull again.

### Harness files appear in normal `git status`

Do not `git add` them to the research repo.

Instead, add harness-managed paths to `.git/info/exclude`, for example:

```gitignore
/.harness/
/.claude/
/.agents/
/README.md
/AI_AGENT_SETUP.md
/Harness_Update_Guide.md
/.gitignore
/tooling/
/auto_iterate_v7_plan/
/*.template
```

## Summary

Use `git` for research files and `hgit` for framework files.

After every harness pull:

1. verify `hgit status`
2. read updated framework docs
3. diff templates against project-owned files
4. verify normal `git status` is still clean with respect to harness paths
