# Experiment Queue

Status: active

This file stores concrete follow-up experiments, falsifiers, controls,
assurance gaps, and paper-driven run requests. It is a planning queue, not
Conclusion Evidence by itself.

## Queue

| ID | Priority | Status | Assurance Axis | Question | Falsifier | Evidence Needed |
| --- | --- | --- | --- | --- | --- | --- |
| pending | medium | open | TBD | Pending experiment. | TBD | TBD |

## Status Values

- `open`
- `planned`
- `running`
- `blocked`
- `completed`
- `dropped`

## Boundary Notes

Queue entries should point to real Source Artifacts or pending `RUN_REQUEST`
records when they come from writing. Completed entries must be reconciled with
`iteration_log.json`, run manifests, and Gate ledgers before they support
claims.
