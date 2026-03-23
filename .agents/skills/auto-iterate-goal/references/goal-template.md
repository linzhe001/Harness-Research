# Goal Template Reference

See `tooling/auto_iterate/docs/auto_iterate_goal_template.md` for the canonical template.

## Required Fields (must be present for controller goal parser)

- `objective.primary_metric.name` — metric name (e.g., PSNR, mAP)
- `objective.primary_metric.direction` — `maximize` or `minimize`
- `objective.primary_metric.target` — numeric target value
- `objective.constraints[]` — hard constraints (may be empty)
- `patience.max_no_improve_rounds` — integer
- `patience.min_primary_delta` — float
- `budget.max_rounds` — integer
- `budget.max_gpu_hours` — float
- `screening_policy.enabled` — boolean
- `screening_policy.threshold_pct` — integer (when enabled)
- `screening_policy.default_steps` — integer (when enabled)

## Optional Fields

- `initial_hypotheses[]` — seed hypotheses for first rounds
- `forbidden_directions[]` — hard boundaries the AI must not cross

## Field Sources

| Field | Primary Source |
|-------|---------------|
| `primary_metric.*` | WF5 evaluation protocol |
| `screening_policy.*` | Project defaults + validate-run experience |
| `budget.*`, `patience.*` | Controller policy config + project stage constraints |
