# Auto-Iterate V7 Implementer Notes

These notes freeze critical algorithms and precedence rules that are not fully captured
by the JSON fixtures alone. Every controller implementation decision must be traceable
to either this document or `auto_iterate_v7_plan/01_contract_freeze.md`.

---

## 1. `current_iteration_id` Binding Algorithm

This is the single most important algorithm to get right. The controller must never
guess which iteration belongs to the current round.

**Algorithm (executed after `plan` phase completes):**

1. Before `plan` launches, read `iteration_log.json` and record `existing_ids = set(iter.id for iter in iterations)`.
2. After `plan` finishes (runtime exits), re-read `iteration_log.json` and compute `current_ids = set(iter.id for iter in iterations)`.
3. Compute `new_ids = current_ids - existing_ids`.
4. If `len(new_ids) != 1`, the `plan` phase is `postcondition_failed`.
   - `len(new_ids) == 0`: the plan phase did not create a new iteration entry.
   - `len(new_ids) >= 2`: the plan phase created multiple entries (ambiguous).
5. If exactly 1 new ID: this is `current_iteration_id`. Write it to `.auto_iterate/state.json`.
6. All subsequent phases (`code`, `run_screening`, `run_full`, `eval`) validate against
   this bound ID only. Never fall back to "take the latest entry".

**Why**: Previous versions used "latest iteration" heuristics, which broke when
concurrent edits or recovery created extra entries.

---

## 2. Goal Precedence

When `start` initializes the loop, values are resolved in this order (highest wins):

1. **CLI overrides** — explicit `--flag value` arguments to `start`
2. **Validated source goal** — extracted schema from the goal markdown file
3. **Controller policy config** — `tooling/auto_iterate/config/auto_iterate_controller.yaml`
4. **Doc defaults** — hardcoded defaults in the controller code
5. **Account registry** — only used for account selection, not metric/budget values

After `start` completes:
- All runtime reads come from `.auto_iterate/state.json`, never re-parsed from the goal file.
- `resume` must not re-read the original goal path — it restores from `state.json` only.

---

## 3. Atomic Write Scope

| File | Atomic (temp + rename) | Reason |
|------|----------------------|--------|
| `state.json` | YES | Avoid resume reading half-written state |
| `lock.json` | YES | Avoid heartbeat/owner corruption |
| `goal.md` | YES | Staged activation must not expose partial goal |
| `goal.next.md` | YES | Same as above |
| `*_brief.json` | YES | Adapter must read complete brief |
| `*_result.json` | YES | Controller must read complete result |
| `events.jsonl` (append) | NO | Append-only is acceptable |
| `events.jsonl` (rotation) | YES | Rename to archive must be atomic |
| `stdout/stderr logs` | NO | Streaming output |

**Implementation pattern**: Write to `<target>.tmp.<pid>` in the same directory,
then `os.replace()` (POSIX atomic rename on same filesystem).

---

## 4. `NEXT_ROUND` vs `halt_reason` — They Are Different Enums

**WF8 decisions** (written by `iterate eval` into `iteration_log.json`):
- `NEXT_ROUND` — ordinary improvement round, stay in WF8
- `DEBUG` — debug-oriented round, stay in WF8
- `CONTINUE` — hand off to orchestrator, exit WF8 → WF9
- `PIVOT` — strategy change, exit WF8 → WF2
- `ABORT` — terminate project direction

**Controller halt reasons** (written by controller into `state.json`):
- `target_met`
- `max_rounds_reached`
- `patience_exhausted`
- `gpu_budget_exhausted`
- `llm_budget_exhausted`
- `manual_stop`
- `operator_pause`
- `waiting_for_account`
- `workflow_continue` — maps from decision `CONTINUE`
- `workflow_pivot` — maps from decision `PIVOT`
- `workflow_abort` — maps from decision `ABORT`
- `manual_action_required`
- `fatal_controller_error`

**Key distinction**: A WF8 decision is the AI's recommendation about what to do next.
A halt reason is the controller's durable record of why it stopped. `NEXT_ROUND` and
`DEBUG` never produce a halt reason — they keep the loop running.

---

## 5. `run_screening` and `run_full` Are Same-Iteration Phases

They are NOT separate iterations. Within a single iteration (bound by `current_iteration_id`):

- `run_screening` is an optional short run to quickly validate feasibility
- `run_full` is the complete training run

The `iteration_log.json` entry has both `screening` and `full_run` as sibling fields:

```json
{
  "id": "iter4",
  "status": "running",
  "screening": {
    "recommended": true,
    "status": "passed"
  },
  "full_run": {
    "status": "completed",
    "resume_mode": "from_scratch",
    "metrics": { "PSNR": 31.2 }
  }
}
```

The controller uses `phase_key` (not `phase_family`) to distinguish them:
- `phase_key=run_screening` + `run_type=screening`
- `phase_key=run_full` + `run_type=full`

Mismatches (e.g., `phase_key=run_full` with `run_type=screening`) must be rejected
by the runtime adapter.

---

## 6. CLI Exit Code Space

| Code | Meaning |
|------|---------|
| 0 | Success |
| 100 | Invalid arguments |
| 101 | Invalid controller state |
| 102 | Lock conflict (another loop is running) |
| 103 | Goal validation failed |
| 104 | Runtime invocation failed |
| 105 | Manual action required |
| 106 | Budget exhausted |
| 107 | Waiting for account |
| 108 | Resumable interruption or operator pause |
| 109 | Fatal controller error |

Note: `paused`, `stopped`, `failed` are durable states in `state.json`,
not exit codes. Remote wrappers must rely on these exit codes, not stderr prose.

---

## 7. Recovery Contract Summary

Phase boundary persistence: controller must persist state at two moments:
1. Before phase launch (so we know what we were about to do)
2. After postcondition validated (so we know what succeeded)

`phase_attempt` rules:
- Increments before each launch of the same `phase_key`
- Resets to 1 when transitioning to a new `phase_key`
- Default `retry_policy.max_phase_attempts = 2`
- Exceeding ceiling → `status=paused`, `halt_reason=manual_action_required`

Phase-specific recovery (on `resume`):

| phase_key | Recovery Rule |
|-----------|--------------|
| `plan` | No new planned iteration → rerun; exactly 1 planned candidate → adopt |
| `code` | Status `planned` or `coding` → rerun; status `training` with complete git_commit → adopt |
| `run_screening` | Missing screening record + status `training` → rerun; terminal screening status → adopt |
| `run_full` | No `full_run` + status `training` → rerun; `recoverable_failed` under ceiling → rerun; `completed` or `failed` → adopt |
| `eval` | No decision/lesson → rerun; status `completed` → adopt |
