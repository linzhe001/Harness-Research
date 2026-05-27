# Auto-Iterate Boundary

## Distinction

Auto-paper optimizes manuscript readiness. Auto-iterate optimizes experimental
iterations and metric-driven research runs. They are peer controllers, not
submodes of each other.

## Forbidden Reuse

Auto-paper must not write or depend on:

- `iteration_log.json`
- `.auto_iterate/`
- WF10 phase prompts
- training budgets
- screening/full-run gates
- `primary_metric` and metric patience semantics

## Allowed Reuse

Auto-paper may reuse software patterns from auto-iterate:

- atomic JSON writes
- CLI control shape
- event logs
- postcondition checks based on files, not stdout
- runtime prompt rendering

## Rename Map

| auto-iterate | auto-paper |
| --- | --- |
| `.auto_iterate` | `.auto_paper` |
| `auto_iterate_ctl` | `auto_paper_ctl` |
| `primary_metric` | `readiness_gates` |
| `initial_hypotheses` | `writing_objectives` |
| `iteration_log.json` | `auto_paper_log.json` |
