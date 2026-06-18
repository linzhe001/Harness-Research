# Experiment And Build Canvas

## Purpose

Use this asset in `build`, `run`, and `analyze` to keep AI-assisted engineering
and experimentation small, testable, and claim-aware.

## Small Verified Build Pattern

```text
clear requirement
  -> smallest runnable slice
  -> first feedback command
  -> implementation
  -> validation output
  -> semantic commit
```

Every code task should state:

- functionality
- inputs and outputs
- constraints
- non-requirements
- first feedback command
- expected artifact

For AI-assisted coding posture, context discipline, and repeated-fix replanning,
also use `ai-assisted-research-workflow.md`.

## Subtractive MVP

Before adding a file, ask:

- Is it needed for the first runnable claim path?
- Which roadmap slice owns it?
- Which feedback command catches breakage?
- Does it add a public API, dependency, or new term?
- Can it stay run-local until proven reusable?

Foundation slices are allowed, but they are not `build_ready_for_iterate` unless
the runnable smoke/eval/training path and run artifact bundle exist.

## Experiment Canvas

Each WF10 iteration should carry this compact canvas:

| Field | Required content |
|---|---|
| `hypothesis` | Mechanism or observation being tested. |
| `dominant_axis` | Higher, Faster, Stronger, Cheaper, or Broader. |
| `falsifier` | Result that would weaken or kill the idea. |
| `baseline_or_control` | Anchor comparison. |
| `minimum_artifact` | Config, log, metric, checkpoint, report, or figure data needed. |
| `planned_command` | Exact command or manual registration path. |
| `claim_implication` | Claim that becomes stronger, weaker, or blocked. |
| `figure_implication` | Table, trend, ablation, failure case, or none. |

## Run Weight

| Scope | Use when | Required discipline |
|---|---|---|
| `config_only` | Hyperparameter or dataset split change. | Record config and command. |
| `run_local_code` | One-off helper, probe, or plot. | Keep under `runs/wf10/<iter>/` and write manifest. |
| `stable_candidate` | Reusable code likely to enter `src/` or `scripts/`. | Promotion plan and acceptance commands. |
| `delegated_build` | Stable architecture or public interface change. | Route through build/code-debug discipline. |

## Analysis Split

Analyze should not collapse everything into a single metric sentence. Separate:

- metric movement
- training or pipeline health
- comparison validity
- missing controls
- failure modes
- claim support
- next experiment

Decision mapping:

| Finding | Likely decision |
|---|---|
| Metric improves and controls are adequate | `NEXT_ROUND` or `CONTINUE` |
| Pipeline or numerical issue | `DEBUG` |
| Missing baseline/control blocks interpretation | `NEXT_ROUND` with required evidence |
| Main falsifier triggered | `PIVOT` or `ABORT` |
| Result supports paper but needs final matrix | `CONTINUE` toward WF11 |

## Re-Plan Rule

If an AI-generated fix fails repeatedly:

```text
third failed patch
  -> stop patching
  -> restate symptom and evidence
  -> re-plan slice or debug hypothesis
```
