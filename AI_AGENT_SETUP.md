# AI Agent Setup Runbook

This file is for AI agents that need to rebuild or refresh a Harness Research
workspace until the operator can immediately use the visible workflow
Entrypoints, for example:

```text
$grill
$prepare
$run
```

Compatibility route hints such as `$init`, `$init-project`, `$iterate`,
`$workflow-supervisor`, and `$auto-iterate-goal` may still be recognized by
hooks and Skill Contracts. They are internal route targets or migration aids,
not the first-layer commands to teach operators. The operator-facing surface is
`$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, and `$change`.

## Success Criteria

Setup is complete only when all of these are true:

- the target research workspace contains Harness framework files
- Codex hooks are installed or explicitly marked `NOT_RUN`
- `schemas/skill_contracts.json` is present and hook status sees the workspace
  as Harness-active
- `CLAUDE.md`, `AGENTS.md`, `README.md`, and `MEMORY.md` are research-owned
  project files, initialized from reviewed candidate templates when missing
- incoming template candidates and `README_new.md` have either been merged into
  research-owned project files or removed as temporary setup inputs
- dynamic-context directories and templates are initialized when the project
  opts into them, including `Experiment_Queue.md`, `Discovery_Ledger.md`, and
  `Research_Wiki.md`
- the operator can open Codex in the target workspace and start from a visible
  Entrypoint without needing to manually reconstruct framework paths
- workflow-supervisor runtime is installed enough for `$prepare` / `$build`
  routing, status, and node validation, or any missing runtime check is
  explicitly marked `NOT_RUN`
- no temporary `harness-research/` or `Harness-Research/` source checkout is
  left inside the target research workspace after `.harness` is attached

Do not invent research facts, dataset paths, environment versions, metrics,
operator preferences, contract approvals, or release claims during setup.

## Mental Model

Harness setup separates framework state from research state:

```text
target workspace root
  |
  +-- framework layer
  |     .harness/                  harness git history
  |     .agents/                   Codex skills and references
  |     .claude/                   Claude Code skills and shared rules
  |     tooling/                   hooks, evidence tools, auto-iterate
  |     templates/                 project bootstrap templates
  |     schemas/                   framework schemas and skill contracts
  |
  +-- research layer
        .git/                      research git history
        CLAUDE.md                  compact project guidance
        AGENTS.md                  Codex/native project guidance
        README.md                  project-facing research README
        PROJECT_STATE.json         workflow state, when initialized
        iteration_log.json         WF10 experiment history
        project_map.json           stable code map after WF7
        docs/                      research docs and dynamic context
        src/ scripts/ configs/     research implementation
```

The two git histories share one worktree but must not track the same files.
Root `AGENTS.md`, `CLAUDE.md`, `README.md`, and `MEMORY.md` are target
research files. Harness templates and the framework source `README.md` are
incoming candidates only; use `README_new.md` for temporary README comparison
when no dedicated `README.md.template` exists.

## Required Inputs

Before changing files, identify:

| Input | Meaning |
| --- | --- |
| `TARGET_WORKSPACE` | directory where research will run |
| `HARNESS_SOURCE` | existing Harness Research checkout to copy from |
| `PROJECT_NAME` | human-readable research project name |
| `dynamic_context` | whether to initialize `docs/10_contract`, `docs/30_evidence`, `.evidence`, etc. |
| `auto_iterate` | whether to prepare `docs/auto_iterate_goal.md` and controller config |

If any of these are ambiguous, stop and ask the operator. The most expensive
setup mistake is initializing the wrong repo.

## Preflight

Export the two roots, then run these from the intended target workspace:

```bash
export TARGET_WORKSPACE=/path/to/research-workspace
export HARNESS_SOURCE=/path/to/Harness-Research
cd "$TARGET_WORKSPACE"

pwd
git status --short 2>/dev/null || true
test -d "$HARNESS_SOURCE/.git"
test -f "$HARNESS_SOURCE/schemas/skill_contracts.json"
test -f "$HARNESS_SOURCE/tooling/codex_hooks/install_hooks.py"
```

Classify the directories:

```text
HARNESS_SOURCE   -> framework source clone
TARGET_WORKSPACE -> live research workspace
reference repos  -> read-only comparison inputs, never the live root
```

Do not run setup inside a baseline/reference repo unless the operator explicitly
chooses it as `TARGET_WORKSPACE`.

## Bootstrap Flow

### 1. Copy Harness Runtime Files Into The Target Workspace

For a new or accepted target workspace, copy only framework runtime paths. Do
not copy the framework source root `AGENTS.md`, `CLAUDE.md`, or `README.md`
over target files. Target workspace versions of those files are
research-owned; they must come from reviewed candidate templates or project
state.

```bash
cd "$TARGET_WORKSPACE"

for path in \
  .agents \
  .claude \
  tooling \
  templates \
  schemas \
  workflow_handbook \
  AI_AGENT_SETUP.md \
  Harness_Update_Guide.md
do
  if [ -e "$HARNESS_SOURCE/$path" ]; then
    rsync -ani "$HARNESS_SOURCE/$path" ./
  fi
done
```

Inspect the dry-run output. If it would overwrite research-owned files such as
`src/`, `scripts/`, `configs/`, `docs/`, `tests/`, root `AGENTS.md`, root
`CLAUDE.md`, or root `README.md`, stop and ask the operator. Those paths should
not be copied from the framework source.

Then copy the framework:

```bash
for path in \
  .agents \
  .claude \
  tooling \
  templates \
  schemas \
  workflow_handbook \
  AI_AGENT_SETUP.md \
  Harness_Update_Guide.md
do
  if [ -e "$HARNESS_SOURCE/$path" ]; then
    rsync -a "$HARNESS_SOURCE/$path" ./
  fi
done
```

Create temporary candidate inputs for research-owned root guidance. These files
are comparison inputs only. After `CLAUDE.md`, `AGENTS.md`, `README.md`, and
`MEMORY.md` are initialized or refreshed, delete the candidates.

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
  if [ -e "$HARNESS_SOURCE/$path" ]; then
    cp -n "$HARNESS_SOURCE/$path" "$CANDIDATE_DIR/$path"
  fi
done

if [ -e "$HARNESS_SOURCE/README.md" ]; then
  cp -n "$HARNESS_SOURCE/README.md" README_new.md
fi
```

Do not copy the framework source `.gitignore` into a target research workspace.
This framework checkout intentionally ignores research-state paths such as
`/src/`, `/scripts/`, `/configs/`, `/docs/*`, and `/tests/*`; in a target
workspace, those are normal research files. Put Harness ownership hiding rules
in `.git/info/exclude` and `.harness/info/exclude` instead.

Before attaching `.harness`, preserve existing research-owned files that may
overlap with paths tracked by the framework source. Sparse checkout can remove
tracked paths outside its selected surface while it applies the framework index;
restore this backup immediately after the sparse checkout is applied.

```bash
SETUP_BACKUP=".setup_backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SETUP_BACKUP"

for path in \
  AGENTS.md \
  CLAUDE.md \
  MEMORY.md \
  OPERATOR_CONTEXT.md \
  README.md \
  PROJECT_STATE.json \
  iteration_log.json \
  project_map.json \
  .gitignore \
  docs \
  src \
  scripts \
  configs \
  baselines \
  experiments \
  tests \
  .evidence \
  .harness_update_candidates \
  README_new.md
do
  if [ -e "$path" ]; then
    rsync -a "$path" "$SETUP_BACKUP"/
  fi
done
```

Create the Harness git history in `.harness` and limit it to the framework
runtime surface with sparse checkout. This prevents `hgit` from claiming
research-owned paths such as root `AGENTS.md`, root `CLAUDE.md`, root
`README.md`, `docs/`, or `tests/`.

```bash
if [ -e .harness ]; then
  echo ".harness already exists; inspect before replacing it" >&2
  exit 1
fi

cp -a "$HARNESS_SOURCE/.git" .harness
git --git-dir=.harness --work-tree=. config core.bare false
git --git-dir=.harness --work-tree=. config status.showUntrackedFiles no
git --git-dir=.harness --work-tree=. config core.sparseCheckout true

cat > .harness/info/sparse-checkout <<'EOF'
/.agents/
/.claude/
/tooling/
/templates/
/schemas/
/workflow_handbook/
/AI_AGENT_SETUP.md
/Harness_Update_Guide.md
EOF

git --git-dir=.harness --work-tree=. read-tree -mu HEAD

if [ -d "$SETUP_BACKUP" ]; then
  rsync -a "$SETUP_BACKUP"/ ./
fi
```

If `HARNESS_SOURCE` was copied inside `TARGET_WORKSPACE` only as a temporary
setup source, remove that nested source checkout after `.harness` and the
runtime files are in place. Do not remove an external `HARNESS_SOURCE` clone;
the operator may use it to update other workspaces.

```bash
TARGET_REAL=$(realpath "$TARGET_WORKSPACE")
HARNESS_REAL=$(realpath "$HARNESS_SOURCE")
HARNESS_BASENAME=$(basename "$HARNESS_REAL")

if [ "$HARNESS_REAL" = "$TARGET_REAL" ]; then
  echo "HARNESS_SOURCE resolves to TARGET_WORKSPACE itself; inspect setup roots." >&2
elif [[ "$HARNESS_REAL" == "$TARGET_REAL"/* ]]; then
  case "$HARNESS_BASENAME" in
    harness-research|Harness-Research)
      test -d .harness
      test -f schemas/skill_contracts.json
      test -f tooling/codex_hooks/install_hooks.py
      test -d "$HARNESS_REAL/.git"
      rm -rf -- "$HARNESS_REAL"
      ;;
    *)
      echo "HARNESS_SOURCE is inside TARGET_WORKSPACE but has an unexpected name; inspect before deleting: $HARNESS_REAL" >&2
      ;;
  esac
else
  echo "HARNESS_SOURCE is outside TARGET_WORKSPACE; keep external framework clone."
fi
```

Optional shell helper:

```bash
alias hgit='git --git-dir=.harness --work-tree=.'
```

### 2. Initialize Or Preserve Research Git

If the target workspace does not already have a research git repo:

```bash
git init
```

Do not move or replace an existing `.git` without explicit operator approval.

### 3. Split Git Ownership

Research git should ignore framework-owned paths:

```bash
mkdir -p .git/info
cat >> .git/info/exclude <<'EOF'

# Harness framework layer
/.harness/
/.setup_backup/
/.codex/
/.harness_hooks/
/.workflow_supervisor/
/.claude/
/.agents/
/tooling/
/templates/
/schemas/
/workflow_handbook/
/AI_AGENT_SETUP.md
/Harness_Update_Guide.md
/.harness_update_candidates/
/README_new.md
EOF
```

Harness git should ignore research-owned paths:

```bash
mkdir -p .harness/info
cat >> .harness/info/exclude <<'EOF'

# Research workspace layer
/.setup_backup/
/.harness_update_candidates/
/CLAUDE.md
/AGENTS.md
/MEMORY.md
/OPERATOR_CONTEXT.md
/README.md
/README_new.md
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
/.auto_iterate/
/.workflow_supervisor/
/tests/
EOF
```

Important rule:

```text
root .gitignore is shared by both git histories
  -> keep it research-owned or safe for both repos
  -> use .git/info/exclude and .harness/info/exclude for ownership hiding
```

Create or preserve a research-owned root `.gitignore` only for ordinary project
runtime outputs:

```bash
touch .gitignore
cat >> .gitignore <<'EOF'

# Runtime outputs
__pycache__/
.pytest_cache/
.harness_hooks/
.harness_update_candidates/
README_new.md
.auto_iterate/
.workflow_supervisor/
.agents/state/workflow_supervisor_worker_results/
wandb/
*.ckpt
*.pth
*.pt
EOF
```

### 4. Create Minimal Research Files

Copy candidate templates only when the target file is missing:

```bash
TEMPLATE_DIR=$(find .harness_update_candidates -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -n 1)
test -n "$TEMPLATE_DIR"

cp -n "$TEMPLATE_DIR/CLAUDE.md.template" CLAUDE.md
cp -n "$TEMPLATE_DIR/AGENTS.md.template" AGENTS.md
cp -n "$TEMPLATE_DIR/MEMORY.md.template" MEMORY.md
```

If `AGENTS.md` or `CLAUDE.md` already exists, verify it is project guidance, not
the framework source guidance:

```bash
rg -n "Use this checkout to improve the framework itself|framework codebase" \
  AGENTS.md CLAUDE.md && {
    echo "Target guidance appears to be copied from the framework source; replace from reviewed candidates or rerun the internal init-project route after operator confirmation." >&2
    exit 1
  } || true
```

If `README.md` is missing, create a short project README from explicit operator
input or reviewed Grill context. Do not copy `README_new.md` directly over the
project README; it is the framework-source README used only for comparison.

Create `OPERATOR_CONTEXT.md` only from explicit operator preferences:

```bash
# Optional. Do not infer this from project facts.
# Set CREATE_OPERATOR_CONTEXT=1 only after the operator explicitly asks for it.
if [ "${CREATE_OPERATOR_CONTEXT:-0}" = "1" ]; then
  cp -n "$TEMPLATE_DIR/OPERATOR_CONTEXT.md.template" OPERATOR_CONTEXT.md
fi
```

Create common research directories:

```bash
mkdir -p src scripts configs baselines experiments tests
mkdir -p docs docs/40_iterations docs/45_discoveries docs/50_memory docs/90_legacy
```

At this point the operator can already ask Codex through visible Entrypoints:

```text
$grill
$prepare
```

If setup still needs to exercise compatibility routing, the hook simulator can
verify that `$init` maps to the internal `init-project` route. Do not teach
`$init` as the primary operator command.

After `CLAUDE.md`, `AGENTS.md`, `README.md`, and `MEMORY.md` are initialized or
merged, delete the candidate inputs:

```bash
rm -rf "$TEMPLATE_DIR"
rm -f README_new.md
rmdir .harness_update_candidates 2>/dev/null || true
```

### 5. Install Workspace-Local Codex Hooks

Install hooks from the target workspace:

```bash
python tooling/codex_hooks/install_hooks.py --workspace-root .
python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
```

Then open `/hooks` in the Codex TUI and trust the Harness workspace hooks when
the commands match:

```text
$(git rev-parse --show-toplevel)/tooling/codex_hooks/user_prompt_submit.py
$(git rev-parse --show-toplevel)/tooling/codex_hooks/pre_tool_use_policy.py
$(git rev-parse --show-toplevel)/tooling/codex_hooks/post_tool_use_markers.py
$(git rev-parse --show-toplevel)/tooling/codex_hooks/require_gate_ledger.py
```

Verify trust when the Codex app server is available:

```bash
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status
```

Expected hook status includes:

```text
Harness contracts: present (.../schemas/skill_contracts.json)
policy effect here: active
```

You can smoke-test `$init` detection without changing files:

```bash
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit \
  --workspace-root . \
  --event-json '{"prompt":"run $init init"}'
```

### 6. Optional Dynamic Context Bootstrap

Use this when the project wants current docs, Evidence Chains, Review Packets,
and contract gates:

```bash
python tooling/evidence/init_context.py --workspace-root . --set-state
```

This creates or preserves:

```text
docs/00_START_HERE.md
docs/10_contract/**
docs/20_facts/**
docs/20_facts/Codebase_Map.md
docs/30_evidence/**
docs/30_evidence/Validation_Table.md
docs/35_protocol/**
docs/40_iterations/**
docs/40_iterations/Experiment_Queue.md
docs/45_discoveries/**
docs/45_discoveries/Discovery_Ledger.md
docs/45_discoveries/Research_Wiki.md
docs/50_memory/**
.evidence/chains/
schemas/
```

It does not fabricate evidence and it does not create `OPERATOR_CONTEXT.md`.

Before treating current contract, fact, or protocol docs as ready, use the
evidence tooling:

```bash
python tooling/evidence/compile_doc.py \
  --workspace-root . \
  --doc docs/10_contract/Project_Contract.md \
  --source PROJECT_STATE.json docs/30_evidence/Evidence_Index.md

python tooling/evidence/validate_docchain.py .evidence/chains/<doc_id>/<build_id>
python tooling/evidence/check_docchain_gates.py --workspace-root .
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
```

Do not hand-edit `.evidence/**`; rerun the owning tooling.

### 7. Optional Workflow Supervisor Bootstrap

Use this when the operator wants conversation-driven execution through visible
Entrypoints such as `$prepare` and `$build`, which route to the internal
workflow-supervisor runtime. Prepare files only; do not approve a contract or
invent dataset/baseline paths during setup.

Useful smoke checks:

```bash
test -f .agents/skills/workflow-supervisor/SKILL.md
test -f tooling/workflow_supervisor/scripts/workflow_ctl.sh
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json || true
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
```

Bridge behavior:

```text
$grill artifacts
  -> docs/05_intake/Execution_Readiness_Packet.md
  -> docs/05_intake/Research_Intent_Draft.md
  -> docs/05_intake/Grill_Round_Log.md
  -> optional .workflow_supervisor/readiness.json
  -> workflow_ctl prepare --complete
  -> .workflow_supervisor/runs/<run_id>/runtime/grill_bridge.json
```

`prepare --complete` may read the Grill outputs above and infer candidate
dataset and baseline requirements. Exact private values still belong in the
readiness artifact or current operator instruction. If the packet leaves a path,
URL, license, or credential ambiguous, the supervisor should raise a typed
pending request rather than guess.

External dataset downloads and baseline clones are disabled unless the operator
passes `--allow-external-downloads` or the readiness artifact explicitly sets an
allow policy such as `external_download_policy: allow` or
`allow_external_downloads: true`.

Codex workers must not hand-edit `.workflow_supervisor/**`. When they need to
return a build result, they write the validated handoff under:

```text
.agents/state/workflow_supervisor_worker_results/**
```

The supervisor then validates and adopts that result into
`.workflow_supervisor/**`.

### 8. Optional Auto-Iterate Bootstrap

Prepare files only. Do not start unattended WF10 during setup.

```bash
mkdir -p docs
cp -n tooling/auto_iterate/docs/auto_iterate_goal_template.md docs/auto_iterate_goal.md
cp -n tooling/auto_iterate/config/templates/auto_iterate_controller.example.yaml \
  tooling/auto_iterate/config/controller.local.yaml
```

Boundary:

```text
docs/auto_iterate_goal.md
  -> research-owned objective, edited by the operator or the internal
     auto-iterate-goal route

tooling/auto_iterate/config/controller.local.yaml
  -> local controller input for this workspace

.auto_iterate/
  -> controller-owned runtime, never create by hand

.workflow_supervisor/
  -> supervisor-owned runtime, never create or edit by hand
```

Before the first real run, validate the goal through `$run` or the internal
auto-iterate-goal route, then inspect controller status:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json
```

WF10 runs must follow the Run Artifact Contract. Before meaningful training,
create or verify a semantic execution commit and record it as
`pre_train_commit`. Before meaningful evaluation, create or verify
`pre_eval_commit`, or record `pre_eval_commit_NOT_CHANGED` when the committed
training source already covers eval code/configs. Run-local code/configs under
`runs/wf10/<iter>/` are part of this execution boundary even when they will not
be promoted to stable code. Completed metric-bearing iterations must point
`iteration_log.json` at a run artifact bundle with `git_commit`, unique
`exp_dir`, resolved config, console log, git snapshot, and metric artifacts.
Screening/proxy runs store the bundle in `screening.run_manifest`; full runs
store the final bundle in top-level `run_manifest` without overwriting
`screening.run_manifest`. Use `docs/40_iterations/Experiment_Queue.md` for
next-run requests and assurance gaps, and `docs/45_discoveries/Research_Wiki.md`
for searchable findings and open questions.

Optional notification-free watchdog check:

```bash
python tooling/run_health/watchdog.py --base-dir /tmp/harness-run-health --once --json
```

Optional supervisor smoke check:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json || true
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
```

Start only after WF9 has passed, `docs/auto_iterate_goal.md` validates, and the
accepted Grill Automation Policy covers the unattended loop. Explicit Human
Approval is still needed for Grill exit/delegation, approval-recording tools,
actions outside the Automation Policy, and irreversible external submit.

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh start \
  --tool codex \
  --goal docs/auto_iterate_goal.md \
  --config tooling/auto_iterate/config/controller.local.yaml
```

## First Commands For The Operator

After setup, tell the operator to open Codex in `TARGET_WORKSPACE` and choose a
visible Entrypoint:

```text
$grill
```

If Grill artifacts already exist and the project is ready for execution
readiness:

```text
$prepare
```

If the project is already in WF10 and needs experiment iteration:

```text
$run
```

For result interpretation after a run:

```text
$analyze
```

Compatibility route hints such as `$init update`, `$workflow-supervisor`, and
`$auto-iterate-goal check` may still be used for migration/debugging, but they
are not the first-layer operator workflow.

## Verification Checklist

Run the smallest useful checks:

```bash
test -f schemas/skill_contracts.json
test -f schemas/skill_contracts.schema.json
test -f .agents/skills/init-project/SKILL.md
test -f .agents/skills/workflow-supervisor/SKILL.md
test -f .claude/skills/init-project/SKILL.md
test -f CLAUDE.md
test -f AGENTS.md
test -f README.md
test -f MEMORY.md

python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status || true
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
python tooling/evidence/check_workflow_state.py --workspace-root .
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit \
  --workspace-root . \
  --event-json '{"prompt":"run $init init"}'
```

Dual-repo checks:

```bash
git --git-dir=.harness --work-tree=. status --short
git status --short
git check-ignore -v \
  .agents/ .claude/ tooling/ schemas/ workflow_handbook/ \
  AI_AGENT_SETUP.md Harness_Update_Guide.md \
  .agents/state/workflow_supervisor_worker_results/ \
  .harness_update_candidates/ README_new.md
if git check-ignore -v README.md; then
  echo "README.md should be research-owned and visible to normal git" >&2
  exit 1
fi
test ! -d harness-research
test ! -d Harness-Research
```

Expected outcome:

- `hgit status` shows only intentional framework edits
- `git status` shows only intentional research files
- `git check-ignore` confirms research git hides framework paths and temporary
  candidates, while root `README.md` stays visible to normal `git`
- no nested temporary Harness source checkout remains in the target workspace
- hook status reports Harness contracts at `schemas/skill_contracts.json`
- compatibility route hint `$init init` maps to internal `init-project`

## Troubleshooting

### `$init` Does Not Trigger `init-project`

Check the contract file:

```bash
rg -n '"\\$init"|init-project' schemas/skill_contracts.json
python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit \
  --workspace-root . \
  --event-json '{"prompt":"run $init init"}'
```

If hooks are installed but not running, open `/hooks` in Codex and trust the
workspace hooks.

### `git status` Shows Harness Files In The Research Repo

Append missing paths to `.git/info/exclude`. Do not add harness-owned paths to
the research commit.

### `hgit status` Shows Research Files

Append missing research paths to `.harness/info/exclude`. Keep the root
`.gitignore` research-owned or conservative because both git histories read it.

### Dynamic Context Gate Fails

Do not mark the project ready by editing JSON manually. Read the failure, update
the source docs or contracts, then rerun:

```bash
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
```

### Auto-Iterate Is Stuck In `running`

Inspect before cleanup:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json
cat .auto_iterate/lock.json 2>/dev/null || true
tail -n 50 .auto_iterate/events.jsonl 2>/dev/null || true
```

Do not invent a successful iteration result. Resume from controller state or
clean stale runtime only after confirming no real controller process is active.

## File Ownership Summary

| Path | Owner | Notes |
| --- | --- | --- |
| `.harness/` | harness git | framework history |
| `.agents/**` | harness git | Codex skills and references, except ignored local state below |
| `.claude/**` | harness git | Claude Code skills and shared rules |
| `tooling/**` | harness git | hooks, evidence, auto-iterate, model API, framework tests |
| `templates/**` | harness git | bootstrap templates |
| `schemas/**` | harness git | framework schemas and Skill Contracts |
| `workflow_handbook/**` | harness git | operator-facing framework docs |
| `AI_AGENT_SETUP.md`, `Harness_Update_Guide.md` | harness git | framework setup/update docs |
| `CLAUDE.md`, `AGENTS.md`, `README.md`, `MEMORY.md` | research git | project guidance, README, and memory |
| `OPERATOR_CONTEXT.md` | research git | explicit operator preferences only |
| `.harness_update_candidates/**`, `README_new.md` | ignored temporary inputs | incoming template / README comparison files; delete after merge |
| `PROJECT_STATE.json` | research git | workflow state |
| `iteration_log.json` | research git | WF10 experiment state |
| `project_map.json` | research git | stable implementation map |
| `docs/20_facts/Codebase_Map.md` | research git | operator-facing stable codebase map |
| `docs/**` | research git | project docs and dynamic context |
| `tests/**` | research git | project tests |
| `docs/30_evidence/**` | research git | operator-readable Conclusion Evidence tables |
| `.evidence/**` | research git or generated audit artifacts | tool-owned Evidence Chains/review packets; use tooling, do not hand-edit |
| `.auto_iterate/**` | ignored runtime | controller-owned |
| `.workflow_supervisor/**` | ignored runtime | supervisor-owned |
| `.agents/state/workflow_supervisor_worker_results/**` | ignored runtime | worker-result handoff, adopted by supervisor |
