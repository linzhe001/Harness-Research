# Paper And Figure System

## Purpose

Use this asset in `write`, `auto-paper-*`, release claim review, or any paper
structure discussion. It turns paper-writing advice into Harness artifacts.

## Abstract Skeleton

```text
What    -> what problem or task is studied?
Why     -> why does it matter now?
How     -> what is the key idea or construction?
So What -> what evidence shows the contribution matters?
```

Do not fill `So What` from intent alone. It needs Conclusion Evidence.

## Technical Paper Logic

```text
background
  -> limitations of prior work
  -> key idea or goal
  -> challenges
  -> methodology modules
  -> evidence plan
  -> contributions
```

Consistency checks:

- Limitations motivate the key idea or goal.
- Challenges arise from implementing the key idea.
- Each module addresses a challenge.
- Contributions map to modules, results, or section anchors.
- Claims stay inside the approved Claim Boundary.

For paragraph-level layout, contribution mapping, and section blueprints, use
`paper-writing-layouts.md`.

## Benchmark Or Evaluation Logic

```text
evaluation gap
  -> benchmark or data construction pipeline
  -> evaluation framework
  -> empirical findings
  -> optional companion method
```

Required checks:

- The gap is an evaluation dimension, not just a missing leaderboard row.
- Construction is reproducible and quality-controlled.
- Metrics, difficulty tiers, or error taxonomy explain the gap.
- Findings reveal capability boundaries.
- Contamination, split design, and provenance are explicit.

For benchmark/evaluation papers, use `benchmark-evaluation-paper.md` before
patching prose. The benchmark skeleton is not a minor variation of the
technical-paper skeleton.

## Introduction Flow

```text
background and motivation
  -> prior-work limitations
  -> problem essence or goal
  -> key challenges
  -> solution overview
  -> contributions with section anchors
```

For technical papers, the key idea carries the story. For new problem or
benchmark papers, the problem definition or evaluation gap carries more weight.

## Section Blueprint Checks

| Section | Job |
|---|---|
| Abstract | Four-question compressed paper. |
| Introduction | Complete story and contribution map. |
| Problem/Formulation | Define task, constraints, and notation. |
| Method/Framework | Explain why each module exists. |
| Experiments | Answer claims and research questions. |
| Related Work | Fair comparison and explicit difference. |
| Conclusion | Summarize supported contribution and limitations. |

## Figure Roles

| Figure role | Job | Typical placement |
|---|---|---|
| Motivated example | Show failure, gap, or real need. | page 1 or early intro |
| Solution overview | Explain workflow or architecture. | method/framework opening |
| Experimental result | Prove claim or show boundary. | experiments |
| Supporting figure | Clarify detail, appendix, or qualitative case. | body or appendix |

Caption rule:

```text
first sentence = visual thesis or finding
details = setup, panels, axes, and interpretation boundary
```

Every quantitative caption claim must map to a claim row, run artifact, metric
file, table, or citation support row.

For figure contracts, chart selection, visual encoding, and AI sketch limits,
use `scientific-plotting.md`.

## Figure Quality Audit

- vector final format when possible
- readable font after scaling
- color-blind-safe palette
- no color-only encoding
- honest axis ranges
- self-contained labels
- no 3D effects or chartjunk
- caption states the finding and boundary

## Pre-Submission Review

Use this five-part lens:

| Dimension | Blocking question |
|---|---|
| Macro logic | Does the story chain hold from motivation to experiments? |
| Writing detail | Does each paragraph have a job and transition? |
| Grammar/wording | Is wording precise and free of repeated mechanical errors? |
| Format | Are citations, labels, equations, figures, and venue constraints correct? |
| Figure quality | Are figures legible, honest, and supported by evidence? |

Severity:

- `CRITICAL`: blocks submission or central claim.
- `MAJOR`: likely reviewer complaint.
- `MINOR`: polish.

For detailed macro-logic, grammar, LaTeX, figure, and reviewer-value checks,
use `pre-submission-review.md`.

## RUN_REQUEST Rule

When writing finds a missing experiment, ablation, baseline, seed sweep, metric
export, or figure artifact, write a `RUN_REQUEST` instead of inventing support.

Request fields:

- blocking claim
- needed evidence
- minimum artifacts
- suggested `$run` prompt
- acceptance check
