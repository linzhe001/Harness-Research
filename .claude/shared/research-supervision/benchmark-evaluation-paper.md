# Benchmark And Evaluation Paper Asset

## Purpose

Use this asset when a paper's contribution is an evaluation dimension,
benchmark, dataset, judge, protocol, or capability-boundary analysis rather than
only a new method.

This asset gives paper structure guidance. It does not prove a benchmark is
valid, uncontaminated, or ready.

## Core Difference

| Question | Technical paper | Benchmark/evaluation paper |
|---|---|---|
| Main contribution | new method or mechanism | new evaluation dimension, dataset, protocol, or findings |
| Introduction axis | key idea or mechanism | evaluation gap plus benchmark design rationale |
| Problem definition | short bridge | load-bearing contribution |
| Heavy section | method | construction pipeline plus evaluation framework |
| Experiment purpose | prove the method wins | reveal capability boundaries and failure structure |
| Key visuals | method overview and result chart | running example, comparison table, pipeline, fine-grained analysis |

## Five Pillars

| Pillar | Required question |
|---|---|
| Research gap | What blind spot would remain if existing benchmarks were solved perfectly? |
| Construction pipeline | How are examples built, filtered, annotated, and quality controlled? |
| Evaluation framework | What dimensions, tiers, metrics, or taxonomy make failures diagnosable? |
| Empirical findings | What does the benchmark reveal beyond a leaderboard? |
| Companion method | Optional: does the benchmark provide a signal that improves models? |

If one of the first four pillars is missing, route the paper back to Grill,
protocol, data construction, or experiment planning before polishing prose.

## Introduction Flow

```text
background and core scenario
  -> running example
  -> limitations of existing benchmarks
  -> research questions
  -> design considerations
  -> benchmark proposal
  -> contributions
```

The running example and comparison table usually carry the early story:

- `Figure 1`: concrete task complexity or evaluation failure.
- `Table 1`: existing benchmark comparison against the missing dimension.

## Design Canvas

| Field | Content |
|---|---|
| capability | exact capability or behavior being evaluated |
| blind_spot | assumption or missing dimension in existing evaluation |
| task_scope | included and excluded behaviors |
| design_goals | coverage, diagnostics, scalability, quality, contamination resistance |
| taxonomy | capability x difficulty, phenomenon x severity, or multi-dimensional quality |
| metrics | metric, scoring method, range, automation level, human-validation plan |
| data_sources | provenance, licensing, split design, contamination risks |
| construction_pipeline | collection, synthesis or transformation, annotation, QC |
| expected_findings | capability boundary, error taxonomy, behavior bias, human-model gap |
| release_boundary | what code/data/protocol can be released and what remains private |

## Construction Pipeline

Use this diagram as the minimum paper-facing pipeline:

```text
source artifacts
  -> selection / filtering
  -> transformation or synthesis
  -> annotation or judging protocol
  -> automatic checks
  -> human or expert validation
  -> split / version / contamination audit
  -> benchmark statistics
```

Quality-control evidence should include at least one of:

- inter-annotator agreement or adjudication protocol
- automatic validators and rejection rates
- expert audit sample size and failure categories
- duplicate, leakage, or contamination checks
- reproducible scripts for construction and evaluation

## Experiment Structure

Organize experiments by research questions, not by whatever result was easiest
to run:

| Section | Job |
|---|---|
| Overall performance | show broad capability boundary across model families or systems |
| Fine-grained analysis | diagnose sub-capabilities, difficulty, or error types |
| Human or reference baseline | anchor the evaluation when feasible |
| Prompting/method factors | test strategies, scale, domain knowledge, or adaptation |
| Case studies | show concrete success and failure mechanisms |
| Opportunities | turn findings into future research directions |

After each major analysis, write a short `Finding X` statement only if the
supporting metric, table, or case evidence exists.

## Harness Integration

- `grill`: classify the idea as benchmark/evaluation when the gap itself is the
  contribution.
- `prepare`: treat data provenance, construction, and annotation plans as
  acquisition or protocol inputs.
- `build`: build reproducible construction/evaluation slices before paper prose.
- `run` / `analyze`: map experiments to RQs and refresh experiment evidence
  before claim writing.
- `write`: choose this skeleton instead of the technical-paper skeleton.

## Submission Checklist

- The gap is specific, surprising, and consequential.
- Existing benchmarks are compared along the missing dimension.
- Design goals and task scope are explicit.
- Pipeline steps have inputs, outputs, QC, and reproducibility story.
- Metrics and taxonomy diagnose failures, not only rank systems.
- Findings are backed by tables, plots, or case evidence.
- Contamination, split design, data provenance, and limitations are stated.
- Any companion method is framed as optional evidence, not required for the
  benchmark's existence.
