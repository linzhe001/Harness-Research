# Anonymized Research Primer

## Purpose

This asset converts a local research-primer slide deck into a reusable Harness
Markdown asset. Personal identity, affiliation, contact, credit, logo, and
identity-bearing examples were removed. Only operational research guidance is
kept.

This file is process guidance. It is not Conclusion Evidence for any project.

## End-To-End Path

The deck's central workflow can be represented as:

```text
research direction
  -> concrete problem
  -> technical innovation
  -> experimental evaluation
  -> paper writing
```

Harness mapping:

| Primer step | Harness owner |
|---|---|
| research direction | `grill`, WF1-WF3 bridge, or `change` for a new direction |
| concrete problem | `grill`, `refine-idea`, Claim Boundary review |
| technical innovation | `refine-arch`, `build-plan`, `build` |
| experimental evaluation | `prepare`, `run`, `analyze` |
| paper writing | `write`, `auto-paper-*`, release claim review |

## Choosing A Direction

A direction is worth sustained work when it has:

- real demand or a concrete usage context
- novelty that can attract a reader's attention
- enough unknown space that the answer is not obvious
- local foundation such as data access, code access, expertise, or baseline
  familiarity

Direction finding is not a one-shot prompt. It normally needs reading, talks,
conference papers, cross-field scanning, and repeated discussion.

## Choosing A Problem

Concrete research problems split into old-problem and new-problem paths:

```text
candidate direction
  -> old well-defined problem?
       | yes
       v
     improve current baseline
       | no
       v
     define and justify a new problem or setting
```

Old problem:

- The task is already defined.
- The contribution must be a better method, stronger system, cleaner
  assumption, cheaper path, or broader setting.
- Baseline strength and experimental fairness are central.

New problem or setting:

- The problem definition itself carries much of the contribution.
- The paper needs a credible real-world need, measurable task, data path, and
  evaluation protocol.
- The story must explain why a new demand, technology, or environment makes
  the problem timely.

## Problem Value Test

Use this decision table during `grill`:

| Question | Strong answer |
|---|---|
| Who benefits? | A concrete user, system, field, or evaluation need. |
| Why now? | A new demand, technology shift, data source, deployment condition, or failure mode. |
| What is measurable? | A metric, benchmark, human judgment protocol, or reproducible qualitative standard. |
| What is the closest baseline? | A current executable baseline or a clear `baseline_repo_missing` blocker. |
| What would falsify it? | A result that would make the direction not worth more investment. |

## Literature Reading Modes

When looking for a direction:

- read broadly
- focus on ideas, problem settings, and failure modes
- avoid over-optimizing details too early

When a direction is selected:

- read deeply
- inspect experiments, datasets, code, and assumptions
- reproduce or at least run the closest code when feasible
- read critically and identify the decisive weakness

## Research Operating Habits

The operational lesson is simple:

```text
plan clearly -> execute quickly -> validate honestly -> summarize lessons
```

Useful habits:

- protect research time
- avoid repeatedly switching ideas without extracting lessons
- understand prior work before claiming novelty
- write and test code carefully
- summarize mistakes and negative results
- use tools, but keep judgment with the researcher

Common failure modes:

- no real interest in the problem
- shallow understanding of prior work
- rushing without understanding
- careless experiments or writing
- avoiding hard implementation or evaluation work

## Paper Value Lens

A work's paper value depends on:

- problem novelty
- method novelty
- technical or theoretical depth
- experiment quality against existing work
- writing structure and presentation quality

Reviewer lens:

| Positive signal | Negative signal |
|---|---|
| Novel Problem | Old problem plus shallow method combination |
| Novel Method | Method is weaker than current strong baselines |
| Nice Story | Reader must guess the logic |
| Nice Presentation | Poor figures, grammar, layout, or formatting |
| Strong Experiments | Missing strong baselines or unfair settings |

## Abstract Diagram

The abstract is the compressed paper:

```text
What    -> what problem is studied?
Why     -> why does it matter now?
How     -> what is the key idea?
So What -> what evidence shows impact?
```

## Introduction Diagram

The introduction expands the abstract:

```text
motivation / background
  -> limitation of prior work
  -> problem or goal
  -> key observation / idea
  -> challenges
  -> solution overview
  -> contributions and evidence preview
```

High-risk introduction failures:

- no concrete motivation
- unclear difference from existing methods
- contributions not mapped to sections or evidence
- no running example for a complex method
- overstating claims before experiments support them

## Overview / Framework Section

The overview section should let a reader understand the method before details:

```text
section leading text
  -> whole workflow or architecture
  -> module purpose
  -> which challenge each module addresses
  -> pointers to detailed subsections
```

Requirements:

- self-contained
- figure-supported
- clear module names
- each technical point tied to a challenge
- no dependence on later details for basic understanding

## Technical Detail Section

Technical writing should proceed from simple to complex:

```text
why this design exists
  -> plain-language core idea
  -> definitions and notation
  -> algorithm or module
  -> example walkthrough
  -> complexity, limitation, or implementation note
```

Use figures, tables, formulas, pseudocode, and examples when they reduce reader
load. Do not assume the reader will infer the contribution unaided.

## Related Work

Related work should:

- state the concrete difference from each relevant line of work
- be fair to prior contributions
- avoid distorting prior claims
- use citation formatting consistently
- avoid copying another paper's wording

## Conclusion

The conclusion should summarize contribution and evidence without repeating the
introduction verbatim:

```text
what was solved
  -> what was shown
  -> what remains limited
  -> what future direction follows
```

## Title Pattern

Use a title that names the problem, method, and contribution signal when
possible:

```text
<Problem> through/with <Method> for <Contribution>
```

The title can be concise or creative, but it should not hide the actual work.

## Figure Emphasis

The primer repeatedly stresses that figures are not decoration:

```text
Figure 1     -> motivation or failure case
Overview     -> method architecture or workflow
Experiments  -> evidence, trend, ablation, or boundary
```

Figure checks:

- readable after scaling
- self-contained labels and caption
- no excessive visual clutter
- core message clear without full paper context
- quantitative claims backed by data

## Writing Discipline

Before drafting:

- build the paper outline
- decide what each section and paragraph must do
- map contributions to evidence and section anchors
- discuss uncertain structure before polishing prose

During drafting:

- use simple sentences where possible
- avoid repeated text
- make transitions explicit
- read each paragraph after writing
- use grammar tools for mechanical checking, not claim creation
