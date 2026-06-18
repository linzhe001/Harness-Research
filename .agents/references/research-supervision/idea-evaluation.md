# Idea Evaluation Asset

## Purpose

Use this asset in `grill`, `change`, or early `write` planning when an idea
needs structured pressure-testing. It converts advisor-style idea review into
Harness candidate context.

This asset does not approve a project, baseline, dataset, or Claim Boundary.

## First-Pass Story

Try to write:

```text
Because <field/user/system> faces <bottleneck>,
we study <problem> and test whether <move> improves <signal>.
```

If the sentence cannot be written without placeholders, keep the Grill round
open.

## Problem Type

| Type | Primary contribution | Main risk |
|---|---|---|
| Old problem | better method, system, assumption, or efficiency | weak baseline or marginal improvement |
| New problem | useful problem definition and measurement | vague motivation or unverifiable claim |
| New setting | known task under new constraints | setting not important enough |
| Benchmark/evaluation | missing evaluation dimension and reproducible construction | leaderboard without findings |
| Mixed | two or more of the above | overbroad paper scope |

Record `problem_type` in Grill artifacts when it changes the next safe action.

## Lifecycle And Capability Fit

An idea has a shelf life. Fast-moving application work may become stale within
months, while theory, data-intensive, or systems work may justify a longer
cycle. During Grill, record lifecycle risk when it changes feasibility.

| Category | Typical lifecycle | Fit signal | Main mismatch |
|---|---|---|---|
| Application research | 3-6 months | strong coding and fast experiment execution | slow implementation or weak baseline access |
| Foundational theory | 6-12 months | mathematical depth and sustained focus | weak theory background or short timeline |
| Cross-disciplinary | 6-9 months | domain expertise plus CS execution | missing study protocol, users, or approvals |
| Frontier exploration | 3-9 months | quick experiments plus deep analysis | field moves faster than the team can validate |
| Data-intensive | 6-12 months | data engineering and scalable evaluation | unclear data source or annotation budget |
| Innovative technique | 12+ months | strong foundations and tolerance for risk | too ambitious for current resources |

Capability check:

- effective weekly research time
- implementation depth
- data or annotation access
- compute and infrastructure
- review cadence
- venue timing

Three or more mismatch flags should route to narrowing, collaboration,
timeline change, or pivot before prepare.

## Fatal-Flaw Screen

Run before optimistic scoring. Report at most two flaws.

| ID | Flaw | Detection | Defense |
|---|---|---|---|
| F1 | No novelty | Cannot name the delta over closest prior work. | State the exact axis where the work differs and wins. |
| F2 | Wrong audience | Target venue values a different contribution type. | Retarget venue or reshape contribution. |
| F3 | Weak baseline | Baseline is outdated, weak, or non-executable. | Add current strong baseline or justify cutoff. |
| F4 | Weak motivation | No concrete beneficiary or failure case. | Add real user/system/field need. |
| F5 | Capability mismatch | Resources, skill, compute, or time do not fit. | Narrow, partner, stage, or pivot. |
| F6 | Unverifiable claim | No planned experiment can prove the claim. | Design decisive experiment or weaken claim. |
| F7 | Access blocker | Data, model, approval, or licensing is unavailable. | Secure access before execution or change scope. |
| F8 | Overbroad scope | More than four contribution types. | Split work or cut claims. |
| F9 | Solution-first | Technique searches for a problem. | Restart from a real failure case. |
| F10 | No failure mode | Method is framed as universal. | Pre-register limitations and failure cases. |

Severity:

- `CRITICAL`: not defensible within lifecycle; route to `pivot` or `abandon`.
- `MAJOR`: requires material scoping, literature, or experiment work.
- `MINOR`: fixable with focused writing or small checks.

## Five-Axis Score

Score only from current operator input and Source Artifacts.

| Axis | What it means | Strong evidence |
|---|---|---|
| Higher | better accuracy, quality, or effectiveness | targeted metric and mechanism |
| Faster | lower wall-clock, token, memory, or compute cost | quantified bottleneck and speed path |
| Stronger | robustness, generalization, fault tolerance | named failure mode or OOD setting |
| Cheaper | lower data, annotation, training, or deployment cost | cost factor or reduced resource path |
| Broader | transfer, unification, or cross-domain reuse | non-obvious domain bridge or common abstraction |

Interpretation:

- `8+` on one axis and `6+` on another can support a paper thesis.
- No axis at `7+` means the idea is probably under-specified.
- Three or more axes at `5 or below` suggests narrowing or pivot.

## Paradigm Probe

Use only when the operator is asking for a stronger or more disruptive angle:

| Probe | Question |
|---|---|
| First principles | Which field assumption is being challenged? |
| Elephant in the room | Which known failure is everyone avoiding? |
| Technology cycle | What recent capability makes this newly feasible? |
| Hamming test | If solved, would the field's practice change? |

Two or more credible yes answers means the idea may deserve a deeper Grill
round rather than a narrow implementation plan.

## Feasibility Gate

Before moving from Grill to prepare, make the decisive experiment concrete:

| Gate | Required answer |
|---|---|
| Baseline | strongest executable baseline or explicit `baseline_repo_missing` |
| Data | source, access, size, target path, and approval blocker |
| Metric | primary signal and acceptable comparison protocol |
| Falsifier | result that would weaken or kill the idea |
| Minimum artifact | config, log, metric, report, or figure data needed first |
| Claim boundary | strongest claim allowed if the first evidence succeeds |

## Grill Output Fields

When relevant, add:

- `problem_type`
- `dominant_improvement_axis`
- `fatal_flaw_status`
- `main_falsifier`
- `reviewer_risk`
- `capability_or_access_blocker`

These are candidate context. They are not Approved Contracts.
