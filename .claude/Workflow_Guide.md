# Harness Research Workflow Complete Guide

This document provides a detailed introduction to the domain-neutral research
workflow system built on Claude Code Skills. The system drives an AI/ML research
project from idea to release or paper-ready state while keeping evidence,
protocols, contracts, runtime state, and lessons separated.

---

## 1. System Architecture Overview

### 1.1 Three-Layer Configuration System

The system uses Claude Code's three-layer configuration mechanism, layered by loading frequency and scope:

| Layer | Location | Loading Method | Purpose |
|-------|----------|----------------|---------|
| **CLAUDE.md** | Project root | Auto-loaded every session | Global context: project name, environment, tech stack, current stage |
| **Rules** | `.claude/rules/` | Auto-loaded when editing files matching `globs` | Behavioral constraints: code modification standards, pre-training git operations, dependency change reminders |
| **Skills** | `.claude/skills/` | Manually invoked by user via `/skill-name` | Stage executors: complete logic for each workflow stage |

**Design philosophy**: CLAUDE.md is minimal (≤80 lines), containing only stable information "needed every time"; Rules load conditionally by path (via globs frontmatter), avoiding context pollution from irrelevant info; Skills are invoked on demand to execute specific work. Stage skills set `disable-model-invocation: true` and must be explicitly triggered by the user or orchestrator.

### 1.1.1 Operator-Facing Primitive Model

The operator-facing model should stay smaller than the implementation surface.
Most Harness work can be explained as eight primitives:

| Primitive | Human question | Main entrypoints | Boundary |
|------|------|------|------|
| `init` | Where is the workspace and what context exists? | `/orchestrator init`, `/init-project init`, `init_context.py` | Sets up structure and stable context; does not prove research facts. |
| `evidence` | What do we actually know? | fact docs, evidence tables, `compile_doc.py` | Evidence must come from source artifacts, logs, metrics, or explicit records. |
| `protocol` | What procedure should this project follow? | `/protocol-compiler`, `compile_protocol.py` | Drafts are evidence-derived until a human accepts the relevant contract. |
| `contract` | What boundaries are approved? | `/review-packet`, `approve_contract.py`, dynamic gates | Human approval is explicit and auditable; hooks are not approval. |
| `code` | What implementation changes are needed? | `/code-expert`, `/code-debug` | Code changes must respect contracts, plans, and project_map ownership. |
| `validate` | Did the change or stage actually pass? | `/validate-run`, tests, context/docchain gates | Report `PASS`, `FAIL`, or `NOT_RUN`; do not imply unrun gates passed. |
| `iterate` | What is the next experiment loop decision? | `/iterate`, auto-iterate controller | `iteration_log.json` is the experiment source of truth. |
| `release` | Which claims are supported? | `/final-exp`, `/release`, docchain/context gates | Claims must stay inside approved boundaries and evidence support. |

Tooling is layered so the workflow stays explainable:

- **Always-on guardrails**: `CLAUDE.md`, `AGENTS.md`, skill contracts, and hooks shape behavior and catch missing reads or forbidden writes.
- **On-demand evidence tools**: `compile_protocol.py`, `compile_doc.py`, review packets, approval tools, and dynamic-context gates create auditable state when a stage needs it.
- **Controller-owned runtime**: `.auto_iterate/**` and WF10 controller logs belong to the auto-iterate controller; operators should inspect them, not hand-edit them.

### 1.2 State Ownership

Each state file has a designated ownership boundary to avoid multi-source divergence:

| File | Write Responsibility | Purpose |
|------|------------|---------|
| `PROJECT_STATE.json` | orchestrator owns stage transitions; stage skills may record their own artifact metadata when invoked by the workflow | Stage transitions (single source of truth for stages) |
| `iteration_log.json` | iterate skill | Experiment history (single source of truth for experiments) |
| `project_map.json` | build-plan generates; code-expert, code-debug, or any workflow step that adds/removes/renames stable files or changes stable interfaces must update it | Stable implementation structure (single source of truth for durable files, not the architecture decision) |
| `CLAUDE.md` | init-project generates in stages | Global context for each Claude Code session |
| `OPERATOR_CONTEXT.md` | operator, recorded by init/orchestrator only from explicit input | Stable operator preferences; not evidence for project facts |

**Key rule**: iterate **does not write** PROJECT_STATE.json; orchestrator **does not write** iteration_log.json. Cross-file information is obtained through **reading**.

| File | Owner | Purpose |
|------|------------|---------|
| `.auto_iterate/` | auto-iterate controller | Controller-owned runtime state (e.g. `state.json`, phase logs). The controller only **reads** `iteration_log.json` and `PROJECT_STATE.json`; it never writes them. |

### 1.2.1 Gate Evidence Model

Workflow restrictions are layered:

```text
skill instructions
  -> Python gates / tests
  -> controller preflight and postconditions
  -> Codex sandbox, approval policy, execpolicy rules, hooks when configured
  -> explicit human approval records
```

Instructions are not proof that a gate ran. When a workflow action performs a
stage transition, writes current docs, changes stable code or interfaces, edits
canonical state, or prepares WF10/WF11/WF12 readiness, the final report must
include a gate ledger:

```text
Gate ledger
- command: <exact command or "not run">
- result: PASS | FAIL | NOT_RUN
- reason: <why this gate was required or why it could not run>
- artifacts: <state/doc/evidence paths created or updated>
```

Do not describe a gate as machine-verified unless the command, controller
preflight, controller postcondition, CI job, or approval tool actually ran. If
it did not run, report `NOT_RUN` with the reason. Codex runtime guards can
block or remind around tool use, but Harness readiness still depends on
`tooling/evidence/*.py`, controller checks, and explicit human approval records.
High-risk Codex skills may also define a machine-readable read/action/boundary
contract in `.agents/skill-contracts/contracts.json`; hooks and CI should treat
that file as the source of truth for required read sets and forbidden actions.

### 1.3 Dynamic Context Model

Harness core does not predefine field-specific profiles. Each project derives
its protocol from current evidence:

```text
operator context -> research evidence -> dynamic protocol -> approved contract
  -> evidence-compiled docs -> reproducible iteration -> promoted lessons
```

Current-project dynamic context files are research-owned:

- `OPERATOR_CONTEXT.md` stores operator preferences, not project facts. It is
  written only from explicit operator input during init or an explicit preference
  update; later stages read it but must not infer or rewrite preferences.
  `tooling/evidence/init_context.py` may create the dynamic-context directory
  and template layout, and may update `PROJECT_STATE.json` when `--set-state`
  is used, but it does not create or infer `OPERATOR_CONTEXT.md`.
- `docs/20_facts/**` stores current fact-layer summaries compiled from project
  artifacts, logs, configs, metrics, or evidence chains.
- `docs/30_evidence/**` stores evidence tables and open questions.
- `docs/35_protocol/**` stores evidence-derived protocol drafts.
- `docs/10_contract/**` stores human-approved project, evaluation, baseline,
  and claim contracts.
- `.evidence/chains/**` stores evidence_chain/source_manifest/doc_audit JSON
  for compiled current docs.
- `docs/50_memory/**` stores decisions, negative results, and candidate or
  accepted lessons; `MEMORY.md` stores accepted high-value lessons only.

Legacy flat docs such as `docs/Feasibility_Report.md`,
`docs/Technical_Spec.md`, and `docs/Baseline_Report.md` are compatibility
inputs to the fact layer. When refreshed, migrate current facts into
`docs/20_facts/**` or the numbered context docs, and archive superseded flat
docs under `docs/90_legacy/`.

### 1.4 Workflow Overview

```text
WF0 bootstrap/init
  -> WF1 survey
  -> WF2 idea-debate
  -> WF3 refine-idea
  -> WF4 data-prep
  -> WF5 baseline-repro
  -> WF6 architecture-design
  -> WF7 build-plan
  -> WF8 code-expert
  -> WF9 validate-run
  -> WF10 iterate
  -> WF11 final-exp
  -> WF12 release

WF10 decisions:
  NEXT_ROUND or DEBUG -> stay in WF10
  CONTINUE            -> WF11
  PIVOT               -> roll back to WF2 idea-debate/refine-idea
  ABORT               -> terminate project
```

WF0 is a setup layer, not a research claim stage. It chooses the target
workspace, copies or refreshes compact guidance files, optionally records
explicit operator preferences in `OPERATOR_CONTEXT.md`, optionally initializes
dynamic-context directories with `init_context.py`, and checks that hooks and
contracts are installed. WF0 does not approve protocols, evaluation contracts,
or release claims.

Utility skills (non-numbered stages):
- `/init-project` — WF0/bootstrap helper for compact project guidance and explicit operator context updates
- `/code-debug` — Code fixes (called by /iterate code or used independently)
- `/evaluate` — Result analysis (called by /iterate eval or used independently)
- `/env-setup` — Maintenance tool; used for environment refresh after dependency changes, not a main workflow prerequisite

---

## 2. Orchestrator — Central Dispatcher

**Invocation**: `/orchestrator [init|status|next|rollback|decision]`

The orchestrator does not perform specific research work, but manages the state transitions of the entire workflow:

- **`init`** — Run WF0 setup: create the directory structure, generate PROJECT_STATE.json, call `/init-project init` to generate minimal CLAUDE.md, and initialize dynamic context only when requested
- **`status`** — View current progress: includes stage consistency checks, reads iteration_log.json additionally during WF10
- **`next`** — Advance to next stage: verify prerequisites (are artifacts complete, any blockers), then call the corresponding skill
- **`rollback`** — Roll back to a specified stage: preserves history, does not delete any artifacts
- **`decision`** — Record key decisions: content, reasoning, alternatives considered

**Auto-trigger**: The `next` command automatically calls `/init-project update` to update CLAUDE.md after WF1, WF2, WF3, WF4, WF5, WF6, and WF7.

---

## 3. Stage Details

### WF1-WF4: Survey → Idea Debate → Refine Idea → Data

| Stage | Skill | Output | Decision |
|-------|-------|--------|----------|
| WF1 survey-idea | `/survey-idea` | docs/Feasibility_Report.md + optional `docs/30_evidence/**` | PROCEED/PIVOT/ABANDON |
| WF2 idea-debate | `/idea-debate` | docs/Idea_Debate.md + optional protocol updates | SELECT/PILOT_FIRST/MERGE/PIVOT/ABANDON |
| WF3 refine-idea | `/refine-idea` | docs/Refined_Idea.md + optional protocol drafts | SELECT/PILOT_FIRST/PIVOT/ABANDON |
| WF4 data-prep | `/data-prep` | docs/Dataset_Stats.md + data pipeline + CLAUDE.md dataset path sync + AGENTS.md consistency check | — |

WF2 is mandatory for new projects. Legacy projects that predate idea-debate may warn instead of failing, but a new dynamic-context project must hard-fail if it tries to move from WF1 directly to data preparation, baseline reproduction, or architecture design.

When dynamic context is enabled, `/protocol-compiler` can compile
`docs/30_evidence/**` into a reviewable draft packet before updating
`docs/35_protocol/**`.
Use `/review-packet` when a human approval decision is needed; the packet
summarizes context gates, protocol drift, docchain status, open questions, and
the exact approve/revise/reject action.

### WF5: Baseline Reproduction (with Mandatory Gate)

| | |
|---|---|
| **Skill** | `/baseline-repro [baseline_name or 'all']` |
| **Output** | `docs/Baseline_Report.md` + baseline_metrics + evaluation_protocol |
| **Gate** | Baseline_Report.md must exist, each baseline's status must be verified/partial (cannot be untested) |

If intentionally skipping certain baselines, they must be marked as `partial` with reasons explained in the report.
WF5 is also responsible for creating the first runnable environment and syncing `CLAUDE.md`'s `## Environment` and baseline summary.
When `docs/10_contract/Baseline_Contract.md` or
`docs/10_contract/Evaluation_Contract.md` exists, WF5 reads it first. If a
contract is missing, WF5 may derive a draft baseline or evaluation contract
from baseline evidence and `PROJECT_STATE.json.evaluation_protocol`.
WF5 is the first hard contract approval point: dynamic-context projects should
run protocol drift, context contract gates, docchain gates, and a review packet
before unattended WF10 or final experiments rely on the baseline set or
evaluation protocol.

### WF6-WF8: Architecture → Planning → Coding

| Stage | Skill | Output |
|-------|-------|--------|
| WF6 architecture-design | `/refine-arch` | docs/Technical_Spec.md |
| WF7 build-plan | `/build-plan` | docs/Implementation_Roadmap.md + project_map.json |
| WF8 code-expert | `/code-expert` | Complete project code |

WF6 chooses the MVP architecture from WF1-WF5 evidence, dataset constraints,
baseline behavior, and the Evaluation Contract. WF7 translates that design into
file ownership, implementation order, smoke tests, and `project_map.json`.
Architecture answers what should exist and why; the plan answers how to build
and verify it.

Run `/deep-check` as a design-review gate after WF6 and before WF7 when the
architecture changes claim boundaries, evaluation assumptions, core model/data
interfaces, or high-cost implementation direction.

### Dynamic Contract and Gate Timing

| Point | Required handling |
|------|-------------------|
| WF1 | Evidence tables may be compiled into draft protocol candidates. |
| WF2 | Idea debate may refresh protocol assumptions; drafts remain unapproved. |
| WF3 | Refined idea records task framing, metric needs, baselines to test, and open questions; use `/protocol-compiler` when evidence changed. |
| WF4 | Dataset and execution facts should be compiled or audited as fact docs when dynamic context is enabled. |
| WF5 | Baseline Contract and Evaluation Contract are drafted or approved; run protocol drift, context gates, docchain gates, and `/review-packet` for approval. |
| WF6/WF7 | Architecture and plan must read the Project/Baseline/Evaluation/Claim contracts when they exist; changing scope requires contract review instead of silent edits. |
| WF8/WF9 | Run contract gating before implementation and validation; do not rewrite contracts unless scope changes. |
| WF10 | Manual iteration reads `iteration_log.json`; unattended auto-iteration requires approved or explicitly accepted Evaluation Contract plus protocol-drift and dynamic-context gates. |
| WF11 | Final experiment design must pass dynamic-context checks and respect Evaluation Contract and Claim Boundary. |
| WF12 | Release claims must pass docchain/context gates and stay inside the Claim Boundary. |

### WF9: Code Review + Training Pipeline Validation (Gate)

| | |
|---|---|
| **Skill** | `/validate-run [config_path]` |
| **Review Items** | Codex code review (new code vs baseline equivalence: data pipeline, model, loss, evaluation metrics, common ML bugs) |
| **Validation Items** | 100-step training, checkpoint save/load, eval pipeline, wandb connection, git_snapshot |
| **Gate** | PASS → WF10, REVIEW → user confirms then continue or fix, FAIL → /code-debug to fix |

Ensures no code correctness or infrastructure issues are encountered during iteration.

Use `/code-review` as the reusable review-only gate outside the full WF9
validation flow:
- light mode for targeted codebase understanding
- medium mode after code changes before handoff
- heavy mode when generated docs, evidence chains, release claims, or stage
  gates depend on the reviewed code

Medium and heavy `/code-review` reports must include git metadata, changed line
ranges, independent reviewer statuses, reconciled findings, and a Gate ledger.
Fixes discovered by `/code-review` route through `/code-debug`.

**WF9 → WF10 bridge**: after validate-run PASS, the orchestrator auto-triggers `/auto-iterate-goal` to verify that the iteration goal is well-defined and ready before WF10 can start.
For dynamic-protocol projects, this bridge must also check the Evaluation
Contract. Auto-iteration requires an approved contract or an explicit operator
decision to proceed with a draft.
It should also run `/protocol-drift-check` for WF10. Blocking open questions,
due low-confidence assumptions, unreviewed negative results, or an unreviewed
PIVOT/ABORT signal require protocol review before unattended iteration.

### WF10: Structured Experiment Iteration (Core)

| | |
|---|---|
| **Skill** | `/iterate [plan|code|run|eval|ablate|status|log]` |
| **Output** | iteration_log.json (continuously updated), best checkpoint |
| **Decision** | NEXT_ROUND → stay in WF10 / DEBUG → debug round in WF10 / CONTINUE → WF11 / PIVOT → WF2 idea-debate/refine-idea / ABORT → terminate |

**Seven subcommands**:

| Subcommand | Purpose | Utility Called |
|------------|---------|---------------|
| `plan [hypothesis]` | Record hypothesis, check for repeated lessons, design changes, selective Codex review | — |
| `code [description]` | Implement code changes, enforce git commit | `/code-debug` |
| `run [config_path]` | Execute training + run eval + collect metrics (automated) | — |
| `eval [log_path]` | Evaluate results, compare against baseline + best, make decision | `/evaluate` |
| `ablate [iter_id] --components "..."` | Intra-iteration ablation experiment, determine component contributions | — |
| `status` | View current iteration + last 5 + best | — |
| `log` | Complete iteration history table | — |

**Typical iteration loop**:
```
/iterate plan "Upgrade backbone from ResNet-50 to ResNet-101 to enhance feature representation"
  → Repeated lessons check (warn about known failure patterns)
  → Record hypothesis, design config_diff
  → (Selective) Codex review of the approach

/iterate code "Upgrade backbone to ResNet-101"
  → Write persistent context (.claude/iterations/iter{N}/context.json)
  → Call /code-debug to modify code + enforce git commit
  → Remove symlink (preserve persistent context)
  → Status becomes "training"

/iterate run {config_path}
  → Auto-execute training (background task)
  → After training completes, auto-run {EVAL_SCRIPT}
  → Parse stdout to extract metrics, update iteration_log.json
  → Status becomes "running", output metrics summary

/iterate eval experiments/{exp_prefix}_iter27/
  → Call /evaluate to parse metrics → per-iteration report (docs/iterations/iter27.md)
  → Compare against baseline + best, make decision
  → Output recommended next command

# Optional: ablation experiment (determine component contributions)
/iterate ablate iter27 --components "aux_loss:loss.lambda_aux=0.0,lr_warmup:train.warmup_steps=0"
  → Run w/o training for each component
  → Output comparison table (component / primary_metric / Delta / Contribution)
```

**`run` automated execution flow**:

The `run` subcommand automates the full pipeline from code to metrics, replacing the previous manual training flow:

```
Build training command → Bash(run_in_background) → Parse stdout metrics → Run {EVAL_SCRIPT} → Update iteration_log.json
```

- Auto-builds `python {TRAIN_SCRIPT} --config ... --no_snapshot` command from config_diff
- Uses `run_in_background: true` to support 10-60 minute long training runs
- After training completes, parses training trajectory fields from stdout (e.g., best step, final step, intermediate validation summaries)
- Auto-runs `{EVAL_SCRIPT}`, extracting final metrics per the evaluation protocol established in WF5
- Error handling: on OOM/NaN/crash, keeps status="training" and reports error; never fails silently
- `--manual` fallback: for cluster training scenarios, degrades to metadata registration mode

**`ablate` ablation experiments**:

Quickly determine component contributions, generating a comparison table:

```
/iterate ablate {base_iter} --components "name1:override1,name2:override2"
```

Components are passed via `--components` as `name:override` pairs.
For each component, generates a `{base_iter}_no_{component}` sub-iteration, auto-evaluates after training, and classifies by the active Evaluation Contract thresholds. If the contract does not define ablation thresholds, use the default PSNR-style delta thresholds below:

| Delta Range | Classification |
|-------------|----------------|
| < -1.0 dB | `significant` — core component |
| < -0.3 dB | `moderate` — contributes |
| >= -0.3 dB and <= 0 dB | `minimal` — can be simplified |
| > 0 dB | `negative` — better without it |

Supports resumption: already completed sub-iterations are automatically skipped.

**Other key features**:
- **Persistent context**: stored at `.claude/iterations/iter{N}/context.json`, symlink as compatibility layer
- **Enforced git commit**: if no commit hash after code subcommand completes, stays in coding status without advancing
- **Repeated lessons check**: plan phase scans known lessons, warns about repeated failure patterns
- **Screening protocol**: non-architecture/loss changes should do a 5K-10K proxy run first
- **Same-iteration phases**: each iteration may include a `screening` phase (fast proxy run) and a `full_run` phase, both orchestrated by the controller within the same iteration
- **Auto mode**: when `auto_mode=true`, the controller drives the plan→code→run→eval loop without blocking on user confirmation
- **Controller resume**: on restart, the controller recovers state from `.auto_iterate/state.json` combined with repository inspection (iteration_log.json, git status) to determine where to resume

### WF11: Formal Ablation Experiments

| | |
|---|---|
| **Skill** | `/final-exp [stage_report_path]` |
| **Output** | docs/Final_Experiment_Matrix.md |
| **Prerequisite** | WF10 final iteration decision is CONTINUE |

Design a complete experiment matrix meeting top-venue standards:
- **Ablation experiments**: each innovation component ON/OFF, isolating individual contributions (can reuse preliminary results from WF10 `/iterate ablate`)
- **Hyperparameter search**: search space and strategy for key hyperparameters
- **Robustness tests**: different resolutions, extreme scenarios, OOD data
- **Cross-dataset evaluation**: verify generalizability
- **Compute budget**: estimate total GPU hours, plan execution order

### WF12: Submission & Release

| | |
|---|---|
| **Skill** | `/release [submit|package|validate]` |
| **Output** | Submission package (multi-scene rendering + packaging + filename validation) |
| **Prerequisite** | WF11 ablation experiments completed |

Three subcommands:
- **`validate`** — Check submission package completeness (filename format, resolution, scene coverage)
- **`package`** — Generate submission package conforming to competition/conference requirements
- **`submit`** — Multi-scene training + rendering + packaging + dry-run check

---

## 4. Utility Skills

### 4.1 env-setup — Maintenance Environment Refresh

**Invocation**: `/env-setup [create|refresh]`

- Not a main workflow prerequisite
- First runnable environment is created by WF5 `/baseline-repro`
- Only used when dependencies change, machines are switched, or `CLAUDE.md` environment section is outdated

When `requirements*.txt`, `environment*.yml`, or `pyproject.toml` change, the `deps-update` rule automatically reminds to run refresh.

### 4.2 code-debug — Code Fixes

**Invocation**: `/code-debug [error_log_path or issue description]`

**Operation modes** (determined by `.claude/current_iteration.json` context):
- `planned_change`: called by /iterate code, implements changes per hypothesis, semantic commit upon completion
- `bugfix`: called independently, diagnoses and fixes crashes/errors
- `perf_tuning`: called independently, performance optimization

After modifying code, automatically runs `py_compile` + `ruff check`; syncs `project_map.json` when interfaces change.

### 4.3 evaluate — Result Analysis

**Invocation**: `/evaluate [log_path]`

Core features:
- Parse training logs, extract target metrics defined by baseline/evaluation protocol
- Diagnose training issues (overfitting, vanishing gradients, loss divergence, etc.)
- Compare against baseline performance + historical best
- Provide NEXT_ROUND/DEBUG/CONTINUE/PIVOT/ABORT decision

**Per-iteration reports**: when called from /iterate eval, writes to `docs/iterations/iter{N}.md`.
`docs/Stage_Report.md` serves as the latest summary index.
`docs/50_memory/Lessons.md` is the candidate/accepted lesson workspace.
`MEMORY.md` stores accepted human-readable lessons; `iteration_log.json` remains
the machine source of truth. Auto-iteration may generate observations, findings,
and lesson candidates, but raw auto-run output must not be promoted directly
into `MEMORY.md`.

---

## 5. Key Feature Details

### 5.1 Stable vs Volatile File Layering

project_map.json only tracks **stable implementation files**:
- src/ core modules
- baselines/ subdirectories
- Core configs and scripts (listed in CLAUDE.md Entry Scripts)

**Volatile experiment assets** are not tracked:
- per-iteration scripts (run_*.sh, run_ablation_*.py)
- Temporary experiment configs
- Everything under experiments/

### 5.2 Documentation Surface and Legacy Archive

`docs/` is the current human-facing documentation surface. Keep root-level `docs/*.md` limited to the necessary Markdown files that best describe the current codebase state.

When a workflow refreshes an existing current doc, archive the previous version first:

```text
docs/Foo.md
  -> docs/90_legacy/YYYY-MM-DD/Foo__HHMMSS.md
  -> docs/Foo.md  (new current version)
```

Use `.claude/shared/documentation-evidence-rule.md` for source-grounded claims and `.claude/shared/documentation-style.md` for concise writing, ASCII flow diagrams, and archive naming.

### 5.3 Pre-Training Git + wandb Integration

Three layers of safeguards ensure complete version records for every training run:

1. **Claude's semantic commits** (rule-enforced)
2. **git_snapshot.py safety net** (in code)
3. **wandb + checkpoint records** (in code)

### 5.4 Codex Cross-Validation

| Trigger Point | Trigger Condition | Review Target | Review Focus |
|---------------|-------------------|---------------|--------------|
| WF6 design review | **Triggered for architecture, claim-boundary, metric, or high-cost interface changes** | Technical_Spec technical approach | Find missed risks and failure modes before implementation planning |
| WF9 validate-run | **Always triggered** (code entry gate) | src/ new code vs baselines/ reference impl | Baseline equivalence: data pipeline, model computation, loss, evaluation metrics |
| WF10 /iterate plan | **Selectively triggered**: new loss family, architecture changes, post-PIVOT, 3 consecutive DEBUGs | Single iteration hypothesis | Hypothesis validation, avoid repeated failures |

Recorded values: `"used"` / `"skipped_low_value"` / `"unavailable"` (no longer using null)

### 5.5 CLAUDE.md Staged Generation

CLAUDE.md is maintained as a **stable operations guide** (≤80 lines), without fast-changing experiment content.
Fast-changing content (current best, current risks, next experiment) resides in iteration_log.json and MEMORY.md.

| Timing | Content Added |
|--------|--------------|
| `init` | Environment placeholder + Workflow overview |
| After WF1 | Idea description |
| After WF2 | Idea debate decision reference |
| After WF3 | Refined idea and target framing |
| After WF4 | Dataset paths and statistics |
| After WF5 | Baseline metrics reference |
| After WF6 | Tech stack and architecture summary |
| After WF7 | Project Structure + Core Artifacts |
| After the first WF10 experiment | Entry Scripts (lock entry scripts) |

### 5.6 Automated Training Execution

`/iterate run` implements full pipeline automation from code to metrics:

```
                     /iterate run [config_path]
                               │
                               ▼
                ┌────────────────────────────┐
                │ ① Read iteration_log.json   │
                │    Find status="training"   │
                │    iteration                │
                │    Extract config_diff      │
                └──────────────┬─────────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ② Build training command    │
                │    python {TRAIN_SCRIPT}    │
                │      --config {config_path} │
                │      --no_snapshot          │
                │      {dotlist overrides}    │
                │    Determine exp_dir        │
                └──────────────┬─────────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ③ Bash(run_in_background)   │
                │    Execute training,        │
                │    ⏱ 10-60 min              │
                │    Record started_at        │
                │    timestamp                │
                └──────────────┬─────────────┘
                               │
                       ┌───────┴───────┐
                       │               │
                   exit = 0        exit ≠ 0
                       │               │
                       │               ▼
                       │    ┌────────────────────────┐
                       │    │ Error diagnosis          │
                       │    │ ┌──────────────────────┐│
                       │    │ │ "CUDA out of memory" ││
                       │    │ │ → OOM, suggest lower  ││
                       │    │ │   resolution          ││
                       │    │ ├──────────────────────┤│
                       │    │ │ "nan" in loss line   ││
                       │    │ │ → NaN, suggest lower  ││
                       │    │ │   LR                  ││
                       │    │ ├──────────────────────┤│
                       │    │ │ Other non-zero exit   ││
                       │    │ │ → crash, output stderr││
                       │    │ └──────────────────────┘│
                       │    │ Status stays "training"  │
                       │    │ Report error, terminate  │
                       │    └────────────────────────┘
                       │
                       ▼
                ┌────────────────────────────┐
                │ ④ Parse training stdout     │
                │    Extract training_trace   │
                │    e.g., best_step/         │
                │    final_step and           │
                │    intermediate metrics     │
                │    exposed by training      │
                │    script                   │
                └──────────────┬─────────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ⑤ Locate best checkpoint    │
                │    Scan exp_dir/checkpoints/│
                │    Sort by step, take latest│
                └──────────────┬─────────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ⑥ Run {EVAL_SCRIPT}         │
                │    --checkpoint {best_ckpt} │
                │    --output_dir {exp}/eval  │
                │    Extract metrics per      │
                │    evaluation protocol      │
                │    established in WF5       │
                └──────────────┬─────────────┘
                               │
                       ┌───────┴───────┐
                       │               │
                   eval success    eval failure
                       │               │
                       ▼               ▼
              ┌──────────────┐  ┌──────────────────┐
              │ Record all    │  │ Record training   │
              │ metrics       │  │ metrics only      │
              │ (train+eval)  │  │ Prompt user to    │
              │               │  │ run eval manually │
              └──────┬───────┘  └────────┬─────────┘
                     │                   │
                     └─────────┬─────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ⑦ Update iteration_log.json │
                │    run_manifest:            │
                │      command, config_path,  │
                │      exp_dir, duration,     │
                │      exit_code, ckpt_path   │
                │    metrics:                 │
                │      Only write protocol-   │
                │      defined tracked metrics│
                │    training_trace:          │
                │      best_step/final_step   │
                │      etc.                   │
                │    status → "running"       │
                └──────────────┬─────────────┘
                               │
                               ▼
                    Output metrics summary +
                    recommend `/iterate eval`
```

**`--manual` fallback**: If training needs to run on a cluster or user passes `--manual`, degrades to metadata registration mode
(only records command, config_path, exp_dir, expected_steps), status→"running", user calls `/iterate eval` after training completes.

### 5.7 Per-iteration Reports

Evaluation reports are stored per iteration:
- `docs/iterations/iter1.md`, `docs/iterations/iter2.md`, ...
- `docs/Stage_Report.md` serves as the latest summary index
- code-debug reads the latest iteration report rather than an outdated singleton

---

## 6. Rules Details

### 6.1 project-map.md

**Trigger condition**: when editing files under `src/`, `baselines/`, `configs/`, `scripts/`, `tests/`.
**Covered formats**: `*.py`, `*.yaml`, `*.yml`, `*.json`, `*.sh`
**Distinguishes stable/volatile**: only stable files need project_map.json updates.

### 6.2 pre-training.md

**Trigger condition**: when editing `scripts/train*.py`, `src/**/*.py`, `baselines/**/train*.py`.

### 6.3 deps-update.md

**Trigger condition**: when editing `requirements*.txt`, `environment*.yml`, `pyproject.toml`, `setup.py`.

---

## 7. State Transition Overview

### 7.1 Workflow Stage Transitions (Managed by PROJECT_STATE.json)

```text
WF0 bootstrap/init
  -> WF1 survey
  -> WF2 idea-debate
  -> WF3 refine-idea
  -> WF4 data-prep
  -> WF5 baseline-repro
  -> WF6 architecture-design
  -> WF7 build-plan
  -> WF8 code-expert
  -> WF9 validate-run
  -> WF10 iterate
  -> WF11 final-exp
  -> WF12 release

WF10 PIVOT rolls back to WF2. WF9 FAIL stays before WF10 and routes through
code-debug. WF6 design review can block WF7 until the architecture issue is
resolved or explicitly accepted.
```

After WF0, each completed research stage triggers `/init-project update` through
orchestrator to update CLAUDE.md.

### 7.2 WF10 Internal Iteration State Machine (Managed by iteration_log.json)

```
                        /iterate plan "hypothesis"
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │           planned              │  Repeated lessons check
                    │  hypothesis + config_diff      │  (Selective) Codex review
                    │  recorded                      │
                    └───────────────┬───────────────┘
                                    │
                                    │  /iterate code "description"
                                    ▼
                    ┌───────────────────────────────┐
                    │           coding               │  Write persistent context
                    │  Call /code-debug to modify    │  → .claude/iterations/iter{N}/
                    │  code                          │
                    │  Run py_compile + ruff check   │
                    │  Semantic git commit            │
                    └───────────────┬───────────────┘
                                    │
                            commit succeeded?
                           ┌────────┴────────┐
                           │                 │
                        failed            succeeded
                           │                 │
                           ▼                 ▼
                 Stay "coding"    ┌──────────────────────────┐
                 Report error     │        training           │
                 to user          │  Code ready, awaiting     │
                 Await manual fix │  training registration    │
                                  └────────────┬─────────────┘
                                               │
                                               │  /iterate run [config_path]
                                               ▼
                         ┌─────────────────────────────────────────────┐
                         │              Training Execution Phase        │
                         │                                              │
                         │  ┌──────────────────────────────────────┐   │
                         │  │ Build cmd → Bash(background) → wait  │   │
                         │  │ {TRAIN_SCRIPT} --config ... ⏱10-60min│   │
                         │  └──────────────────┬───────────────────┘   │
                         │                     │                        │
                         │             ┌───────┴───────┐                │
                         │             │               │                │
                         │          exit=0          exit≠0              │
                         │             │               │                │
                         │             │               ▼                │
                         │             │     ┌───────────────────┐      │
                         │             │     │ OOM → suggest lower│      │
                         │             │     │   resolution       │      │
                         │             │     │ NaN → suggest lower│      │
                         │             │     │   LR               │      │
                         │             │     │ crash → stderr     │      │
                         │             │     │ Stay "training"    │      │
                         │             │     │ Report error,      │      │
                         │             │     │ terminate ✗        │      │
                         │             │     └───────────────────┘      │
                         │             ▼                                │
                         │  ┌────────────────────────────────────┐     │
                         │  │ Parse stdout → peak/final metrics  │     │
                         │  │ Locate best checkpoint              │     │
                         │  │ Run {EVAL_SCRIPT} → protocol-       │     │
                         │  │ defined final metrics               │     │
                         │  └──────────────────┬─────────────────┘     │
                         │                     │                        │
                         │                     ▼                        │
                         │  ┌────────────────────────────────────┐     │
                         │  │ Update iteration_log.json           │     │
                         │  │   run_manifest + metrics            │     │
                         │  │   status → "running"                │     │
                         │  └────────────────────────────────────┘     │
                         └─────────────────────────────────────────────┘
                                              │
                                              │  /iterate eval [exp_dir]
                                              ▼
                    ┌───────────────────────────────┐
                    │           running              │  Call /evaluate to parse
                    │  Compare against baseline +    │  Generate per-iteration
                    │  historical best               │  report
                    │  Extract lessons learned        │  docs/iterations/iter{N}.md
                    │  Make decision                  │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │         completed              │
                    │  status="completed",           │
                    │  decision recorded              │
                    └───────────────┬───────────────┘
                                    │
                  ┌──────────┬──────────┬───────┴───────┬─────────┐
                  │          │          │               │         │
              NEXT_ROUND   DEBUG    CONTINUE          PIVOT     ABORT
                  │          │          │               │         │
                  ▼          ▼          ▼               ▼         ▼
            back to plan back to plan → WF11          → WF2   Terminate
            (ordinary    (debug-      (exit WF10,   (idea     project
             round)       oriented)    ablation)      pivot)
                            │
                            └──→ /iterate plan "new hypothesis based on lessons"
                                        │
                                        ▼
                                   (loop back to planned)

            ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
            Optional branch: /iterate ablate (after completed)
            ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄

              /iterate ablate {base_iter} --components "..."
                                │
                        ┌───────┴────────┐
                        │ For each        │
                        │ component:      │
                        │  Train w/o comp │
                        │  Run eval       │
                        │  Record sub-iter│
                        └───────┬────────┘
                                │
                                ▼
                ┌───────────────────────────────────┐
                │ Output comparison table             │
                │ Component | Metric | Delta | Class  │
                │ ─────────────────────────────────  │
                │ contract thresholds preferred       │
                │ fallback: < -1.0 dB → significant  │
                │ fallback: < -0.3 dB → moderate     │
                │ fallback: >= -0.3 dB → minimal     │
                │ fallback: > 0 dB → negative        │
                └───────────────────────────────────┘
```

### 7.3 State File Ownership

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   PROJECT_STATE.json    │     │   iteration_log.json    │
│   Single source of truth│     │   Single source of truth│
│   for stages            │     │   for experiments       │
│                         │     │                         │
│   Write responsibility: │     │   Writer:               │
│     orchestrator owns   │     │     /iterate skill      │
│     stage transitions;  │     │                         │
│     stage skills record │     │                         │
│     artifact metadata   │     │                         │
│                         │     │   Contents:             │
│   Contents:             │     │     iterations[]        │
│     current_stage       │     │     best_iteration      │
│     history[]           │     │     baseline_metrics    │
│     artifacts           │     │                         │
├─────────────────────────┤     ├─────────────────────────┤
│   project_map.json      │     │   CLAUDE.md             │
│   Single source of truth│     │   Global context        │
│   for stable file layout│     │                         │
│                         │     │   Writer:               │
│   Write responsibility: │     │     /init-project       │
│     build-plan creates; │     │     staged incremental  │
│     code-expert/debug   │     │     population          │
│     and stable-file     │     │                         │
│     writers keep synced │     │                         │
│                         │     │                         │
│   Tracks stable files   │     │   ≤80 lines, stable     │
│   only                  │     │   operations guide      │
└─────────────────────────┘     └─────────────────────────┘

┌─────────────────────────┐
│   .auto_iterate/        │
│ Controller runtime state│
│                         │
│ Writer:                 │
│   auto-iterate controller│
│                         │
│ Contents:               │
│   state.json, phase logs│
│                         │
│ Reads (never writes):   │
│   iteration_log.json    │
│   PROJECT_STATE.json    │
└─────────────────────────┘

Key rule: /iterate does not write PROJECT_STATE.json
         orchestrator does not write iteration_log.json
         controller only reads iteration_log.json and PROJECT_STATE.json
         Cross-file information is obtained through "reading"
```

### 7.4 Consistency Anti-Drift Rules

- Always use single definitions: `WF2=idea-debate`, `WF3=refine-idea`, `WF5=baseline`, `WF6=refine-arch/architecture-design`, `WF7=build-plan`, `WF8=code-expert`, `WF9=validate-run`, `WF10=iterate`.
- After WF4 completes, `PROJECT_STATE.json.dataset_paths` and `CLAUDE.md`'s `### Dataset Paths` must be immediately synced. `AGENTS.md` must remain stable but should be checked so it still points operators to `CLAUDE.md` for volatile dataset and environment paths.
- After WF5 completes, `CLAUDE.md`'s `## Environment` must no longer contain placeholder content.
- WF10 `run/eval` must use the baseline/evaluation protocol from WF5 output to determine which metrics to record; training traces and final evaluation metrics are stored separately.
- After any WF10 subcommand completes, `iteration_log.json` is the authoritative experiment state. Any `PROJECT_STATE.json.current_stage.latest_iteration`, `iteration_count`, or `CLAUDE.md Current stage` summary must be synchronized by orchestrator/init-project by reading `iteration_log.json`, not by the auto-iterate controller.
- Iterations missing semantic commits, `run_manifest`, or `lessons` must not be marked as completed.

---

## 8. Quick Reference

**Common commands**:
```
/orchestrator init          # Initialize project
/orchestrator status        # View current status
/orchestrator next          # Advance to next stage
/orchestrator rollback 2    # Roll back to WF2 idea-debate/refine-idea
/orchestrator decision      # Record key decision

/baseline-repro all         # Reproduce all baselines
/validate-run               # WF9 training pipeline validation
/code-review medium         # Review current diff with git metadata and line refs

/iterate plan "hypothesis"  # Plan new iteration (with repeated lessons check)
/iterate code "description" # Implement changes (enforced git commit)
/iterate run config.yaml    # Execute training + auto-collect metrics
/iterate eval path/to/exp   # Evaluate results + make decision
/iterate ablate {base_iter} --components "name:override,..."  # Ablation experiment
/iterate status             # View iteration progress
/iterate log                # Complete iteration history

/code-debug [error info]    # Fix code issues (can be used independently)
/evaluate [log_path]        # Analyze results (can be used independently)
/env-setup refresh          # Refresh environment snapshot after dependency changes

/release validate           # Check submission package completeness
/release package            # Generate submission package
/release submit             # Multi-scene training + packaging
```

**Git branching strategy**: Single-person projects can develop directly on master/main. Team collaboration can optionally use per-stage branches.

**Commit conventions** (choose format by scenario):
- Training-related code changes: `train(research): {description}` or `train(baseline/{name}): {description}`
- Workflow docs/configs: `[WF{n}] {type}: {message}`, type = feat / fix / docs / refactor / exp
