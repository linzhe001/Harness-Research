# Auto-Iterate Boundary

## Distinction

Auto-paper optimizes manuscript readiness. Auto-iterate optimizes experimental
iterations and metric-driven research runs. They are peer controllers, not
submodes of each other.

## Forbidden Reuse

Auto-paper must not write or use as sole claim evidence:

- `iteration_log.json`
- `.auto_iterate/`
- WF10 phase prompts
- training budgets
- screening/full-run gates
- `primary_metric` and metric patience semantics

## Allowed Reuse

Auto-paper may read the generated
`docs/30_evidence/Experiment_Evidence_Index.{json,md}` and the run artifact
paths listed inside it. `$run`/`$analyze` own refreshing that index from
`iteration_log.json`.

Auto-paper may also read `iteration_log.json` directly as a weak signal for
experiment intent and sequence, but it must cross-check purpose and results
against iteration reports, configs, logs, metrics, or run artifacts before
writing paper-facing claims.

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

## Run Feedback

When auto-paper needs more experiment evidence, it writes
`auto_paper_output/<paper_id>/run_request_register.{json,md}` and returns
`RUN_REQUEST`. `$run` reads that request as planning input; auto-paper does not
start training jobs itself.
