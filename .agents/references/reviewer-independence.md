# Reviewer Independence Protocol

## Core Principle

Reviewer calls must point to primary artifacts and ask for judgment; they must not coach the reviewer with the executor's interpretation.

## Allowed Reviewer Context

- role or persona
- review objective
- file paths and artifact locations
- structural metadata such as section names, metric protocol names, or venue constraints
- hard constraints the reviewer must apply

## Disallowed Reviewer Context

- executor summaries of file contents
- executor interpretations of results
- executor recommendations or preferred conclusions
- selected "key findings" extracted by the executor
- leading assertions that frame the work as strong, weak, correct, or nearly ready
- previous review feedback, unless continuing the same reviewer thread and asking whether the reviewer considers their own prior concerns resolved

## Correct Pattern

```text
Review this project gate as a senior ML reviewer.

Files to read:
- Technical spec: docs/Technical_Spec.md
- Baseline report: docs/Baseline_Report.md
- Stable code map: project_map.json
- Current iteration log: iteration_log.json

Task:
- Evaluate correctness and missing risks.
- Return critical/warning/info findings with file paths and rationale.
```

## Required Recording

Each reviewer result must record:

- reviewer status: `used`, `unavailable`, or `skipped_low_value`
- artifacts passed to the reviewer
- trace path if tracing is enabled
- unresolved critical findings
