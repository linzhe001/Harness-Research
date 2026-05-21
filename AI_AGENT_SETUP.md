# AI Agent Setup Runbook

This file is for AI agents that need to rebuild or refresh a Harness Research
workspace until the operator can immediately use the workflow, for example:

```text
$init init
$orchestrator status
$iterate status
```

Canonical names still exist. `$init` is the short alias for
`$init-project`; `/init-project` remains the Claude Code form.

## Success Criteria

Setup is complete only when all of these are true:

- the target research workspace contains Harness framework files
- Codex hooks are installed or explicitly marked `NOT_RUN`
- `schemas/skill_contracts.json` is present and hook status sees the workspace
  as Harness-active
- `CLAUDE.md`, `AGENTS.md`, and `MEMORY.md` exist from project templates;
  `$init init` can then refresh compact guidance without needing framework
  paths to be reconstructed
- dynamic-context directories and templates are initialized when the project
  opts into them
- the operator can open Codex in the target workspace and run `$init init`
  without needing to manually reconstruct framework paths

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
        PROJECT_STATE.json         workflow state, when initialized
        iteration_log.json         WF10 experiment history
        project_map.json           stable code map after WF7
        docs/                      research docs and dynamic context
        src/ scripts/ configs/     research implementation
```

The two git histories share one worktree but must not track the same files.

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
not copy the framework source root `AGENTS.md` or `CLAUDE.md`; target workspace
versions of those files must come from templates or `$init`.

```bash
cd "$TARGET_WORKSPACE"

for path in \
  .agents \
  .claude \
  tooling \
  templates \
  schemas \
  workflow_handbook \
  README.md \
  AI_AGENT_SETUP.md \
  AGENTS.md.template \
  CLAUDE.md.template \
  MEMORY.md.template \
  OPERATOR_CONTEXT.md.template \
  settings.local.json.template
do
  if [ -e "$HARNESS_SOURCE/$path" ]; then
    rsync -ani "$HARNESS_SOURCE/$path" ./
  fi
done
```

Inspect the dry-run output. If it would overwrite research-owned files such as
`src/`, `scripts/`, `configs/`, `docs/`, `tests/`, root `AGENTS.md`, or root
`CLAUDE.md`, stop and ask the operator. Those paths should not be copied from
the framework source.

Then copy the framework:

```bash
for path in \
  .agents \
  .claude \
  tooling \
  templates \
  schemas \
  workflow_handbook \
  README.md \
  AI_AGENT_SETUP.md \
  AGENTS.md.template \
  CLAUDE.md.template \
  MEMORY.md.template \
  OPERATOR_CONTEXT.md.template \
  settings.local.json.template
do
  if [ -e "$HARNESS_SOURCE/$path" ]; then
    rsync -a "$HARNESS_SOURCE/$path" ./
  fi
done
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
  .evidence
do
  if [ -e "$path" ]; then
    rsync -a "$path" "$SETUP_BACKUP"/
  fi
done
```

Create the Harness git history in `.harness` and limit it to the framework
runtime surface with sparse checkout. This prevents `hgit` from claiming
research-owned paths such as root `AGENTS.md`, root `CLAUDE.md`, `docs/`, or
`tests/`.

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
/README.md
/AI_AGENT_SETUP.md
/AGENTS.md.template
/CLAUDE.md.template
/MEMORY.md.template
/OPERATOR_CONTEXT.md.template
/settings.local.json.template
EOF

git --git-dir=.harness --work-tree=. read-tree -mu HEAD

if [ -d "$SETUP_BACKUP" ]; then
  rsync -a "$SETUP_BACKUP"/ ./
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
/.claude/
/.agents/
/tooling/
/templates/
/schemas/
/workflow_handbook/
/README.md
/AI_AGENT_SETUP.md
/Harness_Update_Guide.md
/*.template
/settings.local.json.template
EOF
```

Harness git should ignore research-owned paths:

```bash
mkdir -p .harness/info
cat >> .harness/info/exclude <<'EOF'

# Research workspace layer
/.setup_backup/
/CLAUDE.md
/AGENTS.md
/MEMORY.md
/OPERATOR_CONTEXT.md
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
.auto_iterate/
wandb/
*.ckpt
*.pth
*.pt
EOF
```

### 4. Create Minimal Research Files

Copy templates only when the target file is missing:

```bash
cp -n CLAUDE.md.template CLAUDE.md
cp -n AGENTS.md.template AGENTS.md
cp -n MEMORY.md.template MEMORY.md
```

If `AGENTS.md` or `CLAUDE.md` already exists, verify it is project guidance, not
the framework source guidance:

```bash
rg -n "Use this checkout to improve the framework itself|framework codebase" \
  AGENTS.md CLAUDE.md && {
    echo "Target guidance appears to be copied from the framework source; replace from templates or run \$init init after operator confirmation." >&2
    exit 1
  } || true
```

Create `OPERATOR_CONTEXT.md` only from explicit operator preferences:

```bash
# Optional. Do not infer this from project facts.
cp -n OPERATOR_CONTEXT.md.template OPERATOR_CONTEXT.md
```

Create common research directories:

```bash
mkdir -p src scripts configs baselines experiments tests
mkdir -p docs docs/40_iterations docs/50_memory docs/90_legacy
```

At this point the operator can already ask Codex:

```text
$init init
```

The canonical form is:

```text
$init-project init
```

`$init init` prepares compact guidance. It does not approve contracts, validate
research evidence, or advance workflow stages.

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
docs/50_memory/**
.evidence/chains/
.evidence/schemas/
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

### 7. Optional Auto-Iterate Bootstrap

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
  -> research-owned objective, edited by the operator / $auto-iterate-goal

tooling/auto_iterate/config/controller.local.yaml
  -> local controller input for this workspace

.auto_iterate/
  -> controller-owned runtime, never create by hand
```

Before the first real run:

```bash
$auto-iterate-goal check
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json
```

Start only after WF9 has passed and the human accepts the relevant contract
boundary:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh start \
  --tool codex \
  --goal docs/auto_iterate_goal.md \
  --config tooling/auto_iterate/config/controller.local.yaml
```

## First Commands For The Operator

After setup, tell the operator to open Codex in `TARGET_WORKSPACE` and run:

```text
$init init
```

Then:

```text
$orchestrator status
```

If the project is ready to initialize workflow state:

```text
$orchestrator init
```

If only compact guidance needs refresh:

```text
$init update
```

## Verification Checklist

Run the smallest useful checks:

```bash
test -f schemas/skill_contracts.json
test -f schemas/skill_contracts.schema.json
test -f .agents/skills/init-project/SKILL.md
test -f .claude/skills/init-project/SKILL.md
test -f CLAUDE.md
test -f AGENTS.md
test -f MEMORY.md

python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit \
  --workspace-root . \
  --event-json '{"prompt":"run $init init"}'
```

Dual-repo checks:

```bash
git --git-dir=.harness --work-tree=. status --short
git status --short
git check-ignore -v .agents/ .claude/ tooling/ schemas/ README.md AI_AGENT_SETUP.md
```

Expected outcome:

- `hgit status` shows only intentional framework edits
- `git status` shows only intentional research files
- `git check-ignore` confirms research git hides framework paths
- hook status reports Harness contracts at `schemas/skill_contracts.json`
- `$init init` maps to `init-project`

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
| `.agents/**` | harness git | Codex skills and references |
| `.claude/**` | harness git | Claude Code skills and shared rules |
| `tooling/**` | harness git | hooks, evidence, auto-iterate, model API, framework tests |
| `templates/**` | harness git | bootstrap templates |
| `schemas/**` | harness git | framework schemas and Skill Contracts |
| `README.md`, `AI_AGENT_SETUP.md` | harness git | framework docs |
| `CLAUDE.md`, `AGENTS.md`, `MEMORY.md` | research git | project guidance and memory |
| `OPERATOR_CONTEXT.md` | research git | explicit operator preferences only |
| `PROJECT_STATE.json` | research git | workflow state |
| `iteration_log.json` | research git | WF10 experiment state |
| `project_map.json` | research git | stable implementation map |
| `docs/20_facts/Codebase_Map.md` | research git | operator-facing stable codebase map |
| `docs/**` | research git | project docs and dynamic context |
| `tests/**` | research git | project tests |
| `docs/30_evidence/**` | research git | operator-readable Conclusion Evidence tables |
| `.evidence/**` | research git or generated audit artifacts | tool-owned Evidence Chains/review packets; use tooling, do not hand-edit |
| `.auto_iterate/**` | ignored runtime | controller-owned |
