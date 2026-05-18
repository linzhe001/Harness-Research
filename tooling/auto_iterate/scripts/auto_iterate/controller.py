"""Auto-iterate V7 loop controller.

Implements the state machine described in ``02_controller_runtime_plan.md``
§4.  The controller owns ``.auto_iterate/`` and orchestrates fresh Codex
processes for each phase via the runtime adapter.

The controller does NOT write ``iteration_log.json`` or
``PROJECT_STATE.json`` — those remain owned by their respective skills.
"""

# ruff: noqa: E501

from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .accounts import AccountRegistry
from .events import EventLogger, iso_now
from .goal import (
    GoalManager,
)
from .goal import (
    parse as parse_goal,
)
from .goal import (
    validate as validate_goal,
)
from .lock import LockConflictError, LockManager
from .policy import DEFAULT_POLICY, PolicyConfig
from .postcondition import PostconditionValidator, iteration_metrics
from .recovery import ADOPT, FAIL, RecoveryEngine
from .runtime import (
    BriefValidationError,
    HeartbeatWorker,
    PhaseSupervisor,
    build_brief,
)
from .state import StateLoadError, StateStore, atomic_write_json

# ---------------------------------------------------------------------------
# Exit codes (frozen in 01§8.5)
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_INVALID_ARGS = 100
EXIT_INVALID_STATE = 101
EXIT_LOCK_CONFLICT = 102
EXIT_GOAL_VALIDATION = 103
EXIT_RUNTIME_FAILED = 104
EXIT_MANUAL_ACTION = 105
EXIT_BUDGET_EXHAUSTED = 106
EXIT_WAITING_ACCOUNT = 107  # Reserved; legacy waiting-for-account no longer emitted.
EXIT_RESUMABLE = 108
EXIT_FATAL = 109


def _numeric_metric_value(value: Any, metric_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"primary metric {metric_name!r} must be numeric")
    return float(value)


# ---------------------------------------------------------------------------
# Decision → halt_reason mapping
# ---------------------------------------------------------------------------
_DECISION_HALT: dict[str, str] = {
    "CONTINUE": "workflow_continue",
    "PIVOT": "workflow_pivot",
    "ABORT": "workflow_abort",
}

# Canonical phase sequence.
_PHASE_SEQUENCE = ["plan", "code", "run_screening", "run_full", "eval"]
_PERSISTED_POLICY_KEYS = (
    "timeouts",
    "terminate_grace_sec",
    "retry_policy",
    "heartbeat",
    "event_log",
    "runtime",
)


def _merge_with_fallback(
    override: dict[str, Any],
    fallback: dict[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(fallback)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_with_fallback(value, result[key])
        else:
            result[key] = copy.deepcopy(value)
    return result


def _clean_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    cleaned = reason.strip()
    return cleaned or None


# ---------------------------------------------------------------------------
# LoopController
# ---------------------------------------------------------------------------


class LoopController:
    """Main auto-iterate controller state machine."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        dry_run: bool = False,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.auto_dir = self.workspace_root / ".auto_iterate"
        self.dry_run = dry_run

        self.store = StateStore(self.auto_dir)
        self.events = EventLogger(self.auto_dir / "events.jsonl")
        self.goal_mgr = GoalManager(self.auto_dir)

        self.state: dict[str, Any] = {}
        self.policy: dict[str, Any] = {}
        self.lock_mgr: LockManager | None = None
        self.heartbeat: HeartbeatWorker | None = None
        self.accounts: AccountRegistry = AccountRegistry.external_current()
        self.validator = PostconditionValidator(self.workspace_root)

    # ==================================================================
    # start
    # ==================================================================

    def start_loop(
        self,
        goal_path: str,
        *,
        config_path: str | None = None,
        tool: str = "codex",
        cli_overrides: dict[str, Any] | None = None,
        skip_dynamic_preflight: bool = False,
        skip_dynamic_preflight_reason: str | None = None,
        allow_draft_contract: bool = False,
        allow_review_required: bool = False,
    ) -> int:
        """Initialize and run a new auto-iterate loop. Returns exit code."""
        if skip_dynamic_preflight and not _clean_reason(skip_dynamic_preflight_reason):
            return EXIT_INVALID_ARGS

        # 1. Parse and validate goal.
        try:
            parsed_goal = parse_goal(goal_path)
            errors = validate_goal(parsed_goal)
            if errors:
                return EXIT_GOAL_VALIDATION
        except Exception:
            return EXIT_GOAL_VALIDATION

        # 2. Load policy, merge precedence.
        pc = PolicyConfig.load(config_path)
        pc.merge_with_goal(parsed_goal)
        if cli_overrides:
            pc.merge_with_cli(cli_overrides)
        self.policy = pc.freeze()

        # 3. Resolve external current auth from CODEX_HOME or ~/.codex.
        self.accounts = AccountRegistry.external_current()

        # 4. Check lock conflict.
        stale_threshold = self.policy.get("heartbeat", {}).get(
            "stale_threshold_sec", 120
        )
        self.lock_mgr = LockManager(
            self.auto_dir / "lock.json",
            stale_threshold_sec=stale_threshold,
        )
        try:
            conflict = self.lock_mgr.check_conflict()
            if conflict == "live":
                return EXIT_LOCK_CONFLICT
            if conflict == "stale":
                self.lock_mgr.clear_stale()
        except Exception:
            return EXIT_FATAL

        # 5. Build initial state.
        loop_id = f"auto_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        obj = parsed_goal.get("objective", {})
        budget = self.policy.get("budget", {})
        llm_budget = self.policy.get("llm_budget", {})
        patience = self.policy.get("patience", {})
        screening_policy = parsed_goal.get(
            "screening_policy", self.policy.get("screening_policy", {})
        )

        self.state = {
            "schema_version": 1,
            "loop_id": loop_id,
            "status": "running",
            "tool": tool,
            "current_round_index": 0,
            "current_phase_key": "plan",
            "current_iteration_id": None,
            "phase_attempt": 1,
            "goal": {
                "source_path": goal_path,
                "activated_at": iso_now(),
            },
            "objective": obj,
            "initial_hypotheses": parsed_goal.get("initial_hypotheses", []),
            "forbidden_directions": parsed_goal.get("forbidden_directions", []),
            "best": {
                "iteration_id": None,
                "round_index": None,
                "primary_metric": None,
                "updated_at": None,
            },
            "patience": {
                "max_no_improve_rounds": patience.get("max_no_improve_rounds", 5),
                "min_primary_delta": patience.get("min_primary_delta", 0.1),
                "consecutive_no_improve": 0,
            },
            "budget": {
                "max_rounds": budget.get("max_rounds", 20),
                "completed_rounds": 0,
                "gpu_count": budget.get("gpu_count", 1),
                "max_gpu_hours": budget.get("max_gpu_hours", 100.0),
                "used_gpu_hours": 0.0,
                "tracking_method": "wall_time_hours_x_gpu_count",
            },
            "llm_budget": {
                "max_calls": llm_budget.get("max_calls", 200),
                "used_calls": 0,
                "tracking_method": "runtime_invocation_count",
            },
            "accounts": self.accounts.to_state_dict(),
            "last_decision": None,
            "halt_reason": None,
            "last_failure": None,
            "timeouts": copy.deepcopy(self.policy.get("timeouts", {})),
            "terminate_grace_sec": self.policy.get("terminate_grace_sec", 30),
            "retry_policy": copy.deepcopy(self.policy.get("retry_policy", {})),
            "heartbeat": copy.deepcopy(self.policy.get("heartbeat", {})),
            "event_log": copy.deepcopy(self.policy.get("event_log", {})),
            "runtime": copy.deepcopy(self.policy.get("runtime", {})),
            # Internal: not persisted but used during run.
            "_policy": self.policy,
            "screening_policy": screening_policy,
        }

        acquired = False
        try:
            # 6. Acquire lock before writing controller-owned runtime state so a
            # losing contender does not overwrite the active loop's files.
            self.lock_mgr.acquire(loop_id, tool, str(self.workspace_root))
            acquired = True

            # 7. Run dynamic-context gates before launching autonomous WF10.
            self.store.ensure_dirs()
            if skip_dynamic_preflight:
                self._record_dynamic_preflight_skip(
                    reason=_clean_reason(skip_dynamic_preflight_reason),
                )
            else:
                preflight_ok = self._run_dynamic_context_preflight(
                    allow_draft=allow_draft_contract,
                    allow_review_required=allow_review_required,
                )
                if not preflight_ok:
                    self._pause_for_dynamic_preflight_failure(loop_id)
                    return EXIT_MANUAL_ACTION

            # 8. Persist initial runtime state.
            self.goal_mgr.snapshot_to(goal_path)
            self._persist_state()

            # 9. Start heartbeat.
            hb_interval = self.policy.get("heartbeat", {}).get("interval_sec", 30)
            self.heartbeat = HeartbeatWorker(self.lock_mgr, interval_sec=hb_interval)
            self.heartbeat.start()

            # 10. Emit event.
            self.events.emit(
                "LOOP_STARTED",
                loop_id,
                "running",
                payload={"tool": tool, "goal_source": goal_path},
            )

            # 11. Run.
            return self.run_main_loop()
        except LockConflictError:
            return EXIT_LOCK_CONFLICT
        except Exception as exc:
            self._record_fatal_controller_error(str(exc))
            return EXIT_FATAL
        finally:
            if acquired:
                self._cleanup()

    # ==================================================================
    # resume
    # ==================================================================

    def resume_loop(
        self,
        *,
        config_path: str | None = None,
        skip_dynamic_preflight: bool = False,
        skip_dynamic_preflight_reason: str | None = None,
        allow_draft_contract: bool = False,
        allow_review_required: bool = False,
    ) -> int:
        """Resume from a previously interrupted loop. Returns exit code."""
        if skip_dynamic_preflight and not _clean_reason(skip_dynamic_preflight_reason):
            return EXIT_INVALID_ARGS

        # Load existing state.
        try:
            self.state = self.store.load_state()
        except Exception:
            return EXIT_INVALID_STATE

        status = self.state.get("status")
        if status not in ("paused", "failed", "running"):
            return EXIT_INVALID_STATE

        # Reconstruct frozen runtime policy from durable state. Config/defaults
        # are only a compatibility fallback for older state files that predate
        # persisted policy fields.
        pc = PolicyConfig.load(config_path)
        self.policy = self._policy_from_state(pc.freeze())
        self.state["_policy"] = self.policy
        self._ensure_policy_fields_in_state()

        # Resolve external current auth from CODEX_HOME or ~/.codex.
        self.accounts = AccountRegistry.external_current()
        self.accounts.restore_runtime(self.state.get("accounts"))
        self.state["accounts"] = self.accounts.to_state_dict()

        # Lock management.
        stale_threshold = self.state.get("heartbeat", {}).get(
            "stale_threshold_sec",
            self.policy.get("heartbeat", {}).get("stale_threshold_sec", 120),
        )
        self.lock_mgr = LockManager(
            self.auto_dir / "lock.json",
            stale_threshold_sec=stale_threshold,
        )
        conflict = self.lock_mgr.check_conflict()
        if conflict == "live":
            return EXIT_LOCK_CONFLICT
        if conflict == "stale":
            cleared = self.lock_mgr.clear_stale()
            if cleared:
                self.events.emit(
                    "STALE_LOCK_CLEARED",
                    self.state["loop_id"],
                    "running",
                    payload={"cleared_pid": cleared.get("pid")},
                )

        # Recovery.
        recovery = RecoveryEngine(
            self.validator,
            primary_metric_name=self._objective_primary_metric_name(),
        )
        max_attempts = self._phase_retry_ceiling()
        plan = recovery.recover(self.state, max_phase_attempts=max_attempts)

        if plan["action"] == FAIL:
            self.state["status"] = "paused"
            self.state["halt_reason"] = "manual_action_required"
            self._persist_state()
            return EXIT_MANUAL_ACTION

        adopt_after_preflight = plan["action"] == ADOPT
        if adopt_after_preflight:
            # Adopt the existing state; advance only after preflight passes.
            if plan["phase_key"] == "plan" and plan.get("adopted_iteration_id"):
                self.state["current_iteration_id"] = plan["adopted_iteration_id"]
                self.state.pop("plan_binding", None)

        # Re-acquire lock.
        self.state["status"] = "running"
        loop_id = self.state["loop_id"]
        tool = self.state.get("tool", "codex")
        acquired = False
        try:
            self.lock_mgr.acquire(loop_id, tool, str(self.workspace_root))
            acquired = True

            if skip_dynamic_preflight:
                self._record_dynamic_preflight_skip(
                    reason=_clean_reason(skip_dynamic_preflight_reason),
                )
                self._persist_state()
            else:
                preflight_ok = self._run_dynamic_context_preflight(
                    allow_draft=allow_draft_contract,
                    allow_review_required=allow_review_required,
                )
                if not preflight_ok:
                    self._pause_for_dynamic_preflight_failure(loop_id)
                    return EXIT_MANUAL_ACTION

            if adopt_after_preflight:
                self._advance_phase()

            # Start heartbeat.
            hb_interval = self.state.get("heartbeat", {}).get(
                "interval_sec",
                self.policy.get("heartbeat", {}).get("interval_sec", 30),
            )
            self.heartbeat = HeartbeatWorker(self.lock_mgr, interval_sec=hb_interval)
            self.heartbeat.start()

            self.events.emit("LOOP_RESUMED", loop_id, "running")
            self._persist_state()

            return self.run_main_loop()
        except LockConflictError:
            return EXIT_LOCK_CONFLICT
        except Exception as exc:
            self._record_fatal_controller_error(str(exc))
            return EXIT_FATAL
        finally:
            if acquired:
                self._cleanup()

    # ==================================================================
    # main loop
    # ==================================================================

    def run_main_loop(self) -> int:
        """Execute the phase loop until halt. Returns exit code."""
        while self.state["status"] == "running":
            phase_key = self.state["current_phase_key"]
            round_idx = self.state["current_round_index"]

            # -- Round boundary checks ------------------------------------
            if phase_key == "plan":
                # Check operator signals.
                signal = self._check_operator_signals()
                if signal:
                    return self._map_exit_code()

                # Activate pending goal.
                if not self._activate_pending_goal():
                    return self._map_exit_code()

                # Check stop conditions.
                halt = self._check_stop_conditions()
                if halt:
                    self.events.emit(
                        "LOOP_STOPPED",
                        self.state["loop_id"],
                        "stopped",
                        round_index=round_idx,
                        payload={"halt_reason": self.state["halt_reason"]},
                    )
                    return self._map_exit_code()

                # Budget pre-check.
                if not self._budget_allows_next_round():
                    self.state["status"] = "stopped"
                    self.state["halt_reason"] = self._budget_halt_reason()
                    self._persist_state()
                    self.events.emit(
                        "LOOP_STOPPED",
                        self.state["loop_id"],
                        "stopped",
                        round_index=round_idx,
                        payload={"halt_reason": self.state["halt_reason"]},
                    )
                    return self._map_exit_code()

                # Increment round.
                self.state["current_round_index"] += 1
                round_idx = self.state["current_round_index"]
                self.events.emit(
                    "ROUND_STARTED",
                    self.state["loop_id"],
                    "running",
                    round_index=round_idx,
                )

            # -- Screening bypass -----------------------------------------
            if phase_key == "run_screening" and self._should_bypass_screening():
                self.events.emit(
                    "SCREENING_BYPASSED",
                    self.state["loop_id"],
                    "running",
                    round_index=round_idx,
                    payload={"reason": "screening disabled or not recommended"},
                )
                self.state["current_phase_key"] = "run_full"
                phase_key = "run_full"
                self._reset_phase_retry_state()
                self._persist_state()

            # -- Run one phase --------------------------------------------
            result = self._run_one_phase(phase_key, round_idx)
            if result is None:
                # Fatal error during phase execution.
                return self._map_exit_code()

            # -- Heartbeat health check -----------------------------------
            if self.heartbeat and not self.heartbeat.is_alive():
                self.state["status"] = "failed"
                self.state["halt_reason"] = "fatal_controller_error"
                self.state["last_failure"] = "heartbeat worker died"
                self._persist_state()
                self.events.emit(
                    "LOOP_FAILED",
                    self.state["loop_id"],
                    "failed",
                    payload={"reason": "heartbeat_worker_death"},
                )
                return EXIT_FATAL

        # Loop exited normally.
        self._persist_state()
        return self._map_exit_code()

    # ==================================================================
    # run one phase
    # ==================================================================

    def _run_one_phase(self, phase_key: str, round_idx: int) -> dict[str, Any] | None:
        """Execute a single phase. Returns the postcondition result or None on fatal."""
        loop_id = self.state["loop_id"]
        iteration_id = self.state.get("current_iteration_id")
        self.state["phase_attempt"] = int(self.state.get("phase_attempt", 1)) + 1
        if phase_key == "plan":
            binding = self.state.get("plan_binding")
            if not isinstance(binding, dict) or "existing_ids" not in binding:
                self.state["plan_binding"] = {
                    "existing_ids": sorted(self.validator.get_iteration_ids()),
                }
        self._persist_state()

        self.events.emit(
            "PHASE_STARTED",
            loop_id,
            "running",
            round_index=round_idx,
            phase_key=phase_key,
        )

        # Snapshot pre-IDs for plan phase from durable state so resume can bind
        # the same iteration deterministically.
        pre_ids = None
        if phase_key == "plan":
            existing_ids = self.state.get("plan_binding", {}).get("existing_ids", [])
            pre_ids = set(existing_ids)

        # Select external current auth.
        account = self.accounts.select_account(self.state)
        account_id = account["id"]
        codex_home = account.get("codex_home", "")
        self.state["accounts"]["selected_account_id"] = account_id
        self._persist_state()

        # Build brief and run.
        timeout = self.state.get("timeouts", {}).get(
            phase_key,
            self.policy.get("timeouts", {}).get(phase_key, 1800),
        )
        grace = self.state.get(
            "terminate_grace_sec", self.policy.get("terminate_grace_sec", 30)
        )

        supervisor = PhaseSupervisor(
            workspace_root=self.workspace_root,
            runtime_dir=self.auto_dir / "runtime",
        )

        try:
            recent_lessons, failed_hypotheses = self._plan_context()
            brief = build_brief(
                self.state,
                phase_key,
                recovery_mode=self.state.get("_recovery_mode", "normal"),
                recent_lessons=recent_lessons,
                failed_hypotheses=failed_hypotheses,
            )
            runtime_result = supervisor.run_phase(
                brief=brief,
                account_id=account_id,
                codex_home=codex_home,
                timeout_sec=timeout,
                terminate_grace_sec=grace,
                iteration_id=iteration_id,
                dry_run=self.dry_run,
                run_phase_full_access=self._run_phase_full_access(),
            )
        except BriefValidationError as e:
            self.state["status"] = "failed"
            self.state["halt_reason"] = "fatal_controller_error"
            self.state["last_failure"] = str(e)
            self._persist_state()
            return None
        except Exception as e:
            self.state["last_failure"] = str(e)
            self._persist_state()
            self.events.emit(
                "PHASE_FAILED",
                loop_id,
                "running",
                round_index=round_idx,
                phase_key=phase_key,
                payload={"error": str(e)},
            )
            return self._handle_phase_failure(phase_key, round_idx)

        # Record LLM usage.
        self.accounts.record_usage(account_id, calls=1)
        self.state["llm_budget"]["used_calls"] = (
            self.state["llm_budget"].get("used_calls", 0) + 1
        )
        self.state["accounts"] = self.accounts.to_state_dict()

        # Handle runtime failure.
        exit_class = runtime_result.get("runtime_exit_class", "internal_error")
        if runtime_result.get("timed_out"):
            self.events.emit(
                "PHASE_TIMEOUT",
                loop_id,
                "running",
                round_index=round_idx,
                phase_key=phase_key,
            )
            return self._handle_phase_failure(phase_key, round_idx)

        if exit_class == "quota_or_rate_limit":
            self.accounts.record_external_retry(account_id, "quota_or_rate_limit")
            self.state["accounts"] = self.accounts.to_state_dict()
            self.events.emit(
                "EXTERNAL_AUTH_RETRY",
                loop_id,
                "running",
                payload={
                    "reason": "quota_or_rate_limit",
                    "account_id": account_id,
                },
            )
            return self._handle_phase_failure(
                phase_key,
                round_idx,
                external_auth_retry=True,
            )

        if exit_class == "auth_failure":
            self.accounts.record_external_retry(account_id, "auth_failure")
            self.state["accounts"] = self.accounts.to_state_dict()
            self.events.emit(
                "EXTERNAL_AUTH_RETRY",
                loop_id,
                "running",
                payload={
                    "reason": "auth_failure",
                    "account_id": account_id,
                },
            )
            return self._handle_phase_failure(
                phase_key,
                round_idx,
                external_auth_retry=True,
            )

        if exit_class != "success":
            failure_reason = runtime_result.get("failure_reason") or exit_class
            self.state["last_failure"] = (
                f"runtime_exit_class={exit_class}: {failure_reason}"
            )
            self.events.emit(
                "PHASE_FAILED",
                loop_id,
                "running",
                round_index=round_idx,
                phase_key=phase_key,
                payload={
                    "runtime_exit_class": exit_class,
                    "exit_code": runtime_result.get("exit_code"),
                    "failure_reason": failure_reason,
                },
            )
            return self._handle_phase_failure(phase_key, round_idx)

        # Validate postcondition.
        validation = self.validator.validate(
            phase_key,
            iteration_id,
            pre_ids=pre_ids,
            primary_metric_name=self._objective_primary_metric_name(),
        )

        if not validation["ok"]:
            self.state["last_failure"] = str(validation.get("payload", {}))
            self.events.emit(
                "PHASE_FAILED",
                loop_id,
                "running",
                round_index=round_idx,
                phase_key=phase_key,
                payload=validation.get("payload"),
            )
            return self._handle_phase_failure(phase_key, round_idx)

        # Phase succeeded.
        self.events.emit(
            "PHASE_COMPLETED",
            loop_id,
            "running",
            round_index=round_idx,
            phase_key=phase_key,
            payload={"classification": validation.get("classification")},
        )

        # Bind iteration_id after plan.
        if phase_key == "plan":
            self.state["current_iteration_id"] = validation.get("iteration_id")
            self.state.pop("plan_binding", None)

        # Track GPU hours for run phases.
        if phase_key in ("run_screening", "run_full"):
            duration_sec = runtime_result.get("duration_sec", 0)
            gpu_count = self.state["budget"].get("gpu_count", 1)
            gpu_hours = (duration_sec / 3600.0) * gpu_count
            self.state["budget"]["used_gpu_hours"] = round(
                self.state["budget"].get("used_gpu_hours", 0) + gpu_hours, 3
            )

        # Handle eval decision.
        if phase_key == "eval":
            decision = validation.get("payload", {}).get("decision")
            self.state["last_decision"] = decision
            return self._apply_decision(decision, round_idx, validation)

        if self._advance_after_success(phase_key, validation):
            self.state["phase_attempt"] = 1
            self._persist_state()
            return validation

        # Advance to next phase.
        self._advance_phase()
        self.state["phase_attempt"] = 1
        self._persist_state()
        return validation

    # ==================================================================
    # decision transitions
    # ==================================================================

    def _apply_decision(
        self,
        decision: str | None,
        round_idx: int,
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        loop_id = self.state["loop_id"]

        if decision in ("NEXT_ROUND", "DEBUG"):
            # Update best tracking.
            self._update_best_tracking(round_idx)
            self.state["budget"]["completed_rounds"] += 1

            self.events.emit(
                "ROUND_COMPLETED",
                loop_id,
                "running",
                round_index=round_idx,
            )
            self._rotate_events_if_needed(round_idx)

            # Reset for next round.
            self.state["current_phase_key"] = "plan"
            self.state["current_iteration_id"] = None
            self._reset_phase_retry_state()
            self.state.pop("_recovery_mode", None)
            self._persist_state()

        elif decision in _DECISION_HALT:
            halt_reason = _DECISION_HALT[decision]
            self.state["status"] = "stopped"
            self.state["halt_reason"] = halt_reason
            self.state["budget"]["completed_rounds"] += 1

            self.events.emit(
                "ROUND_COMPLETED",
                loop_id,
                "stopped",
                round_index=round_idx,
            )
            self._rotate_events_if_needed(round_idx)
            self.events.emit(
                "LOOP_STOPPED",
                loop_id,
                "stopped",
                payload={"halt_reason": halt_reason, "decision": decision},
            )
            self._persist_state()

        return validation

    # ==================================================================
    # helpers
    # ==================================================================

    def _advance_phase(self) -> None:
        """Move to the next phase in the sequence."""
        current = self.state["current_phase_key"]
        try:
            idx = _PHASE_SEQUENCE.index(current)
            if idx + 1 < len(_PHASE_SEQUENCE):
                self.state["current_phase_key"] = _PHASE_SEQUENCE[idx + 1]
                self._reset_phase_retry_state()
        except ValueError:
            pass

    def _advance_after_success(
        self, phase_key: str, validation: dict[str, Any]
    ) -> bool:
        """Apply phase-specific success transitions.

        Screening failure is a valid screening outcome, but it must not spend a
        full training run. The next phase is eval, where the iteration records
        the failed hypothesis and decision.
        """
        if (
            phase_key == "run_screening"
            and validation.get("classification") == "failed"
        ):
            self.events.emit(
                "SCREENING_FAILED",
                self.state["loop_id"],
                "running",
                round_index=self.state.get("current_round_index"),
                phase_key=phase_key,
                payload={"next_phase": "eval", "reason": "screening_failed"},
            )
            self.state["current_phase_key"] = "eval"
            self._reset_phase_retry_state()
            return True
        return False

    def _plan_context(
        self,
        *,
        lessons_limit: int = 8,
        failed_limit: int = 5,
    ) -> tuple[list[str], list[str]]:
        """Collect recent lessons and failed hypotheses from iteration_log.json."""
        log = self.validator.load_iteration_log()
        iterations = log.get("iterations", [])

        recent_lessons: list[str] = []
        failed_hypotheses: list[str] = []
        seen_lessons: set[str] = set()
        seen_failed: set[str] = set()

        for it in reversed(iterations):
            lessons = it.get("lessons", [])
            if isinstance(lessons, list):
                for lesson in reversed(lessons):
                    if (
                        isinstance(lesson, str)
                        and lesson
                        and lesson not in seen_lessons
                        and len(recent_lessons) < lessons_limit
                    ):
                        recent_lessons.append(lesson)
                        seen_lessons.add(lesson)

            hypothesis = it.get("hypothesis")
            decision = it.get("decision")
            screening_status = it.get("screening", {}).get("status")
            full_run_status = it.get("full_run", {}).get("status")
            failed = (
                decision in {"DEBUG", "PIVOT", "ABORT"}
                or screening_status == "failed"
                or full_run_status in {"failed", "recoverable_failed"}
            )
            if (
                failed
                and isinstance(hypothesis, str)
                and hypothesis
                and hypothesis not in seen_failed
                and len(failed_hypotheses) < failed_limit
            ):
                failed_hypotheses.append(hypothesis)
                seen_failed.add(hypothesis)

            if (
                len(recent_lessons) >= lessons_limit
                and len(failed_hypotheses) >= failed_limit
            ):
                break

        return recent_lessons, failed_hypotheses

    def _should_bypass_screening(self) -> bool:
        sp = self.state.get("screening_policy", {})
        if not sp.get("enabled", True):
            return True
        # Check if plan recommended screening.
        iter_id = self.state.get("current_iteration_id")
        if iter_id:
            log = self.validator.load_iteration_log()
            for it in log.get("iterations", []):
                if it.get("id") == iter_id:
                    screening = it.get("screening", {})
                    if screening.get("recommended") is False:
                        return True
        return False

    def _handle_phase_failure(
        self,
        phase_key: str,
        round_idx: int,
        *,
        external_auth_retry: bool = False,
    ) -> dict[str, Any] | None:
        """Handle a phase failure: retry or pause."""
        max_attempts = self._phase_retry_ceiling(
            external_auth_retry=external_auth_retry
        )
        attempt = self.state.get("phase_attempt", 1)

        if attempt > max_attempts:
            self.state["status"] = "paused"
            self.state["halt_reason"] = "manual_action_required"
            self._persist_state()
            self.events.emit(
                "MANUAL_ACTION_REQUIRED",
                self.state["loop_id"],
                "paused",
                round_index=round_idx,
                payload={"phase_key": phase_key, "attempts": attempt},
            )
            return None

        # Will retry on next loop iteration (phase_attempt already incremented).
        self.state["_recovery_mode"] = "retry"
        self._persist_state()
        return {"ok": False, "phase_key": phase_key, "classification": "retrying"}

    def _check_operator_signals(self) -> str | None:
        """Check for pause/stop signal files."""
        pause_file = self.workspace_root / ".auto_iterate_pause"
        stop_file = self.workspace_root / ".auto_iterate_stop"

        if stop_file.exists():
            stop_file.unlink(missing_ok=True)
            self.state["status"] = "stopped"
            self.state["halt_reason"] = "manual_stop"
            self._persist_state()
            self.events.emit(
                "LOOP_STOPPED",
                self.state["loop_id"],
                "stopped",
                payload={"halt_reason": "manual_stop"},
            )
            return "stopped"

        if pause_file.exists():
            pause_file.unlink(missing_ok=True)
            self.state["status"] = "paused"
            self.state["halt_reason"] = "operator_pause"
            self._persist_state()
            self.events.emit(
                "LOOP_PAUSED",
                self.state["loop_id"],
                "paused",
                payload={"halt_reason": "operator_pause"},
            )
            return "paused"

        return None

    def _activate_pending_goal(self) -> bool:
        if not self.goal_mgr.has_staged():
            return True
        success, errors = self.goal_mgr.activate_staged(self.state)
        if success:
            # Re-parse activated goal and update objective.
            try:
                new_goal = parse_goal(self.goal_mgr.goal_path)
                self._apply_goal_fields(new_goal)
                self.state["goal"]["activated_at"] = iso_now()
                self._persist_state()
            except Exception:
                self.events.emit(
                    "GOAL_ACTIVATION_FAILED",
                    self.state["loop_id"],
                    "paused",
                    payload={"errors": ["activated goal could not be re-parsed"]},
                )
                self.state["status"] = "paused"
                self.state["halt_reason"] = "manual_action_required"
                self._persist_state()
                return False
            self.events.emit(
                "GOAL_ACTIVATED",
                self.state["loop_id"],
                "running",
            )
            return True
        else:
            self.events.emit(
                "GOAL_ACTIVATION_FAILED",
                self.state["loop_id"],
                "paused",
                payload={"errors": errors},
            )
            self.state["status"] = "paused"
            self.state["halt_reason"] = "manual_action_required"
            self._persist_state()
            return False

    def _check_stop_conditions(self) -> str | None:
        """Check budget, patience, and target conditions."""
        budget = self.state.get("budget", {})
        llm = self.state.get("llm_budget", {})
        patience = self.state.get("patience", {})

        # Success target.
        if self._is_target_met():
            self.state["status"] = "stopped"
            self.state["halt_reason"] = "target_met"
            self._persist_state()
            return "target_met"

        # Max rounds.
        if budget.get("completed_rounds", 0) >= budget.get("max_rounds", 999):
            self.state["status"] = "stopped"
            self.state["halt_reason"] = "max_rounds_reached"
            self._persist_state()
            return "max_rounds_reached"

        # GPU budget.
        if budget.get("max_gpu_hours", 0) > 0:
            if budget.get("used_gpu_hours", 0) >= budget["max_gpu_hours"]:
                self.state["status"] = "stopped"
                self.state["halt_reason"] = "gpu_budget_exhausted"
                self._persist_state()
                return "gpu_budget_exhausted"

        # LLM budget.
        if llm.get("max_calls", 0) > 0:
            if llm.get("used_calls", 0) >= llm["max_calls"]:
                self.state["status"] = "stopped"
                self.state["halt_reason"] = "llm_budget_exhausted"
                self._persist_state()
                return "llm_budget_exhausted"

        # Patience.
        max_no_improve = patience.get("max_no_improve_rounds", 999)
        consecutive = patience.get("consecutive_no_improve", 0)
        if consecutive >= max_no_improve:
            self.state["status"] = "stopped"
            self.state["halt_reason"] = "patience_exhausted"
            self._persist_state()
            return "patience_exhausted"

        return None

    def _budget_allows_next_round(self) -> bool:
        llm = self.state.get("llm_budget", {})
        max_calls = llm.get("max_calls", 0)
        used = llm.get("used_calls", 0)
        # Need at least 5 calls for a full round (plan+code+screen+run+eval).
        if max_calls > 0 and used + 5 > max_calls:
            return False
        return True

    def _budget_halt_reason(self) -> str:
        llm = self.state.get("llm_budget", {})
        if (
            llm.get("max_calls", 0) > 0
            and llm.get("used_calls", 0) + 5 > llm["max_calls"]
        ):
            return "llm_budget_exhausted"
        return "gpu_budget_exhausted"

    def _is_target_met(self) -> bool:
        """Return True when the tracked best value has reached the goal target."""
        objective = self.state.get("objective", {}).get("primary_metric", {})
        direction = objective.get("direction")
        target = objective.get("target")
        best_value = self.state.get("best", {}).get("primary_metric")

        if direction not in ("maximize", "minimize"):
            return False
        if target is None or best_value is None:
            return False

        try:
            target_num = float(target)
            best_num = float(best_value)
        except (TypeError, ValueError):
            return False

        if direction == "maximize":
            return best_num >= target_num
        return best_num <= target_num

    def _update_best_tracking(self, round_idx: int) -> None:
        """Update best iteration and patience tracking after eval."""
        iter_id = self.state.get("current_iteration_id")
        if not iter_id:
            return

        log = self.validator.load_iteration_log()
        for it in log.get("iterations", []):
            if it.get("id") == iter_id:
                metrics = iteration_metrics(it)
                pm_name = (
                    self.state.get("objective", {})
                    .get("primary_metric", {})
                    .get("name")
                )
                if pm_name and pm_name in metrics:
                    new_val = _numeric_metric_value(metrics[pm_name], pm_name)
                    old_val = self.state["best"].get("primary_metric")
                    old_num = (
                        _numeric_metric_value(old_val, pm_name)
                        if old_val is not None
                        else None
                    )
                    direction = (
                        self.state.get("objective", {})
                        .get("primary_metric", {})
                        .get("direction", "maximize")
                    )
                    delta = float(
                        self.state.get("patience", {}).get("min_primary_delta", 0)
                    )

                    improved = False
                    if old_num is None:
                        improved = True
                    elif direction == "maximize" and new_val > old_num + delta:
                        improved = True
                    elif direction == "minimize" and new_val < old_num - delta:
                        improved = True

                    if improved:
                        self.state["best"] = {
                            "iteration_id": iter_id,
                            "round_index": round_idx,
                            "primary_metric": new_val,
                            "updated_at": iso_now(),
                        }
                        self.state["patience"]["consecutive_no_improve"] = 0
                        self.events.emit(
                            "NEW_BEST",
                            self.state["loop_id"],
                            "running",
                            round_index=round_idx,
                            payload={
                                "iteration_id": iter_id,
                                "primary_metric": new_val,
                                "previous_best": old_val,
                            },
                        )
                    else:
                        self.state["patience"]["consecutive_no_improve"] = (
                            self.state["patience"].get("consecutive_no_improve", 0) + 1
                        )
                break

    def _objective_primary_metric_name(self) -> str | None:
        value = (
            self.state.get("objective", {})
            .get("primary_metric", {})
            .get("name")
        )
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _persist_state(self) -> None:
        """Write state to disk (strip internal keys)."""
        to_save = {k: v for k, v in self.state.items() if not k.startswith("_")}
        self.store.save_state(to_save)

    def _policy_from_state(self, fallback: dict[str, Any]) -> dict[str, Any]:
        policy = copy.deepcopy(fallback)
        for key in _PERSISTED_POLICY_KEYS:
            if key in self.state:
                state_value = self.state[key]
                if isinstance(state_value, dict) and isinstance(policy.get(key), dict):
                    policy[key] = _merge_with_fallback(state_value, policy[key])
                else:
                    policy[key] = copy.deepcopy(state_value)
        if "screening_policy" in self.state:
            policy["screening_policy"] = copy.deepcopy(self.state["screening_policy"])
        return policy

    def _ensure_policy_fields_in_state(self) -> None:
        for key in _PERSISTED_POLICY_KEYS:
            fallback_value = self.policy.get(key, DEFAULT_POLICY.get(key))
            if key not in self.state:
                self.state[key] = copy.deepcopy(fallback_value)
            elif isinstance(self.state.get(key), dict) and isinstance(
                fallback_value, dict
            ):
                self.state[key] = _merge_with_fallback(self.state[key], fallback_value)

    def _reset_phase_retry_state(self) -> None:
        self.state["phase_attempt"] = 1

    def _run_phase_full_access(self) -> bool:
        runtime = self.state.get("runtime", self.policy.get("runtime", {}))
        if not isinstance(runtime, dict):
            return True
        return bool(runtime.get("run_phase_full_access", True))

    def _rotate_events_if_needed(self, round_idx: int | None = None) -> None:
        event_log = self.state.get("event_log", self.policy.get("event_log", {}))
        if not isinstance(event_log, dict):
            return
        try:
            rotate_bytes = int(event_log.get("rotate_bytes", 0))
        except (TypeError, ValueError):
            return
        if rotate_bytes <= 0:
            return
        archive = self.events.rotate_if_needed(rotate_bytes)
        if archive:
            self.events.emit(
                "EVENT_LOG_ROTATED",
                self.state.get("loop_id", ""),
                self.state.get("status", "running"),
                round_index=round_idx,
                payload={"archive": archive, "rotate_bytes": rotate_bytes},
            )

    def _run_dynamic_context_preflight(
        self,
        *,
        allow_draft: bool = False,
        allow_review_required: bool = False,
    ) -> bool:
        """Run the dynamic-context gate suite before autonomous WF10 starts."""
        preflight_path = self.auto_dir / "dynamic_context_preflight.json"
        checker_path = (
            self.workspace_root / "tooling" / "evidence" / "check_dynamic_context.py"
        )
        if not checker_path.exists():
            dynamic_markers = self._dynamic_context_markers_present()
            ok = not dynamic_markers
            summary = {
                "ok": ok,
                "applicability": (
                    "legacy_or_standard_tooling_missing"
                    if ok
                    else "dynamic_context_tooling_missing"
                ),
                "stage": "wf10",
                "checked_at": iso_now(),
            }
            atomic_write_json(
                preflight_path,
                summary,
            )
            self.state["dynamic_preflight"] = summary
            return ok

        spec = importlib.util.spec_from_file_location(
            "harness_auto_iterate_check_dynamic_context",
            checker_path,
        )
        if spec is None or spec.loader is None:
            summary = {
                "ok": False,
                "applicability": "dynamic_context",
                "stage": "wf10",
                "checked_at": iso_now(),
                "error": "cannot_load_check_dynamic_context",
            }
            atomic_write_json(
                preflight_path,
                summary,
            )
            self.state["dynamic_preflight"] = summary
            return False

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check_dynamic_context(
            self.workspace_root,
            stage="wf10",
            allow_draft=allow_draft,
            allow_review_required=allow_review_required,
            write_review_packet=True,
        )
        summary = {
            "ok": bool(result.get("ok")),
            "applicability": "dynamic_context",
            "stage": result.get("stage", "wf10"),
            "checked_at": iso_now(),
            "allow_draft_contract": allow_draft,
            "allow_review_required": allow_review_required,
            "summary": result.get("summary", {}),
            "error_count": result.get("error_count", 0),
            "warning_count": result.get("warning_count", 0),
            "review_packet": result.get("review_packet"),
        }
        atomic_write_json(
            preflight_path,
            summary,
        )
        self.state["dynamic_preflight"] = summary
        return bool(result.get("ok"))

    def _record_dynamic_preflight_skip(self, *, reason: str | None) -> None:
        summary = {
            "ok": True,
            "applicability": "skipped_by_operator",
            "stage": "wf10",
            "checked_at": iso_now(),
            "reason": reason,
        }
        self.state["dynamic_preflight"] = summary
        atomic_write_json(self.auto_dir / "dynamic_context_preflight.json", summary)
        self.events.emit(
            "DYNAMIC_PREFLIGHT_SKIPPED",
            self.state.get("loop_id", ""),
            self.state.get("status", "running"),
            payload={"reason": reason},
        )

    def _pause_for_dynamic_preflight_failure(self, loop_id: str) -> None:
        self.state["status"] = "paused"
        self.state["halt_reason"] = "manual_action_required"
        self.state["last_failure"] = "dynamic_context_preflight_failed"
        self._persist_state()
        self.events.emit(
            "MANUAL_ACTION_REQUIRED",
            loop_id,
            "paused",
            payload={"reason": "dynamic_context_preflight_failed"},
        )

    def _dynamic_context_markers_present(self) -> bool:
        state_path = self.workspace_root / "PROJECT_STATE.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}

        if state.get("context_model_version") == "dynamic-protocol-v1":
            return True
        if state.get("workflow_mode") == "dynamic_context":
            return True

        dynamic_dirs = (
            "docs/10_contract",
            "docs/20_facts",
            "docs/30_evidence",
            "docs/35_protocol",
        )
        return any((self.workspace_root / path).exists() for path in dynamic_dirs)

    def _phase_retry_ceiling(self, *, external_auth_retry: bool = False) -> int:
        retry_policy = self.state.get(
            "retry_policy", self.policy.get("retry_policy", {})
        )
        if not isinstance(retry_policy, dict):
            retry_policy = {}

        raw_max_attempts = retry_policy.get("max_phase_attempts", 2)
        try:
            max_attempts = int(raw_max_attempts)
        except (TypeError, ValueError):
            max_attempts = 2
        max_attempts = max(1, max_attempts)

        if not external_auth_retry:
            return max_attempts

        raw_external_attempts = retry_policy.get("max_external_auth_attempts", 6)
        try:
            external_attempts = int(raw_external_attempts)
        except (TypeError, ValueError):
            external_attempts = 6
        max_attempts = max(max_attempts, external_attempts)

        return max_attempts

    def _apply_goal_fields(self, parsed_goal: dict[str, Any]) -> None:
        self.state["objective"] = parsed_goal.get(
            "objective", self.state.get("objective", {})
        )
        self.state["initial_hypotheses"] = parsed_goal.get("initial_hypotheses", [])
        self.state["forbidden_directions"] = parsed_goal.get("forbidden_directions", [])

        patience = parsed_goal.get("patience", {})
        if patience:
            current_patience = self.state.get("patience", {})
            current_patience["max_no_improve_rounds"] = patience.get(
                "max_no_improve_rounds",
                current_patience.get("max_no_improve_rounds"),
            )
            current_patience["min_primary_delta"] = patience.get(
                "min_primary_delta",
                current_patience.get("min_primary_delta"),
            )
            self.state["patience"] = current_patience

        budget = parsed_goal.get("budget", {})
        if budget:
            current_budget = self.state.get("budget", {})
            current_budget["max_rounds"] = budget.get(
                "max_rounds", current_budget.get("max_rounds")
            )
            current_budget["max_gpu_hours"] = budget.get(
                "max_gpu_hours",
                current_budget.get("max_gpu_hours"),
            )
            self.state["budget"] = current_budget

        screening_policy = parsed_goal.get("screening_policy")
        if isinstance(screening_policy, dict):
            self.state["screening_policy"] = copy.deepcopy(screening_policy)

    def _cleanup(self) -> None:
        """Stop heartbeat and release lock."""
        if self.heartbeat:
            self.heartbeat.stop()
        if self.lock_mgr:
            self.lock_mgr.release()

    def _record_fatal_controller_error(self, error: str) -> None:
        """Persist a fatal controller failure on a best-effort basis."""
        self.state["status"] = "failed"
        self.state["halt_reason"] = "fatal_controller_error"
        self.state["last_failure"] = error
        try:
            self.store.ensure_dirs()
            self._persist_state()
            if self.state.get("loop_id"):
                self.events.emit(
                    "LOOP_FAILED",
                    self.state["loop_id"],
                    "failed",
                    payload={"reason": error},
                )
        except Exception:
            pass

    def _map_exit_code(self) -> int:
        """Map current state to an exit code."""
        hr = self.state.get("halt_reason")
        status = self.state.get("status")
        if status == "running":
            return EXIT_OK
        mapping = {
            "manual_stop": EXIT_OK,
            "target_met": EXIT_OK,
            "max_rounds_reached": EXIT_OK,
            "patience_exhausted": EXIT_OK,
            "workflow_continue": EXIT_OK,
            "workflow_pivot": EXIT_OK,
            "workflow_abort": EXIT_OK,
            "gpu_budget_exhausted": EXIT_BUDGET_EXHAUSTED,
            "llm_budget_exhausted": EXIT_BUDGET_EXHAUSTED,
            "manual_action_required": EXIT_MANUAL_ACTION,
            "operator_pause": EXIT_RESUMABLE,
            "fatal_controller_error": EXIT_FATAL,
        }
        return mapping.get(hr, EXIT_OK)

    # ==================================================================
    # Operator commands (non-loop)
    # ==================================================================

    def status(self, *, as_json: bool = False) -> dict[str, Any] | str:
        """Return current loop status."""
        try:
            state = self.store.load_state()
        except StateLoadError:
            return (
                {"error": "No active loop"}
                if as_json
                else "No active auto-iterate loop."
            )

        if as_json:
            return {
                "schema_version": state.get("schema_version"),
                "loop_id": state.get("loop_id"),
                "status": state.get("status"),
                "halt_reason": state.get("halt_reason"),
                "current_round_index": state.get("current_round_index"),
                "current_phase_key": state.get("current_phase_key"),
                "current_iteration_id": state.get("current_iteration_id"),
                "accounts": {
                    "selected_account_id": state.get("accounts", {}).get(
                        "selected_account_id"
                    )
                },
                "objective": {
                    "primary_metric": {
                        "name": state.get("objective", {})
                        .get("primary_metric", {})
                        .get("name")
                    }
                },
                "best": {"primary_metric": state.get("best", {}).get("primary_metric")},
                "budget": {
                    "completed_rounds": state.get("budget", {}).get("completed_rounds"),
                    "max_rounds": state.get("budget", {}).get("max_rounds"),
                },
                "llm_budget": {
                    "used_calls": state.get("llm_budget", {}).get("used_calls"),
                    "max_calls": state.get("llm_budget", {}).get("max_calls"),
                },
                "last_decision": state.get("last_decision"),
                "last_failure": state.get("last_failure"),
            }

        lines = [
            f"Loop: {state.get('loop_id')}",
            f"Status: {state.get('status')}",
            f"Round: {state.get('current_round_index')} / {state.get('budget', {}).get('max_rounds')}",
            f"Phase: {state.get('current_phase_key')}",
            f"Best: {state.get('best', {}).get('primary_metric')} ({state.get('best', {}).get('iteration_id')})",
            f"Decision: {state.get('last_decision')}",
        ]
        if state.get("halt_reason"):
            lines.append(f"Halt: {state['halt_reason']}")
        return "\n".join(lines)

    def tail_events(self, lines: int = 20, *, jsonl: bool = False) -> list[Any]:
        """Return recent events."""
        return self.events.tail(lines=lines, jsonl=jsonl)

    def pause(self) -> bool:
        """Create a pause signal file."""
        signal = self.workspace_root / ".auto_iterate_pause"
        signal.touch()
        return True

    def stop(self) -> bool:
        """Create a stop signal file."""
        signal = self.workspace_root / ".auto_iterate_stop"
        signal.touch()
        return True

    def override_goal(self, goal_path: str) -> int:
        """Stage a new goal for activation at the next round boundary."""
        try:
            parsed = parse_goal(goal_path)
            errors = validate_goal(parsed)
            if errors:
                return EXIT_GOAL_VALIDATION
        except Exception:
            return EXIT_GOAL_VALIDATION

        self.goal_mgr.stage_next(goal_path)
        self.events.emit(
            "GOAL_STAGED",
            self.state.get("loop_id", ""),
            self.state.get("status", "unknown"),
            payload={"source": goal_path},
        )
        return EXIT_OK
