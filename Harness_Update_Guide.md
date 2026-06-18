# Harness Update Guide

## Purpose

This guide explains the day-2 pull and push workflow for Harness Research in a
same-worktree dual-repo project.

## Related Framework Docs

For full framework bootstrap, see:

- [AI_AGENT_SETUP.md](./AI_AGENT_SETUP.md)
- [Legacy Docs Migration](./workflow_handbook/pages/legacy_docs_migration.md)

In this layout:

- the harness repo lives in `.harness`
- the research repo lives in the normal `.git`
- both repos share the same project root as one worktree

That means some framework files can appear at the project root while still
belonging to the harness repo. Target root `AGENTS.md`, `CLAUDE.md`,
`README.md`, and `MEMORY.md` are exceptions: they are research-owned project
guidance files.

## What Is Harness-Owned

When you update harness, the following paths are framework files managed by
`hgit`:

- `.claude/**`
- `.agents/**`, except ignored local state under `.agents/state/**`
- `templates/**`
- `schemas/**`
- `workflow_handbook/**`
- `tooling/codex_hooks/**`
- `tooling/evidence/**`
- `tooling/auto_iterate/**`
- `tooling/run_health/**`
- `tooling/workflow_supervisor/**`
- `tooling/model_api/**`
- `tooling/.tests/**`
- `AI_AGENT_SETUP.md`
- `Harness_Update_Guide.md`

Do not add these files to the research repo.

In a target research workspace, root `AGENTS.md`, `CLAUDE.md`, `README.md`, and
`MEMORY.md` belong to normal `git`. Harness source templates and the framework
source `README.md` are update candidates only. When there is no dedicated
`README.md.template`, write the incoming framework README to `README_new.md`,
compare it with the project README, merge only relevant guidance, and delete
`README_new.md`.

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
  `.agents/state/workflow_supervisor_worker_results/`,
  `.harness_update_candidates/`, `README_new.md`, and `__pycache__/`
- avoid: root `.gitignore` rules whose only purpose is to hide framework files
  from the research repo or research files from the harness repo

Workflow supervisor worker handoffs are local runtime state:

- keep `.agents/state/workflow_supervisor_worker_results/**` out of both git
  histories
- do not manually edit `.workflow_supervisor/**`; use
  `tooling/workflow_supervisor/scripts/workflow_ctl.sh`

If normal `git status --untracked-files=all` suddenly stops showing research
files such as `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/`, or `src/`, the root
`.gitignore` is hiding too much. Move those research-side hide rules into
`.harness/info/exclude`.

### One-time migration for older target workspaces

Older target workspaces may have root `README.md` or root `*.template` files in
the Harness sparse checkout. Move those paths out of the target Harness surface
before the next pull. Preserve research-owned root files first:

```bash
alias hgit='git --git-dir=.harness --work-tree=.'

MIGRATION_BACKUP=".harness_update_candidates/root-doc-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$MIGRATION_BACKUP"

for path in README.md AGENTS.md CLAUDE.md MEMORY.md OPERATOR_CONTEXT.md
do
  if [ -e "$path" ]; then
    cp -a "$path" "$MIGRATION_BACKUP"/
  fi
done

cp .harness/info/sparse-checkout \
  ".harness/info/sparse-checkout.backup.$(date +%Y%m%d_%H%M%S)"

sed -i \
  -e '/^\/README\.md$/d' \
  -e '/^\/AGENTS\.md\.template$/d' \
  -e '/^\/CLAUDE\.md\.template$/d' \
  -e '/^\/MEMORY\.md\.template$/d' \
  -e '/^\/OPERATOR_CONTEXT\.md\.template$/d' \
  -e '/^\/settings\.local\.json\.template$/d' \
  .harness/info/sparse-checkout

hgit read-tree -mu HEAD
cp -a "$MIGRATION_BACKUP"/. ./
```

Then make the ownership excludes explicit:

```bash
cat >> .git/info/exclude <<'EOF'
/.harness_update_candidates/
/README_new.md
EOF

cat >> .harness/info/exclude <<'EOF'
/README.md
/.harness_update_candidates/
/README_new.md
EOF
```

Verify normal `git` can see `README.md`, while temporary candidates remain
ignored. Delete `.harness_update_candidates/` after the migration is verified.

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
HARNESS_BEFORE=$(hgit rev-parse HEAD)
hgit fetch origin
hgit pull --ff-only origin "$(hgit branch --show-current)"
HARNESS_AFTER=$(hgit rev-parse HEAD)
hgit status --short
printf 'Harness updated: %s -> %s\n' "$HARNESS_BEFORE" "$HARNESS_AFTER"
```

Expected result after the final status command: empty output.
Keep `HARNESS_BEFORE` and `HARNESS_AFTER` available for the migration review
below. If you use a wrapper, it should print or persist equivalent before/after
Harness commit refs.

If the variables were lost after a successful pull, recover them from Harness
git metadata when possible:

```bash
HARNESS_BEFORE=$(hgit rev-parse ORIG_HEAD)
HARNESS_AFTER=$(hgit rev-parse HEAD)
hgit reflog --date=iso -5
```

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
  AI_AGENT_SETUP.md Harness_Update_Guide.md \
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
  AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
hgit diff --cached -- \
  AI_AGENT_SETUP.md Harness_Update_Guide.md \
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

- `AI_AGENT_SETUP.md`
- `Harness_Update_Guide.md`
- `.claude/**`
- `.agents/**`
- `workflow_handbook/**`
- `tooling/codex_hooks/**`
- `tooling/auto_iterate/**`
- `tooling/run_health/**`
- `tooling/workflow_supervisor/**`
- `tooling/evidence/**`
- `tooling/model_api/**`

## After Pulling

### 1. Confirm harness is clean

```bash
hgit status --short
```

Expected result: empty output.

### 2. Treat updated setup docs as framework docs

If any of these changed:

- `AI_AGENT_SETUP.md`
- `Harness_Update_Guide.md`

read them as framework updates. Do not commit them into the research repo.

### 3. Compare old and new Harness behavior before migrating

Before changing research-owned files, compare the just-pulled Harness range
against the version the target workspace was using. This step decides whether
the pull is only a framework refresh or also requires a project migration.

Use the `HARNESS_BEFORE` and `HARNESS_AFTER` refs captured during the pull:

```bash
: "${HARNESS_BEFORE:?missing pre-pull Harness ref}"
: "${HARNESS_AFTER:?missing post-pull Harness ref}"

hgit diff --name-status "$HARNESS_BEFORE..$HARNESS_AFTER" -- \
  AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling

hgit diff "$HARNESS_BEFORE..$HARNESS_AFTER" -- \
  schemas/skill_contracts.json templates/docs workflow_handbook/pages \
  .agents/references .agents/skills .claude/shared .claude/skills \
  tooling/evidence tooling/workflow_supervisor tooling/auto_iterate tooling/run_health
```

Then isolate migration-sensitive surfaces:

```bash
hgit diff "$HARNESS_BEFORE..$HARNESS_AFTER" --name-only | rg \
  '^(templates/docs|schemas/|workflow_handbook/pages/legacy_docs_migration.md|\.agents/references/context-layering-policy.md|\.agents/references/contract-gating-rule.md|\.agents/references/evidence-chain-rule.md|\.agents/references/run-artifact-contract.md|tooling/evidence/|tooling/run_health/)'
```

If this command returns paths, read
`workflow_handbook/pages/legacy_docs_migration.md` before editing project docs.
Do not infer facts, approvals, dataset paths, metrics, or successful runs from
the new Harness templates. Templates are migration inputs only.

### 4. Plan the target-workspace migration

Write a short migration plan before modifying project-owned files. For a small
update, the plan can live in the current conversation. For a larger workspace
migration, create a persistent plan such as
`docs/90_legacy/Harness_Update_Migration_Plan.md` in the research repo.

The plan should record:

- `HARNESS_BEFORE` and `HARNESS_AFTER`
- the Harness surfaces that changed
- affected research-owned files such as `AGENTS.md`, `CLAUDE.md`, `README.md`,
  `docs/**`, `MEMORY.md`, `PROJECT_STATE.json`, `iteration_log.json`, and
  `project_map.json`
- which files will be copied, merged, archived under `docs/90_legacy/**`, or
  left unchanged
- which gates will run and any expected `NOT_RUN` reasons
- approval decisions needed before a draft becomes an Approved Contract
- Claim Delta Evidence needed when a paper claim, release claim, or claim
  boundary changes inside an accepted Automation Policy

For contract, fact, protocol, discovery, or memory migrations, use
`workflow_handbook/pages/legacy_docs_migration.md` as the operating guide. Old
docs are Source Artifacts until reclassified. Old `approved`, `final`, or
`validated` wording is not current Human Approval unless there is current
Approval Evidence.

### 5. Generate candidate guidance inputs

Harness updates do not automatically merge project-specific root guidance.
Generate temporary candidates, compare them with the research-owned files, then
delete the candidates after merging relevant guidance.

```bash
CANDIDATE_DIR=".harness_update_candidates/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CANDIDATE_DIR"

for path in \
  AGENTS.md.template \
  CLAUDE.md.template \
  MEMORY.md.template \
  OPERATOR_CONTEXT.md.template \
  settings.local.json.template
do
  if hgit cat-file -e "HEAD:$path" 2>/dev/null; then
    hgit show "HEAD:$path" > "$CANDIDATE_DIR/$path"
  fi
done

if hgit cat-file -e HEAD:README.md 2>/dev/null; then
  hgit show HEAD:README.md > README_new.md
fi
```

`README_new.md` is a comparison input because there is no dedicated
`README.md.template`. Do not copy it directly over the project README.

### 6. Compare candidates with project-owned files

Check at least:

```bash
diff "$CANDIDATE_DIR/CLAUDE.md.template" CLAUDE.md
diff "$CANDIDATE_DIR/AGENTS.md.template" AGENTS.md
if [ -f OPERATOR_CONTEXT.md ]; then
  diff "$CANDIDATE_DIR/OPERATOR_CONTEXT.md.template" OPERATOR_CONTEXT.md
fi
diff README_new.md README.md
diff tooling/auto_iterate/docs/auto_iterate_goal_template.md docs/auto_iterate_goal.md
diff tooling/auto_iterate/config/templates/auto_iterate_controller.example.yaml tooling/auto_iterate/config/controller.local.yaml
diff tooling/auto_iterate/config/templates/auto_iterate_accounts.example.yaml tooling/auto_iterate/config/accounts.local.yaml
```

When Grill or init-project changed, also check whether the accepted-draft
handoff rules need to be merged into project guidance:

```bash
rg -n "update-from-grill|grill_draft_ready" \
  "$CANDIDATE_DIR/CLAUDE.md.template" "$CANDIDATE_DIR/AGENTS.md.template" \
  .agents/skills/grill/SKILL.md .agents/skills/init-project/SKILL.md \
  .claude/skills/grill/SKILL.md .claude/skills/init-project/SKILL.md
diff "$CANDIDATE_DIR/CLAUDE.md.template" CLAUDE.md
diff "$CANDIDATE_DIR/AGENTS.md.template" AGENTS.md
diff README_new.md README.md
```

Current expected behavior after this Harness update:

- after the operator accepts a Grill draft, `$grill` should route to the
  internal `init-project update-from-grill` mode unless guidance initialization
  is skipped
- internal `init-project update-from-grill` reads
  `docs/05_intake/Research_Intent_Draft.md`, `docs/05_intake/Grill_Round_Log.md`,
  `docs/05_intake/Execution_Readiness_Packet.md`, and supervisor-produced
  `.workflow_supervisor/readiness.json` when present
- the handoff may initialize or refresh `CLAUDE.md`, `AGENTS.md`, and
  `README.md`
- dataset paths, baseline repos, and local clone/download targets from Grill
  remain candidate context until `prepare`, WF4, or WF5 verifies them
- the handoff does not create `PROJECT_STATE.json`, `project_map.json`, or
  `iteration_log.json`; missing state/map/iteration JSON immediately after
  `update-from-grill` is expected unless another tool already produced it
- a visible `$prepare` request after accepted Grill output should run status
  first, then route to full prepare with
  `--goal-file docs/05_intake/Research_Intent_Draft.md --complete` when no run is active;
  shell CLI commands still require explicit segment/goal arguments

After all relevant guidance is merged:

```bash
rm -rf "$CANDIDATE_DIR"
rm -f README_new.md
rmdir .harness_update_candidates 2>/dev/null || true
```

### 7. Check dynamic context updates

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

When docs layout, contract docs, memory, discovery, protocol, or
`docs/90_legacy/**` are affected, follow
`workflow_handbook/pages/legacy_docs_migration.md`:

- move old `docs/Research_Intent_Draft.md`, `docs/Grill_Round_Log.md`, and
  `docs/Execution_Readiness_Packet.md` into `docs/05_intake/**`
- migrate old contract text into `docs/10_contract/**` as `Status: draft`
  unless current Approval Evidence exists
- place current facts, Conclusion Evidence inputs, and Protocol Drafts under
  `docs/20_facts/**`, `docs/30_evidence/**`, and `docs/35_protocol/**`
- put planned WF10 questions, falsifiers, controls, paper-driven run requests,
  and assurance gaps in `docs/40_iterations/Experiment_Queue.md`
- put observations, phenomena, hypotheses, and next-run hints in
  `docs/45_discoveries/Discovery_Ledger.md`
- put searchable findings, method notes, paper context, and open questions in
  `docs/45_discoveries/Research_Wiki.md`
- promote only accepted lessons to `docs/50_memory/Lessons.md` or `MEMORY.md`
- archive superseded narrative docs under `docs/90_legacy/**`

Do not overwrite Approved Contracts automatically. If the migration changes a
contract boundary, mark the changed contract `draft` or `superseded`, build a
Review Packet, and wait for explicit Human Approval before treating it as
approved again. Ordinary paper/release claim deltas inside an accepted
Automation Policy should record Claim Delta Evidence and Gate ledger output,
not default to a manual approval pause.

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

### 8. Check WF10 run artifact contract updates

If any of these changed:

- `.agents/references/run-artifact-contract.md`
- `.claude/shared/run-artifact-contract.md`
- `.agents/skills/iterate/**`
- `.claude/skills/iterate/**`
- `schemas/iteration_log.schema.json`
- `tooling/run_artifacts.py`
- `tooling/evidence/check_workflow_state.py`
- `tooling/auto_iterate/**`
- `tooling/run_health/**`

run:

```bash
python tooling/evidence/check_workflow_state.py --workspace-root .
pytest tooling/.tests/test_run_artifacts.py \
  tooling/.tests/test_workflow_state_check.py \
  tooling/.tests/test_auto_iterate_runtime_adapter.py
```

Current run artifact behavior to remember after a pull:

- meaningful training runs require a semantic `pre_train_commit`
- meaningful evaluation runs require `pre_eval_commit` or
  `pre_eval_commit_NOT_CHANGED` when the committed training source already
  covers eval code/configs
- run-local code/configs under `runs/wf10/<iter>/` are part of the execution
  boundary even when they will not be promoted to stable code
- completed metric-bearing iterations need a run artifact bundle with
  `git_commit`, unique `exp_dir`, resolved config, console log, git snapshot,
  and metric artifacts
- `docs/40_iterations/Experiment_Queue.md` is the durable queue for next-run
  questions, falsifiers, and assurance gaps
- `docs/45_discoveries/Research_Wiki.md` is the searchable index for findings,
  method notes, paper context, and open questions
- screening/proxy runs store their bundle in `screening.run_manifest`; full runs
  store the final bundle in top-level `run_manifest`
- full runs must not overwrite `screening.run_manifest`
- old completed iterations without real run artifacts may fail gates after this
  update; backfill only from real Source Artifacts or leave the iteration
  incomplete / legacy-exception documented in the Gate ledger

Do not hand-edit `iteration_log.json` to invent successful runs. If the
artifact directory, stdout log, config snapshot, or git snapshot cannot be
found, keep the result out of strong Conclusion Evidence until rerun.

### 9. Check workflow supervisor and hook updates

If any of these changed:

- `tooling/workflow_supervisor/**`
- `tooling/run_health/**`
- `.agents/skills/workflow-supervisor/SKILL.md`
- `.claude/skills/workflow-supervisor/SKILL.md`
- `schemas/skill_contracts.json`
- `workflow_handbook/**`
- `tooling/codex_hooks/**`

run:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status
python tooling/evidence/validate_workflow_handbook.py --workspace-root .
```

Current supervisor behavior to remember after a pull:

- visible `$prepare` routing can read `$grill` outputs such as
  `docs/05_intake/Execution_Readiness_Packet.md`, `docs/05_intake/Research_Intent_Draft.md`,
  `docs/05_intake/Grill_Round_Log.md`, and optional
  `.workflow_supervisor/readiness.json`
- the inferred bridge is written by the supervisor under
  `.workflow_supervisor/runs/<run_id>/runtime/grill_bridge.json`
- external dataset downloads and baseline clones require
  `--allow-external-downloads` or an explicit allow policy in readiness input
- Codex worker handoffs belong under
  `.agents/state/workflow_supervisor_worker_results/**`; the supervisor adopts
  validated results into `.workflow_supervisor/**`
- after Grill records an Automation Policy, non-Grill prepare/build/run/analyze/
  write/change and release validate/package work should auto-proceed inside
  that policy; submit and approval-recording tools still require explicit
  operator action
- claim or claim-boundary changes inside the policy require Claim Delta
  Evidence and a Gate ledger, not repeated approval prompts
- `tooling/run_health/watchdog.py` is a notification-free status surface for
  long runs; it writes pollable JSON/TXT under `/tmp/harness-run-health` by
  default

When templates add new sections or fields, merge them manually into the
project goal file or local controller YAML.

If your repo versions `controller.local.yaml` / `accounts.local.yaml` as shared
defaults, update those tracked files in place while keeping generated credential
directories outside the repo.

### 10. Check the research repo separately

```bash
git status --short
```

Harness-owned files should not show up there as files to add. If they do, hide
them via `.git/info/exclude` in the research repo instead of tracking them.

After a project migration, commit the research-owned migration slice with normal
`git`. Commit Harness-owned framework changes only with `hgit`. Keep generated
review artifacts out of commits unless the project explicitly archives them.

## Common Problems

### `hgit pull` says local changes would be overwritten

Inspect both staged and unstaged harness state:

```bash
git --git-dir=.harness --work-tree=. diff -- \
  AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
git --git-dir=.harness --work-tree=. diff --cached -- \
  AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .claude .agents workflow_handbook templates schemas tooling
```

If those are just stale local harness changes, restore them to harness `HEAD`
before retrying:

```bash
git --git-dir=.harness --work-tree=. restore \
  --staged --worktree --source=HEAD --ignore-skip-worktree-bits \
  AI_AGENT_SETUP.md Harness_Update_Guide.md \
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
/AI_AGENT_SETUP.md
/Harness_Update_Guide.md
/workflow_handbook/
/tooling/
/.agents/state/workflow_supervisor_worker_results/
/.harness_update_candidates/
/README_new.md
```

### Research files disappear from normal `git status`

This is the opposite failure mode: the shared root `.gitignore` is hiding
research-owned files from the research repo.

Symptoms:

- `git status --untracked-files=all` does not show `CLAUDE.md`, `AGENTS.md`,
  `README.md`, `docs/`, `src/`, or other research scaffolding you just created
- the files exist on disk, but normal `git` behaves as if they are ignored

Fix:

- keep the root `.gitignore` limited to rules safe for both repos
- move "hide research files from harness git" rules into `.harness/info/exclude`
- keep hiding harness-owned files from research git via `.git/info/exclude`

Quick check:

```bash
git check-ignore -v CLAUDE.md AGENTS.md README.md docs src 2>/dev/null || true
git --git-dir=.harness --work-tree=. status --short
git status --untracked-files=all
```

## Summary

Use `git` for research files and `hgit` for framework files.

After every harness pull:

1. verify `hgit status`
2. read updated framework docs
3. compare `HARNESS_BEFORE..HARNESS_AFTER` to identify migration-sensitive
   Harness changes
4. write a migration plan before changing research-owned docs or state
5. generate candidate templates and `README_new.md`
6. diff candidates against project-owned files
7. merge relevant guidance into project-owned `CLAUDE.md`, `AGENTS.md`,
   `README.md`, or `docs/auto_iterate_goal.md` only after reviewing current
   project state, then delete candidates
8. use `workflow_handbook/pages/legacy_docs_migration.md` when old docs,
   contracts, protocol, discovery, memory, or `docs/90_legacy/**` are affected
9. verify normal `git status` is still clean with respect to harness paths and
   is still able to see research-owned files
10. run workflow-supervisor, hook-contract, handbook, and run-artifact checks
   when those paths changed
11. commit research-owned migration slices with normal `git`; use `hgit` only
    for intentional Harness framework changes

For every harness push:

1. verify `hgit status`
2. confirm staged diffs contain no project-local temporary Harness patches
3. confirm you committed only harness-owned paths
4. push with `hgit`, not normal `git`
