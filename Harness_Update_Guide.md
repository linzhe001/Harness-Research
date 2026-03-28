# Harness Update Guide

## Purpose

This guide explains the day-2 pull and push workflow for Harness Research in a
same-worktree dual-repo project.

## Related Framework Docs

For remote-control and Feishu specific operator docs, also see:

- [tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md](./tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md)

For full framework bootstrap, see:

- [AI_AGENT_SETUP.md](./AI_AGENT_SETUP.md)

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
- `tooling/remote_control/**`
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

Remote-control local files follow the same pattern:

- commit templates under `tooling/remote_control/config/templates/`
- keep `tooling/remote_control/config/*.local.*` local-only
- do not commit `tooling/remote_control/vendor/go/`
- do not commit built binaries under `tooling/remote_control/vendor/bin/`

## Daily Pull Workflow

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

## Daily Push Workflow

When you intentionally changed harness-owned files, stay on the harness git
history for the whole cycle:

```bash
hgit status --short
hgit pull --ff-only origin "$(hgit branch --show-current)"
hgit add <harness paths>
hgit commit -m "..."
hgit push origin "$(hgit branch --show-current)"
```

If the remote branch moved after your local commit, rebase the harness branch
before pushing:

```bash
hgit pull --rebase origin "$(hgit branch --show-current)"
hgit push origin "$(hgit branch --show-current)"
```

Do not use normal `git push` for harness-owned files.

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
- `tooling/auto_iterate/**`
- `tooling/remote_control/**`

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
diff tooling/auto_iterate/config/templates/auto_iterate_controller.example.yaml tooling/auto_iterate/config/controller.local.yaml
diff tooling/auto_iterate/config/templates/auto_iterate_accounts.example.yaml tooling/auto_iterate/config/accounts.local.yaml
```

If you use remote control / Feishu integration, also check:

```bash
diff tooling/remote_control/config/templates/remote_control.example.yaml tooling/remote_control/config/remote_control.local.yaml || true
diff tooling/remote_control/config/templates/cc_connect.local.example.toml tooling/remote_control/config/cc_connect.local.toml || true
```

When templates add new sections or fields, merge them manually into the
project goal file or local operator YAMLs. If your repo versions
`controller.local.yaml` / `accounts.local.yaml` as shared defaults, update
those tracked files in place. For remote control, merge new template fields
into your local `.local` files manually, but do not commit secrets or
machine-specific values.

### 3b. Rebuild patched `cc-connect` if needed

If your harness pull changed either of these:

- `tooling/remote_control/cc_connect_src/**`
- `tooling/remote_control/scripts/build_patched_cc_connect.sh`

rebuild the local binary before using Feishu again:

```bash
tooling/remote_control/scripts/build_patched_cc_connect.sh
```

The resulting local binary belongs under `tooling/remote_control/vendor/bin/`
and should stay out of Git history.

### 3b.1 Reinstall local remote-control commands if needed

If your harness pull changed either of these:

- `tooling/remote_control/bin/**`
- `tooling/remote_control/scripts/install_user_commands.sh`

rerun the local command installer:

```bash
tooling/remote_control/scripts/install_user_commands.sh --shell-init
```

This refreshes the user-local command shims such as:

- `codex_all`
- `cw`

If you do not want the installer to manage `~/.profile` / `~/.bashrc`, you can
rerun it without `--shell-init`.

### 3c. Recheck live `cc-connect` workspace assumptions

If you use Feishu / remote control, also verify the live local config still
matches the current workspace after the pull:

- for a single local repo, prefer single-workspace config with `projects.agent.options.work_dir = "$(pwd)"` and no `mode` / `base_dir`
- in `multi-workspace` mode, `base_dir` should be the parent directory of the workspace, not the workspace root itself
- custom commands such as `/ai` and `/home` may still set `work_dir` to the concrete workspace root
- direct natural-language chat still depends on channel-to-workspace binding

Recommended quick check:

```bash
CURRENT_WORKSPACE="$(pwd)"
WORKSPACE_NAME="$(basename "$CURRENT_WORKSPACE")"
WORKSPACE_PARENT="$(dirname "$CURRENT_WORKSPACE")"

rg -n 'name = |mode = |base_dir = |work_dir = ' tooling/remote_control/config/cc_connect.local.toml
tooling/remote_control/bin/cc-connect -version
```

If you changed `cc_connect.local.toml`, restart `cc-connect` before testing in
Feishu. If the bot still says no workspace is bound, run `/workspace bind
<workspace-name>` in that channel.

If you are editing an existing local config rather than creating a fresh one
from the template, follow the in-place migration checklist in
[`tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md`](./tooling/remote_control/REMOTE_CONTROL_GUIDE.zh-CN.md)
section `1.4`.

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
/*.template
```

If local remote-control files appear in `git status`, do not add them. These
paths should remain local-only:

```gitignore
/tooling/remote_control/config/*.local.toml
/tooling/remote_control/config/*.local.yaml
/tooling/remote_control/vendor/go/
/tooling/remote_control/vendor/bin/cc-connect*
```

Do not use `git add -f` on those paths. If you are unsure whether local
protection still works after a pull, verify it explicitly:

```bash
git check-ignore -v tooling/remote_control/config/cc_connect.local.toml
git check-ignore -v tooling/remote_control/config/remote_control.local.yaml
git status --short --ignored tooling/remote_control/config tooling/remote_control/vendor
```

### `build_patched_cc_connect.sh` fails because `go` is missing

The remote-control tree expects Go 1.25. The build helper already prefers a
local toolchain at:

```text
tooling/remote_control/vendor/go/bin/go
```

If `go` is not on `PATH`, unpack a Go 1.25 tarball into
`tooling/remote_control/vendor/go/` and rerun:

```bash
tooling/remote_control/scripts/build_patched_cc_connect.sh
```

This keeps the toolchain local to the harness tree and avoids depending on a
system-wide Go install.

### Bot replies `No workspace found for this channel`

This usually means one of these is true:

- you actually wanted single-workspace mode, but the config is still using `multi-workspace`
- the channel was never bound to a workspace
- `base_dir` points at the wrong parent directory
- `projects.name` changed, so old bindings are stored under a stale project key
- you updated `cc_connect.local.toml` but did not restart `cc-connect`

Remember:

- for one repo, the simplest fix is to remove `mode` / `base_dir` and set `projects.agent.options.work_dir` to the current workspace root
- `base_dir` is the parent directory that contains workspaces
- `work_dir` on `/ai` or `/home` only affects those custom commands
- direct natural-language chat still resolves workspace from channel binding

Recommended recovery:

```bash
CURRENT_WORKSPACE="$(pwd)"
WORKSPACE_NAME="$(basename "$CURRENT_WORKSPACE")"
WORKSPACE_PARENT="$(dirname "$CURRENT_WORKSPACE")"

rg -n 'name = |mode = |base_dir = |work_dir = ' tooling/remote_control/config/cc_connect.local.toml
tooling/remote_control/bin/cc-connect -version
```

Then in Feishu:

```bash
/workspace
/workspace bind <workspace-name>
```

If bindings still look wrong after a rename or config rewrite, inspect:

```bash
sed -n '1,200p' ~/.cc-connect/workspace_bindings.json
```

Bindings are keyed by `project:<name>`, so changing `[[projects]].name`
requires rebinding channels for the new project key.

## Summary

Use `git` for research files and `hgit` for framework files.

After every harness pull:

1. verify `hgit status`
2. read updated framework docs
3. diff templates against project-owned files
4. verify normal `git status` is still clean with respect to harness paths
5. rebuild patched `cc-connect` if remote-control source changed
6. restart `cc-connect` and re-check workspace binding if remote-control config changed

After every harness push:

1. verify `hgit status`
2. confirm you committed only harness-owned paths
3. push with `hgit`, not normal `git`
