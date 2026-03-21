# CV Research Workflow Complete Guide

This document provides a detailed introduction to the CV research workflow system built on Claude Code Skills.
The system drives a CV research project from "idea" to "competition submission / paper-ready" through a fully automated process, managing and ensuring quality at every step.

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

### 1.2 State Ownership

Each state file has a single write-responsible owner to avoid multi-source divergence:

| File | Sole Writer | Purpose |
|------|------------|---------|
| `PROJECT_STATE.json` | orchestrator + each WF skill | Stage transitions (single source of truth for stages) |
| `iteration_log.json` | iterate skill | Experiment history (single source of truth for experiments) |
| `project_map.json` | build-plan generates, code-debug maintains | Code structure (single source of truth for architecture, stable files only) |
| `CLAUDE.md` | init-project generates in stages | Global context for each Claude Code session |

**Key rule**: iterate **does not write** PROJECT_STATE.json; orchestrator **does not write** iteration_log.json. Cross-file information is obtained through **reading**.

### 1.3 Workflow Overview

```
┌──────────────── Early Research & Design ────────────────┐
│                                                          │
│  ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐   │
│  │ WF1 │ →  │ WF2 │ →  │ WF3 │ →  │ WF4 │ →  │ WF5 │   │
│  │survey│    │ arch│    │check│    │ data│    │ base│   │
│  │      │    │      │ ←──│NO-GO│    │      │    │ line│   │
│  └─────┘    └──↑───┘    └─────┘    └─────┘    └─────┘   │
│                │                                          │
└────────────────│──────────────────────────────────────────┘
                 │
┌────────────────│──── Implementation & Validation ────┐
│                │                                      │
│  ┌─────┐    ┌──┴──┐    ┌──────┐                      │
│  │ WF6 │ →  │ WF7 │ →  │WF7.5 │                      │
│  │ plan│    │ code│    │valid │                      │
│  └─────┘    └─────┘    └──┬───┘                      │
│                        FAIL│→ /code-debug → retry     │
│                            │                          │
└────────────────────────────│──────────────────────────┘
                          PASS│
┌─────────────────────────────│── Iterative Optimization ──────────────┐
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────┐            │
│  │                    WF8 Iteration                      │            │
│  │                                                       │            │
│  │    /plan ──→ /code ──→ /run ──→ /eval ──→ decision   │            │
│  │      ↑                                     │          │            │
│  │      │              DEBUG                  │          │            │
│  │      └─────────────────────────────────────┘          │            │
│  │                                                       │            │
│  │    Optional: /ablate (component contribution analysis)│            │
│  └───────────────────────┬───────────────────────────────┘            │
│                          │                                            │
│           ┌──────────────┼──────────────┐                            │
│        CONTINUE        PIVOT          ABORT                          │
│           │              │              │                             │
│           ▼              │              ▼                             │
│  ┌──────┐   ┌──────┐    │           Terminate project                │
│  │ WF9  │ → │ WF10 │    │                                            │
│  │ablate│   │submit│    └──→ Rollback to WF2 (re-architect)          │
│  └──────┘   └──────┘                                                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

Utility skills (non-numbered stages):
- `/code-debug` — Code fixes (called by /iterate code or used independently)
- `/evaluate` — Result analysis (called by /iterate eval or used independently)
- `/env-setup` — Maintenance tool; used for environment refresh after dependency changes, not a main workflow prerequisite

---

## 2. Orchestrator — Central Dispatcher

**Invocation**: `/orchestrator [init|status|next|rollback|decision]`

The orchestrator does not perform specific research work, but manages the state transitions of the entire workflow:

- **`init`** — Initialize project: create directory structure, generate PROJECT_STATE.json, call `/init-project init` to generate minimal CLAUDE.md
- **`status`** — View current progress: includes stage consistency checks, reads iteration_log.json additionally during WF8
- **`next`** — Advance to next stage: verify prerequisites (are artifacts complete, any blockers), then call the corresponding skill
- **`rollback`** — Roll back to a specified stage: preserves history, does not delete any artifacts
- **`decision`** — Record key decisions: content, reasoning, alternatives considered

**Auto-trigger**: The `next` command automatically calls `/init-project update` to update CLAUDE.md after stage completion (upon WF1/WF2/WF4/WF5/WF6 completion).

---

## 3. Stage Details

### WF1–WF4: Survey → Architecture → Deep Check → Data

| Stage | Skill | Output | Decision |
|-------|-------|--------|----------|
| WF1 survey-idea | `/survey-idea` | docs/Feasibility_Report.md | PROCEED/PIVOT/ABANDON |
| WF2 refine-arch | `/refine-arch` | docs/Technical_Spec.md | — |
| WF3 deep-check | `/deep-check` | docs/Sanity_Check_Log.md | GO/CONDITIONAL GO/NO-GO |
| WF4 data-prep | `/data-prep` | docs/Dataset_Stats.md + data pipeline + CLAUDE.md dataset path sync | — |

### WF5: Baseline Reproduction (with Mandatory Gate)

| | |
|---|---|
| **Skill** | `/baseline-repro [baseline_name or 'all']` |
| **Output** | `docs/Baseline_Report.md` + baseline_metrics + evaluation_protocol |
| **Gate** | Baseline_Report.md must exist, each baseline's status must be verified/partial (cannot be untested) |

If intentionally skipping certain baselines, they must be marked as `partial` with reasons explained in the report.
WF5 is also responsible for creating the first runnable environment and syncing `CLAUDE.md`'s `## Environment` and baseline summary.

### WF6–WF7: Planning → Coding

| Stage | Skill | Output |
|-------|-------|--------|
| WF6 build-plan | `/build-plan` | docs/Implementation_Roadmap.md + project_map.json |
| WF7 code-expert | `/code-expert` | Complete project code |

### WF7.5: Code Review + Training Pipeline Validation (Gate)

| | |
|---|---|
| **Skill** | `/validate-run [config_path]` |
| **Review Items** | Codex code review (new code vs baseline equivalence: data pipeline, model, loss, evaluation metrics, common ML bugs) |
| **Validation Items** | 100-step training, checkpoint save/load, eval pipeline, wandb connection, git_snapshot |
| **Gate** | PASS → WF8, REVIEW → user confirms then continue or fix, FAIL → /code-debug to fix |

Ensures no code correctness or infrastructure issues are encountered during iteration.

### WF8: Structured Experiment Iteration (Core)

| | |
|---|---|
| **Skill** | `/iterate [plan|code|run|eval|ablate|status|log]` |
| **Output** | iteration_log.json (continuously updated), best checkpoint |
| **Decision** | CONTINUE → WF9 / DEBUG → new iteration / PIVOT → WF2 / ABORT |

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
For each component, generates a `{base_iter}_no_{component}` sub-iteration, auto-evaluates after training, and classifies by delta:

| Delta Range | Classification |
|-------------|----------------|
| < -1.0 dB | `significant` — core component |
| < -0.3 dB | `moderate` — contributes |
| >= -0.3 dB | `minimal` — can be simplified |
| > 0 dB | `negative` — better without it |

Supports resumption: already completed sub-iterations are automatically skipped.

**Other key features**:
- **Persistent context**: stored at `.claude/iterations/iter{N}/context.json`, symlink as compatibility layer
- **Enforced git commit**: if no commit hash after code subcommand completes, stays in coding status without advancing
- **Repeated lessons check**: plan phase scans known lessons, warns about repeated failure patterns
- **Screening protocol**: non-architecture/loss changes should do a 5K-10K proxy run first

### WF9: Formal Ablation Experiments

| | |
|---|---|
| **Skill** | `/final-exp [stage_report_path]` |
| **Output** | docs/Final_Experiment_Matrix.md |
| **Prerequisite** | WF8 final iteration decision is CONTINUE |

Design a complete experiment matrix meeting top-venue standards:
- **Ablation experiments**: each innovation component ON/OFF, isolating individual contributions (can reuse preliminary results from WF8 `/iterate ablate`)
- **Hyperparameter search**: search space and strategy for key hyperparameters
- **Robustness tests**: different resolutions, extreme scenarios, OOD data
- **Cross-dataset evaluation**: verify generalizability
- **Compute budget**: estimate total GPU hours, plan execution order

### WF10: Submission & Release

| | |
|---|---|
| **Skill** | `/release [submit|package|validate]` |
| **Output** | Submission package (multi-scene rendering + packaging + filename validation) |
| **Prerequisite** | WF9 ablation experiments completed |

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
- Provide CONTINUE/DEBUG/PIVOT/ABORT decision

**Per-iteration reports**: when called from /iterate eval, writes to `docs/iterations/iter{N}.md`.
`docs/Stage_Report.md` serves as the latest summary index.

---

## 5. Key Feature Details

### 5.1 Stable vs Volatile File Layering

project_map.json only tracks **stable architecture files**:
- src/ core modules
- baselines/ subdirectories
- Core configs and scripts (listed in CLAUDE.md Entry Scripts)

**Volatile experiment assets** are not tracked:
- per-iteration scripts (run_*.sh, run_ablation_*.py)
- Temporary experiment configs
- Everything under experiments/

### 5.2 Pre-Training Git + wandb Integration

Three layers of safeguards ensure complete version records for every training run:

1. **Claude's semantic commits** (rule-enforced)
2. **git_snapshot.py safety net** (in code)
3. **wandb + checkpoint records** (in code)

### 5.3 Codex Cross-Validation

| Trigger Point | Trigger Condition | Review Target | Review Focus |
|---------------|-------------------|---------------|--------------|
| WF3 deep-check | **Always triggered** (critical gate) | Technical_Spec technical approach | Find missed risks and failure modes |
| WF7.5 validate-run | **Always triggered** (code entry gate) | src/ new code vs baselines/ reference impl | Baseline equivalence: data pipeline, model computation, loss, evaluation metrics |
| WF8 /iterate plan | **Selectively triggered**: new loss family, architecture changes, post-PIVOT, 3 consecutive DEBUGs | Single iteration hypothesis | Hypothesis validation, avoid repeated failures |

Recorded values: `"used"` / `"skipped_low_value"` / `"unavailable"` (no longer using null)

### 5.4 CLAUDE.md Staged Generation

CLAUDE.md is maintained as a **stable operations guide** (≤80 lines), without fast-changing experiment content.
Fast-changing content (current best, current risks, next experiment) resides in iteration_log.json and MEMORY.md.

| Timing | Content Added |
|--------|--------------|
| `init` | Environment placeholder + Workflow overview |
| After WF1 | Idea description |
| After WF2 | Tech Stack details |
| After WF4 | Dataset paths and statistics |
| After WF5 | Baseline metrics reference |
| After WF6 | Project Structure + Core Artifacts |
| After WF7 first experiment | Entry Scripts (lock entry scripts) |

### 5.5 Automated Training Execution

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

### 5.6 Per-iteration Reports

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

```
┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌─────┐  ┌────┐  ┌──────┐  ┌──────┐
│WF1 │→ │WF2 │→ │WF3 │→ │WF4 │→ │WF5 │→ │WF6 │→ │WF7 │→ │WF7.5│→ │WF8 │→ │ WF9  │→ │ WF10 │
│surv│  │arch│  │chck│  │data│  │base│  │plan│  │code│  │valid│  │iter│  │ablate│  │submit│
└────┘  └─┬──┘  └─┬──┘  └────┘  └────┘  └────┘  └────┘  └──┬──┘  └─┬──┘  └──────┘  └──────┘
          ↑       │                                          │       │
          │    NO-GO → rollback to WF2                       │       │
          │                                            FAIL → fix    │
          ↑                                                          │
          │  PIVOT                                                   │
          └──────────────────────────────────────────────────────────┘
```

After each stage completes, the orchestrator auto-triggers `/init-project update` to update CLAUDE.md.

### 7.2 WF8 Internal Iteration State Machine (Managed by iteration_log.json)

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
                  ┌─────────┬───────┴───────┬─────────┐
                  │         │               │         │
               CONTINUE   DEBUG           PIVOT     ABORT
                  │         │               │         │
                  ▼         ▼               ▼         ▼
               → WF9     Back to plan    → WF2    Terminate
              (ablation) (new hypothesis) (re-arch)  project
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
                │ < -1.0 dB → significant (core)     │
                │ < -0.3 dB → moderate (contributes) │
                │ >= -0.3  → minimal (simplifiable)  │
                │ > 0 dB   → negative (better w/o)   │
                └───────────────────────────────────┘
```

### 7.3 State File Ownership

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   PROJECT_STATE.json    │     │   iteration_log.json    │
│   Single source of truth│     │   Single source of truth│
│   for stages            │     │   for experiments       │
│                         │     │                         │
│   Writer:               │     │   Writer:               │
│     orchestrator        │     │     /iterate skill      │
│     each WF skill       │     │                         │
│                         │     │   Contents:             │
│   Contents:             │     │     iterations[]        │
│     current_stage       │     │     best_iteration      │
│     history[]           │     │     baseline_metrics    │
│     artifacts           │     │                         │
├─────────────────────────┤     ├─────────────────────────┤
│   project_map.json      │     │   CLAUDE.md             │
│   Single source of truth│     │   Global context        │
│   for architecture      │     │                         │
│                         │     │   Writer:               │
│   Writer:               │     │     /init-project       │
│     build-plan generates│     │     staged incremental  │
│     code-debug maintains│     │     population          │
│                         │     │                         │
│   Tracks stable files   │     │   ≤80 lines, stable     │
│   only                  │     │   operations guide      │
└─────────────────────────┘     └─────────────────────────┘

Key rule: /iterate does not write PROJECT_STATE.json
         orchestrator does not write iteration_log.json
         Cross-file information is obtained through "reading"
```

### 7.4 Consistency Anti-Drift Rules

- Always use single definitions: `WF5=baseline`, `WF6=build-plan`, `WF7=code-expert`, `WF7.5=validate-run`, `WF8=iterate`.
- After WF4 completes, `PROJECT_STATE.json.dataset_paths` and `CLAUDE.md`'s `### Dataset Paths` must be immediately synced.
- After WF5 completes, `CLAUDE.md`'s `## Environment` must no longer contain placeholder content.
- WF8's `run/eval` must use the baseline/evaluation protocol from WF5 output to determine which metrics to record; training traces and final evaluation metrics are stored separately.
- After any WF8 subcommand completes, `PROJECT_STATE.json.current_stage.latest_iteration`, `iteration_count`, and `CLAUDE.md Current stage` must be consistent with the latest iteration in `iteration_log.json`.
- Iterations missing semantic commits, `run_manifest`, or `lessons` must not be marked as completed.

---

## 8. Quick Reference

**Common commands**:
```
/orchestrator init          # Initialize project
/orchestrator status        # View current status
/orchestrator next          # Advance to next stage
/orchestrator rollback 2    # Roll back to WF2
/orchestrator decision      # Record key decision

/baseline-repro all         # Reproduce all baselines
/validate-run               # WF7.5 training pipeline validation

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
