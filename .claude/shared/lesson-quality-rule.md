# Lesson Quality Rule

## Purpose

Prevent raw observations from being promoted into durable project memory.

## Levels

- Observation: a run-level result, log event, or metric change.
- Finding: a bounded comparison with evidence, but limited explanation.
- Lesson: an evidence-backed interpretation with boundary and future action.
- Invariant candidate: a possible cross-project process rule requiring repeated
  evidence and human approval.

## Promotion Requirements

A lesson may be accepted into `MEMORY.md` only when it has:

- a clear claim
- evidence source or evidence chain
- at least two evidence types, unless marked low confidence
- alternative explanations or known uncertainties
- applicability boundary
- future action
- promotion status

## Storage

- Raw observations stay in iteration reports or auto summaries.
- Findings and candidate lessons may live in `docs/50_memory/Lessons.md`.
- `MEMORY.md` stores accepted lessons only.
- Research invariants store only cross-project process rules approved by a human.

## Promotion Flow

1. `/iterate eval` or `/evaluate` records observations, findings, and
   `lesson_candidates` in the iteration report and `iteration_log.json`.
2. Candidate lessons may be mirrored to `docs/50_memory/Lessons.md` with
   `promotion_status: candidate`, evidence references, confidence, boundary,
   and unresolved alternatives.
3. A human or review step may mark a candidate `accepted` only after the
   promotion requirements above are satisfied.
4. Only accepted lessons are copied into `MEMORY.md`; the entry must preserve
   the evidence reference, applicability boundary, and future action.
5. If review is skipped or evidence is incomplete, leave the item outside
   `MEMORY.md` so observations are not silently promoted.

## Forbidden Lessons

Avoid vague or over-broad lessons such as:

- "method X is bad"
- "effect is poor, abandon it"
- "probably the model is not good enough"
- "this direction has no value"

Prefer bounded claims:

> Under the current config and single-seed run, method X did not beat the
> baseline. Without seed repeats or ablation, this only shows this configuration
> is not sufficient; it does not disprove method X.
