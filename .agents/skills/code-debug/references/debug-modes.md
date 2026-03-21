# Code Debug Modes

## planned_change

- Triggered by `$iterate code`
- Read active iteration context
- Implement only the scoped change
- preserve existing architecture unless the iteration explicitly changes it

## bugfix

- Triggered by a crash, exception, mismatch, or broken behavior
- prioritize minimal diagnosis and minimal fix

## perf_tuning

- Triggered by underperforming results
- prefer targeted changes backed by metrics or recent reports

## Common Validation

- `python -m py_compile`
- `ruff check --select=E,F,I`
- update `project_map.json` if stable interfaces changed
- semantic commit required before returning control to training
