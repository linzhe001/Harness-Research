# Auto-Iterate Remote Control Guide

This guide explains how to operate the auto-iterate controller locally and how remote wrappers (e.g., cc-connect) can consume its CLI.

## 1. Starting a Loop

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh start \
  --tool codex \
  --goal docs/auto_iterate_goal.md \
  --config tooling/auto_iterate/config/auto_iterate_controller.yaml \
  --accounts tooling/auto_iterate/config/auto_iterate_accounts.yaml
```

Optional flags:
- `--dry-run` — walk the state machine without invoking real Codex
- `--max-rounds N` — override the goal's `budget.max_rounds`

## 2. Checking Status

**Human-readable:**
```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status
```

**Machine-readable (for remote wrappers):**
```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json
```

`status --json` returns a stable contract with at least these fields:
- `schema_version`, `loop_id`, `status`, `halt_reason`
- `current_round_index`, `current_phase_key`, `current_iteration_id`
- `accounts.selected_account_id`
- `objective.primary_metric.name`
- `best.primary_metric`
- `budget.completed_rounds`, `budget.max_rounds`
- `llm_budget.used_calls`, `llm_budget.max_calls`
- `last_decision`, `last_failure`

Remote wrappers must use `--json` output, never parse prose.

## 3. Pausing and Stopping

**Pause** (graceful, at next phase boundary):
```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh pause
```

**Stop** (graceful, at next phase boundary):
```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh stop
```

Both commands create a signal file (`.auto_iterate_pause` or `.auto_iterate_stop`) in the workspace root. The running controller consumes the signal at the next safe phase boundary. The signal file is deleted after consumption.

## 4. Resuming

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh resume \
  --config tooling/auto_iterate/config/auto_iterate_controller.yaml \
  --accounts tooling/auto_iterate/config/auto_iterate_accounts.yaml
```

Resume handles:
- Stale lock detection and cleanup (emits `STALE_LOCK_CLEARED`)
- Phase-specific recovery (adopt existing progress or rerun)
- Re-acquisition of the lock and heartbeat restart

## 5. Staged Goal Updates

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh override --goal docs/auto_iterate_goal_v2.md
```

This writes `.auto_iterate/goal.next.md`. The staged goal activates at the next round boundary, **not** mid-round. If the new goal changes `primary_metric.name` or `direction`, activation is rejected and the loop pauses with `manual_action_required`.

## 6. Viewing Events

**Human-readable:**
```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail --lines 30
```

**Machine-readable (for remote wrappers):**
```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail --jsonl --lines 50
```

`tail --jsonl` returns raw lines from `events.jsonl`. Each line is a JSON object with:
- `v`, `ts`, `event`, `loop_id`, `status`
- Optional: `round_index`, `phase_key`, `payload`

## 7. Diagnosing Lock Conflicts

If `start` or `resume` returns exit code `102` (lock conflict):

1. Check if a controller is actually running: `ps aux | grep auto_iterate`
2. Read the lock: `cat .auto_iterate/lock.json`
3. If the PID is dead and heartbeat is stale, `resume` will auto-clear it
4. If the PID is alive on another host, the lock is legitimately held

## 8. Recovering from `waiting_for_account`

If the controller pauses with `halt_reason=waiting_for_account`:

1. Check account status: `cat .auto_iterate/state.json | jq .accounts`
2. Wait for cooldown to expire, or
3. Fix auth issues in the account's `CODEX_HOME` directory
4. Run `resume` to continue

## 9. Reading stdout/stderr Logs

Runtime logs are stored at:
```
.auto_iterate/runtime/round{N}_{phase}.stdout.log
.auto_iterate/runtime/round{N}_{phase}.stderr.log
```

## 10. Exit Code Reference

| Code | Meaning |
|------|---------|
| 0 | Success (loop completed normally) |
| 100 | Invalid arguments |
| 101 | Invalid controller state |
| 102 | Lock conflict |
| 103 | Goal validation failed |
| 104 | Runtime invocation failed |
| 105 | Manual action required |
| 106 | Budget exhausted |
| 107 | Waiting for account |
| 108 | Resumable interruption / operator pause |
| 109 | Fatal controller error |

## 11. cc-connect Mapping

| Remote Action | Local Command |
|---------------|---------------|
| Start loop | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh start --tool codex --goal docs/auto_iterate_goal.md` |
| Check status | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json` |
| Pause | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh pause` |
| Stop | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh stop` |
| Resume | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh resume` |
| View events | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail --jsonl --lines 50` |
| Update goal | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh override --goal <path>` |

cc-connect or any remote wrapper should:
- Call these commands via SSH or management API
- Parse `--json` / `--jsonl` output, never prose
- Use exit codes for status classification
- Never directly modify `.auto_iterate/` files
