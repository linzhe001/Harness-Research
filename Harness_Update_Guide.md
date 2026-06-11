# Harness Update Guide

## Purpose

This guide explains the day-2 pull and push workflow for Harness Research in a
same-worktree dual-repo project.

## Related Framework Docs

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
- `.agents/**`, except ignored local state under `.agents/state/**`
- `*.template`
- `templates/**`
- `schemas/**`
- `workflow_handbook/**`
- `tooling/codex_hooks/**`
- `tooling/evidence/**`
- `tooling/auto_iterate/**`
- `tooling/workflow_supervisor/**`
- `tooling/model_api/**`
- `tooling/.tests/**`
- `README.md`
- `AI_AGENT_SETUP.md`
- `Harness_Update_Guide.md`

Do not add these files to the research repo.

## Ignore Rules In Dual-Repo Mode

There is only one root `.gitignore` at the shared project root, and both git
histories read it. In a dual-repo target workspace, keep that file
research-owned or limited to rules that are safe for both histories. Do not
copy the framework source `.gitignore` into a target workspace just to hide
Harness paths.

Use per-repo exclude files for ownership hiding:

- use `.git/info/exclude` to hide harness-owned paths from the research repo
- use `.harness/info/exclude` to hide research-owned paths from the harness repo
- use subdirectory `.gitignore` files inside research-owned paths when the
  project needs shared ignore rules for generated research files

Examples:

- good: `experiments/.gitignore`
- good: `data/.gitignore`
- good: root `.gitignore` rules for ordinary runtime outputs such as
  `.auto_iterate/`, `.workflow_supervisor/`, `.harness_hooks/`,
  `.agents/state/workflow_supervisor_worker_results/`, and `__pycache__/`
- avoid: root `.gitignore` rules whose only purpose is to hide framework files
  from the research repo or research files from the harness repo

Workflow supervisor worker handoffs are local runtime state:

- keep `.agents/state/workflow_supervisor_worker_results/**` out of both git
  histories
- do not manually edit `.workflow_supervisor/**`; use
  `tooling/workflow_supervisor/scripts/workflow_ctl.sh`

If normal `git status --untracked-files=all` suddenly stops showing research
files such as `CLAUDE.md`, `AGENTS.md`, `docs/`, or `src/`, the root
`.gitignore` is hiding too much. Move those research-side hide rules into
`.harness/info/exclude`.

## Daily Pull Workflow

### Safe current-pull flow

Run from the target research workspace root, not from the framework source
checkout. Normal `git` is the research repo; `hgit` is the Harness repo stored
in `.harness`.

If `hgit` is not defined in the shell, define it for the current session:

```bash
alias hgit='git --git-dir=.harness --work-tree=.'
```

Then update the Harness framework with a fast-forward pull:

```bash
test -d .harness
hgit remote -v
hgit status --short
hgit fetch origin
hgit pull --ff-only origin "$(hgit branch --show-current)"
hgit status --short
```

Expected result after the final status command: empty output.

If `hgit remote -v` does not point at the Harness Research remote, fix the
Harness remote before pulling. Do not use the research repo remote for Harness:

```bash
hgit remote set-url origin https://github.com/linzhe001/Harness-Research.git
```

Use a branch name explicitly when the target workspace pins Harness to a known
branch:

```bash
hgit pull --ff-only origin master
```

Do not run normal `git pull` to update Harness framework files. Normal `git`
updates the research repo only.

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

When you intentionally change harness-owned files, stay on the harness git
history for the whole cycle. Start from a clean, current Harness branch before
editing:

```bash
hgit status --short
hgit pull --ff-only origin "$(hgit branch --show-current)"
```

After editing, inspect the diff, stage only intentional framework paths, verify
the staged set, then commit and push:

```bash
hgit status --short
hgit diff -- \
  README.md AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
hgit add <harness paths>
hgit diff --cached --name-status
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

### Project-local temporary Harness patches

Some target research workspaces may temporarily modify Harness-owned files while
debugging a project-specific problem, for example an ad hoc dataset scanner in
`tooling/workflow_supervisor/**` or a one-off hook/evidence workaround. Treat
those changes as local patches unless they have been deliberately generalized
for every Harness consumer.

Before any Harness push, always inspect both unstaged and staged Harness
changes:

```bash
hgit status --short
hgit diff -- \
  README.md AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
hgit diff --cached -- \
  README.md AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
```

If the diff contains project-specific logic, local paths, dataset names,
experiment assumptions, or temporary recovery code, do not commit it to
Harness-Research. Save it outside the repo if it may be useful later. If the
same worktree also contains intentional framework edits, split the changes first
and restore only the temporary paths:

```bash
hgit diff -- \
  <temporary-harness-paths> \
  > /tmp/project_local_harness_patch.diff

hgit restore \
  --staged --worktree --source=HEAD --ignore-skip-worktree-bits \
  <temporary-harness-paths>
```

Use the broad framework restore command from the troubleshooting section only
when all Harness changes in the worktree are stale or temporary.

Never run `hgit add .` from a target research workspace. Add only explicit
Harness paths that were intentionally changed as framework code, then verify the
staged set before committing:

```bash
hgit add <intentional-harness-path>
hgit diff --cached --name-status
```

If a temporary patch should become a real Harness feature, first remove
project-specific assumptions, move project data rules behind a generic
configuration or project-owned command interface, add Harness tests, and commit
it as a separate Harness change.

## Before Pulling

Always inspect harness state first:

```bash
hgit status --short
```

If it is not clean, resolve that before `pull`.

Typical blocking files are:

- `README.md`
- `AI_AGENT_SETUP.md`
- `Harness_Update_Guide.md`
- `.claude/**`
- `.agents/**`
- `workflow_handbook/**`
- `tooling/codex_hooks/**`
- `tooling/auto_iterate/**`
- `tooling/workflow_supervisor/**`
- `tooling/evidence/**`
- `tooling/model_api/**`

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
diff OPERATOR_CONTEXT.md.template OPERATOR_CONTEXT.md
diff tooling/auto_iterate/docs/auto_iterate_goal_template.md docs/auto_iterate_goal.md
diff tooling/auto_iterate/config/templates/auto_iterate_controller.example.yaml tooling/auto_iterate/config/controller.local.yaml
diff tooling/auto_iterate/config/templates/auto_iterate_accounts.example.yaml tooling/auto_iterate/config/accounts.local.yaml
```

When Grill or init-project changed, also check whether the accepted-draft
handoff rules need to be merged into project guidance:

```bash
rg -n "update-from-grill|grill_draft_ready" \
  CLAUDE.md.template AGENTS.md.template \
  .agents/skills/grill/SKILL.md .agents/skills/init-project/SKILL.md \
  .claude/skills/grill/SKILL.md .claude/skills/init-project/SKILL.md
diff CLAUDE.md.template CLAUDE.md
diff AGENTS.md.template AGENTS.md
```

Current expected behavior after this Harness update:

- after the operator accepts a Grill draft, `$grill` should route directly to
  `$init-project update-from-grill` unless guidance initialization is skipped
- `$init-project update-from-grill` reads `docs/Research_Intent_Draft.md`,
  `docs/Grill_Round_Log.md`, `docs/Execution_Readiness_Packet.md`, and
  supervisor-produced `.workflow_supervisor/readiness.json` when present
- the handoff may initialize or refresh `CLAUDE.md`, `AGENTS.md`, and
  `README.md`
- dataset paths, baseline repos, and local clone/download targets from Grill
  remain candidate context until `prepare`, WF4, or WF5 verifies them
- the handoff does not create `PROJECT_STATE.json`, `project_map.json`, or
  `iteration_log.json`; missing state/map/iteration JSON immediately after
  `update-from-grill` is expected unless another tool already produced it
- a bare conversation `$workflow-supervisor` after accepted Grill output should
  run status first, then start full prepare with
  `--goal-file docs/Research_Intent_Draft.md --complete` when no run is active;
  shell CLI commands still require explicit segment/goal arguments

If the project uses the dynamic context layout, also compare the framework
templates and schemas before refreshing project-owned docs:

```bash
diff -r schemas .evidence/schemas 2>/dev/null || true
find templates/docs -type f | sort
python tooling/evidence/check_context_gates.py --workspace-root . --stage status
python tooling/evidence/compile_protocol.py --workspace-root .
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage status --review-packet
python tooling/evidence/check_protocol_drift.py --workspace-root . --stage status
python tooling/evidence/build_review_packet.py --workspace-root . --stage status
```

Do not overwrite approved contract docs automatically. Treat template changes as
new guidance and merge them into `docs/10_contract/**`, `docs/30_evidence/**`,
`docs/35_protocol/**`, `.evidence/schemas/**`, or committed docchains only
after reviewing the current project state.

If a project has not yet opted into dynamic context and wants to do so after a
harness update, initialize without overwriting existing docs:

```bash
python tooling/evidence/init_context.py --workspace-root . --set-state
```

If an updated contract/fact/protocol doc needs an evidence chain, regenerate and
validate it:

```bash
python tooling/evidence/compile_doc.py --workspace-root . --doc <doc.md> --source <source...>
python tooling/evidence/compile_protocol.py --workspace-root .
python tooling/evidence/validate_docchain.py .evidence/chains/<doc_id>/<build_id>
python tooling/evidence/check_docchain_gates.py --workspace-root .
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage status --review-packet
python tooling/evidence/check_protocol_drift.py --workspace-root . --stage status
python tooling/evidence/build_review_packet.py --workspace-root . --stage status
```

`compile_doc.py` refreshes the Markdown evidence headers and
`.evidence/index.json`. Commit `.evidence/index.json` and any
`.evidence/chains/**` directory referenced by current docs together with those
docs; leave `.evidence/protocol_compiler/**` and `.evidence/review_packets/**`
as local/generated review artifacts unless the project explicitly archives
them.

### 3b. Check workflow supervisor and hook updates

If any of these changed:

- `tooling/workflow_supervisor/**`
- `.agents/skills/workflow-supervisor/SKILL.md`
- `.claude/skills/workflow-supervisor/SKILL.md`
- `schemas/skill_contracts.json`
- `workflow_handbook/**`
- `tooling/codex_hooks/**`

run:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/evidence/validate_workflow_handbook.py --workspace-root .
```

Current supervisor behavior to remember after a pull:

- `$workflow-supervisor prepare --complete` can read `$grill` outputs such as
  `docs/Execution_Readiness_Packet.md`, `docs/Research_Intent_Draft.md`,
  `docs/Grill_Round_Log.md`, and optional
  `.workflow_supervisor/readiness.json`
- the inferred bridge is written by the supervisor under
  `.workflow_supervisor/runs/<run_id>/runtime/grill_bridge.json`
- external dataset downloads and baseline clones require
  `--allow-external-downloads` or an explicit allow policy in readiness input
- Codex worker handoffs belong under
  `.agents/state/workflow_supervisor_worker_results/**`; the supervisor adopts
  validated results into `.workflow_supervisor/**`

When templates add new sections or fields, merge them manually into the
project goal file or local controller YAML.

If your repo versions `controller.local.yaml` / `accounts.local.yaml` as shared
defaults, update those tracked files in place while keeping generated credential
directories outside the repo.

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
git --git-dir=.harness --work-tree=. diff -- \
  README.md AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
git --git-dir=.harness --work-tree=. diff --cached -- \
  README.md AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
```

If those are just stale local harness changes, restore them to harness `HEAD`
before retrying:

```bash
git --git-dir=.harness --work-tree=. restore \
  --staged --worktree --source=HEAD --ignore-skip-worktree-bits \
  README.md AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
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
/workflow_handbook/
/tooling/
/.agents/state/workflow_supervisor_worker_results/
/*.template
```

### Research files disappear from normal `git status`

This is the opposite failure mode: the shared root `.gitignore` is hiding
research-owned files from the research repo.

Symptoms:

- `git status --untracked-files=all` does not show `CLAUDE.md`, `AGENTS.md`,
  `docs/`, `src/`, or other research scaffolding you just created
- the files exist on disk, but normal `git` behaves as if they are ignored

Fix:

- keep the root `.gitignore` limited to rules safe for both repos
- move "hide research files from harness git" rules into `.harness/info/exclude`
- keep hiding harness-owned files from research git via `.git/info/exclude`

Quick check:

```bash
git check-ignore -v CLAUDE.md AGENTS.md docs src 2>/dev/null || true
git --git-dir=.harness --work-tree=. status --short
git status --untracked-files=all
```

## Summary

Use `git` for research files and `hgit` for framework files.

After every harness pull:

1. verify `hgit status`
2. read updated framework docs
3. diff templates against project-owned files
4. merge relevant template guidance into project-owned `CLAUDE.md`, `AGENTS.md`,
   `README.md`, or `docs/auto_iterate_goal.md` only after reviewing current
   project state
5. verify normal `git status` is still clean with respect to harness paths and
   is still able to see research-owned files
6. run workflow-supervisor, hook-contract, and handbook checks when those paths
   changed

For every harness push:

1. verify `hgit status`
2. confirm staged diffs contain no project-local temporary Harness patches
3. confirm you committed only harness-owned paths
4. push with `hgit`, not normal `git`
