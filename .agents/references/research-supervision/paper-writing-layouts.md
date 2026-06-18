# Paper Writing Layout Asset

## Purpose

Use this asset in `write`, `auto-paper-layout`, `auto-paper-argument`, and
early paper planning. It separates the technical-paper skeleton from
benchmark/evaluation skeletons and gives concrete paragraph jobs.

It is not a substitute for author evidence, citations, or approved Claim
Boundaries.

## Abstract

```text
What    -> what problem or task is studied?
Why     -> why does this problem matter now?
How     -> what is the key idea, method, or construction?
So What -> what evidence shows the contribution matters?
```

The `So What` sentence must come from experiment evidence, not intent.

## Technical Paper Introduction

```text
P1 background and motivation
  -> P2 limitations of existing work
  -> P3 problem essence, hard constraints, or goal
  -> P4 key challenges
  -> P5 solution overview with challenge-module mapping
  -> P6 contributions with section anchors
```

### Paragraph Jobs

| Paragraph | Job | Common failure |
|---|---|---|
| P1 | name the task and concrete running example | opens with a technique instead of a problem |
| P2 | list at most three specific limitations | vague "existing work is insufficient" claim |
| P3 | state problem essence and hard constraints | goal becomes a list of disconnected sub-goals |
| P4 | explain why the problem is non-trivial | challenges describe the proposed method instead of the problem |
| P5 | map each challenge to a module or mechanism | reviewers must infer why modules exist |
| P6 | list 3-4 delivered contributions with section anchors | contributions promise unsupported work |

For a new problem or setting paper, P3 is load-bearing and may be longer.
For a method paper, the key idea or mechanism carries more of the story.

## Running Example

A running example should be:

- real or grounded in real artifacts
- specific enough to show a concrete failure
- small enough to understand quickly
- reused in the introduction, method walkthrough, and case study
- connected to the motivated example figure

Avoid multiple unrelated examples. If the example disappears after the
introduction, the story is not yet coherent.

## Contribution Alignment

Every contribution should map to at least one of:

- a problem or setting definition
- a key method module
- a benchmark, dataset, or protocol artifact
- a result, finding, ablation, or release artifact
- a section that actually delivers it

Reject contribution bullets that only say "extensive experiments", "new
framework", "comprehensive analysis", or "state-of-the-art performance" without
scope, evidence, and section delivery.

## Section Blueprint

| Section | Job |
|---|---|
| Problem/Formulation | define task, notation, scope, constraints, and example |
| Method/Framework | give overview first, then modules ordered by novelty and dependency |
| Experiments | answer claims and research questions with fair baselines and controls |
| Related Work | credit prior work and state exact differences without copying prose |
| Limitations | state unsupported settings, data limits, and failure cases |
| Conclusion | summarize solved problem, supported evidence, and remaining boundary |

Method sections should lead with the overall architecture or workflow before
details. Simple components can be explained inline; complex components deserve
their own subsections. If a component has no novelty or claim role, keep it
short.

## Experiment Writing

Experiment prose should state:

```text
goal of comparison
  -> dataset / protocol / metric
  -> baseline set
  -> result
  -> why the result happened
  -> claim implication
```

Each main module needs an ablation or a documented reason why ablation is not
feasible. Each result paragraph should extract a finding, not only report a
number.

## Consistency Gate

Before patching prose, check:

- limitations motivate challenges
- challenges map to method modules
- contributions map to sections
- figures use the same module names as prose
- experiment metrics match the active evaluation protocol
- claims stay inside Claim Boundary and evidence support
