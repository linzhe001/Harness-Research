# Research Supervision Patterns

## Purpose

This reference distills reusable research-supervision patterns from local
reference material into Harness terminology. It is a process reference, not
Conclusion Evidence for any target research project.

The source PDF was converted into this anonymized Markdown asset by extracting
only operational guidance. Identity, affiliation, contact, credit, logo, and
identity-bearing example details were intentionally removed. The diagrams
below are abstracted from the slide structure rather than copied as images.

## Layering Rule

Treat this file as L1 Core invariant guidance. It may shape questions,
checklists, paper planning, figure planning, and iteration analysis, but it
does not prove project facts, dataset availability, baseline strength, metric
results, or Human Approval.

If a pattern below creates a claim about the current project, support that claim
with current project Source Artifacts, Conclusion Evidence, Gate Evidence, or
explicit Approval Evidence.

## Integrated Asset Pack

Use the internal assets under `research-supervision/`.

| Internal asset | Use when |
|---|---|
| `research-supervision/coverage-matrix.md` | Maintainers need to audit source coverage and anonymization decisions. |
| `research-supervision/phd-research-primer.md` | The operator needs the anonymized primer converted from the PDF, including diagrams and writing guidance. |
| `research-supervision/idea-evaluation.md` | Grill or change-intake needs fatal-flaw, problem-type, five-axis, or paradigm checks. |
| `research-supervision/experiment-and-build-canvas.md` | Build, run, or analyze needs small verified slices and experiment canvas fields. |
| `research-supervision/ai-assisted-research-workflow.md` | Build, figure, or writing work uses AI assistance and needs explicit judgment boundaries. |
| `research-supervision/paper-writing-layouts.md` | Write or auto-paper needs paragraph jobs, technical-paper layout, or contribution mapping. |
| `research-supervision/benchmark-evaluation-paper.md` | Write or Grill needs benchmark/evaluation paper design, RQs, construction, and findings. |
| `research-supervision/scientific-plotting.md` | Write or auto-paper-figure needs figure contracts, plotting choices, and visual gates. |
| `research-supervision/paper-and-figure-system.md` | Write needs paper skeletons, figure roles, caption rules, or pre-submission review checks. |
| `research-supervision/pre-submission-review.md` | Write or harden needs final paper readiness and severity classification. |
| `research-supervision/case-patterns.md` | Write needs generic patterns extracted from case-study analyses. |

## Research Pipeline

Use this pipeline as the default mental model when a project feels underspecified:

```text
research direction
  -> concrete problem
  -> technical innovation
  -> experimental evaluation
  -> paper writing
```

Every durable Harness artifact should know which part of this pipeline it
serves. A strong project can explain the handoff between adjacent steps.

## Direction And Problem Framing

Good research directions usually have four properties:

- real demand or a real user need
- novelty that can attract attention
- enough unknown space that the answer is not obvious
- local execution foundation, such as data, code, expertise, or baseline access

Concrete problems split into two broad types:

| Type | Main question | Harness implication |
|---|---|---|
| Old problem | Can we solve a well-defined task better? | Baseline recency, strong evaluation contracts, and fair comparison dominate. |
| New problem or setting | Can we define an important problem nobody has cleanly measured? | Problem definition, data access, measurement validity, and story chain dominate. |

Decision sketch:

```text
candidate idea
  -> is the problem already well defined?
       | yes
       v
     old problem -> latest strong baseline -> better method or cheaper/faster route
       |
       no
       v
     new problem -> real use case -> measurable task -> credible data source
```

For old problems, the improvement axis must be explicit. Use:

- `Higher`: better quality, accuracy, or effectiveness.
- `Faster`: lower wall-clock time, token cost, memory, or compute.
- `Stronger`: better robustness, generalization, or fault tolerance.
- `Cheaper`: less data, annotation, training, or deployment cost.
- `Broader`: transfer to new domains or unify fragmented task families.

For new problems, require:

- a concrete user, system, or field need
- a task definition that can be measured
- a data source or construction path
- a benchmark, metric, or evaluation protocol
- an honest statement of what the paper will not claim

## Grill Checks

During Grill, add these checks only after the initial blocking questions are
clear. Do not turn Grill into a long questionnaire.

### First-Pass Positioning

Ask for one sentence:

```text
Because <field/user/system> now faces <concrete bottleneck>,
we study <problem> and test whether <proposed move> improves <signal>.
```

If this sentence cannot be written without placeholders, keep grilling.

### Fatal-Flaw Screen

Run the screen before optimistic scoring. Report at most two flaws.

| Flaw | Detection question | Typical defense |
|---|---|---|
| No novelty | What is added beyond the closest prior work? | Name one concrete axis where the project differs and wins. |
| Wrong venue or audience | Would recent target-venue papers value this contribution type? | Retarget the venue or reshape the contribution. |
| Weak baseline | Is the baseline current and strong? | Add the strongest recent public baseline or justify an explicit cutoff. |
| Weak motivation | Who benefits if this is solved? | Add a concrete beneficiary and real failure case. |
| Capability mismatch | Can the team finish within the lifecycle and resource limits? | Narrow scope, partner, or pivot. |
| Unverifiable claim | What experiment would prove the main claim? | Design the decisive experiment or weaken the claim. |
| Data or ethics blocker | Is required data or approval accessible? | Secure access before execution or choose another setting. |
| Overbroad scope | Are there more than four distinct contribution types? | Split the work or cut claims. |
| Solution-first idea | Did the idea start from a technique without a problem? | Restart from a concrete failure case. |
| No failure mode | Where does the method fail? | Pre-register limitations and failure cases. |

Severity rule:

- `CRITICAL`: cannot be defended within the project lifecycle.
- `MAJOR`: needs material scoping, literature, or experiment work.
- `MINOR`: can be fixed by focused writing or small checks.

Any `CRITICAL` flaw should route to `pivot` or `abandon`, not prepare.

### Five-Axis Score

Score only from the operator's stated idea and current Source Artifacts:

| Axis | Score | Evidence requirement |
|---|---|---|
| Higher | 1-10 | Specific signal or metric that can improve. |
| Faster | 1-10 | Specific runtime, token, memory, or cost bottleneck. |
| Stronger | 1-10 | Specific robustness or generalization failure. |
| Cheaper | 1-10 | Specific data, annotation, training, or deployment cost. |
| Broader | 1-10 | Specific domain transfer or unification path. |

Useful thresholds:

- One axis at `8+` and a second at `6+`: likely a paper thesis if execution is feasible.
- No axis at `7+`: idea is too vague or needs sharper positioning.
- Three or more axes at `5 or below`: scope likely needs pivot or narrowing.

### Readiness Output Additions

When useful, add these compact rows to Grill artifacts:

- `problem_type`: old problem, new problem, new setting, benchmark/evaluation,
  or mixed.
- `dominant_improvement_axis`: Higher, Faster, Stronger, Cheaper, Broader.
- `main_falsifier`: the observation or metric that would make the idea not worth pursuing.
- `reviewer_risk`: the first objection a skeptical reviewer would raise.

These rows are candidate context, not Approved Contracts.

## Build And Code Patterns

AI-assisted build work should optimize for small verified progress:

```text
clear requirement
  -> smallest runnable slice
  -> first feedback command
  -> implementation
  -> validation output
  -> semantic commit
```

Use the "commander" posture:

- The operator owns problem framing, design tradeoffs, and correctness judgment.
- The agent can accelerate mechanical coding, debugging, refactoring, and test scaffolding.
- Every code task needs inputs, outputs, constraints, non-requirements, and a feedback command.
- If a fix fails repeatedly, step back and re-plan instead of stacking patches.

Build-plan should prefer subtractive MVP thinking:

- Keep only files needed for the first runnable claim path.
- Separate foundation slices from the minimal smoke/eval/training-ready path.
- Bind each slice to one research outcome and one acceptance command.
- Keep new public APIs, dependencies, and terms under an explicit complexity budget.

## Run And Analyze Patterns

Each WF10 iteration should be a small experiment canvas:

| Field | Question |
|---|---|
| Hypothesis | What mechanism or observation is being tested? |
| Dominant axis | Higher, Faster, Stronger, Cheaper, or Broader? |
| Falsifier | What result would make this idea weaker? |
| Baseline or control | What result is the comparison anchored to? |
| Minimum artifact | Which config, log, metric, checkpoint, or report must exist? |
| Claim implication | If it works, what paper claim becomes stronger? |
| Figure implication | Would this produce a result table, trend plot, ablation, or failure case? |

Analyze should separate:

- verified metric movement
- training or pipeline health
- explanation candidates
- missing controls
- claim support
- next experiment

Do not promote a result into a paper claim unless the run artifact bundle and
Experiment Evidence Index support it.

## Paper Logic Patterns

### Abstract

Use the four-question skeleton:

```text
What    -> what problem or task is studied?
Why     -> why is this problem worth a paper now?
How     -> what is the key idea or construction?
So What -> what evidence shows the contribution matters?
```

### Introduction

Treat the introduction as an expanded abstract and compressed paper:

```text
background and motivation
  -> limitations of prior work
  -> problem essence or goal
  -> key challenges
  -> solution overview
  -> contributions with section anchors
```

Every contribution should map to a challenge, method module, result, or section.

### Technical Paper Skeleton

Use this chain before drafting prose:

```text
background
  -> limitations
  -> key idea or goal
  -> challenges
  -> methodology modules
  -> contributions
  -> evidence plan
```

Consistency checks:

- Limitations motivate the key idea or goal.
- Challenges arise from implementing the key idea, not from module names.
- Each methodology module addresses one challenge.
- Contributions cover modules or results that the paper actually delivers.

### Benchmark Or Evaluation Paper Skeleton

Benchmark-style work needs different load-bearing pieces:

```text
evaluation gap
  -> construction pipeline
  -> evaluation framework
  -> empirical findings
  -> optional companion method
```

Required checks:

- The benchmark measures a missing evaluation dimension.
- The construction pipeline is reproducible and quality controlled.
- The evaluation framework has dimensions, tiers, metrics, or error taxonomy.
- Findings reveal capability boundaries, not only a leaderboard.
- Contamination, split design, and data provenance are explicit.

## Figure Patterns

Plan figures from claims, not decoration. Three figures usually carry the
story:

| Figure role | Purpose | Typical representation |
|---|---|---|
| Motivated example | Show the real failure or gap. | Running example, existing vs proposed, or performance teaser. |
| Solution overview | Explain the method without reading details. | Pipeline, system architecture, or multi-layer diagram. |
| Experimental results | Prove a claim or expose a boundary. | Table, grouped bar, line chart, scatter, ablation, or error breakdown. |

Caption rule:

```text
first sentence = finding or visual thesis
remaining caption = setup, axes/panels, and key interpretation boundary
```

Universal figure audit:

- vector output for final figures when possible
- readable font after scaling
- color-blind-safe palette and no color-only encoding
- honest axis ranges
- self-contained labels
- no chartjunk or 3D effects
- every quantitative caption claim maps to evidence

When a PDF, Markdown note, or draft suggests a figure without the data needed
for a quantitative panel, keep it conceptual, mark `USER_GATE`, or create a
`RUN_REQUEST`.

## Pre-Submission Review Pattern

Use this as the hardening lens for paper-facing work:

| Dimension | Blocking question |
|---|---|
| Macro logic | Does the story chain hold from motivation to experiments? |
| Writing detail | Does every paragraph have a job and transition? |
| Grammar and wording | Are sentences simple, precise, and free of repeated errors? |
| Format | Are references, labels, equations, captions, and venue constraints correct? |
| Figure quality | Are figures legible, honest, and caption-supported? |

Reviewer-value checklist:

- Novel Problem: is the problem or setting useful and clearly defined?
- Novel Method: is the method more than a simple combination?
- Nice Story: is the logic easy to follow?
- Nice Presentation: are figures, layout, grammar, and formatting professional?
- Strong Experiments: are baselines current, settings fair, and controls appropriate?

Common blockers:

- old problem with a shallow combination of existing methods
- weak or outdated baseline
- missing decisive experiment
- vague contribution list
- raster or unreadable figures
- overclaiming beyond the approved Claim Boundary

## Phase Routing Summary

| Entrypoint | Use this reference for |
|---|---|
| `grill` | Problem type, fatal flaws, five-axis scoring, falsifier, reviewer risk. |
| `build` | Subtractive MVP, smallest runnable slice, clear requirement, small-step validation. |
| `run` | Experiment canvas, dominant axis, falsifier, minimum artifact, claim and figure implication. |
| `analyze` | Metric movement, training health, missing controls, claim support, next decision. |
| `write` | Abstract/intro skeleton, technical or benchmark paper logic, figure planning, pre-submission review. |
| `change` | Route deltas that affect problem framing, evaluation, claim boundary, or paper skeleton back to the owning stage. |
