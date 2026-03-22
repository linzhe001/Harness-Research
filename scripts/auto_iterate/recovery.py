"""Recovery engine for the auto-iterate controller.

Determines how to resume after a crash or interruption by inspecting
the durable state (``state.json``) and the repository
(``iteration_log.json``).

See ``01_contract_freeze.md`` §9 for the frozen recovery contract.
"""

from __future__ import annotations

from typing import Any

from .postcondition import PostconditionValidator, _get_iteration


# ---------------------------------------------------------------------------
# Recovery actions
# ---------------------------------------------------------------------------

RERUN = "rerun"
ADOPT = "adopt"
FAIL = "fail"


def recovery_action(
    phase_key: str,
    iteration_id: str | None,
    iterations: list[dict[str, Any]],
    phase_attempt: int,
    max_phase_attempts: int,
) -> tuple[str, str]:
    """Determine recovery action for the current phase.

    Returns ``(action, reason)`` where action is one of
    ``RERUN``, ``ADOPT``, ``FAIL``.
    """
    if phase_attempt >= max_phase_attempts:
        return FAIL, f"phase_attempt={phase_attempt} >= max={max_phase_attempts}"

    if phase_key == "plan":
        return _recover_plan(iteration_id, iterations)
    elif phase_key == "code":
        return _recover_code(iteration_id, iterations)
    elif phase_key == "run_screening":
        return _recover_run_screening(iteration_id, iterations)
    elif phase_key == "run_full":
        return _recover_run_full(iteration_id, iterations)
    elif phase_key == "eval":
        return _recover_eval(iteration_id, iterations)
    else:
        return FAIL, f"Unknown phase_key: {phase_key}"


# -- plan -------------------------------------------------------------------

def _recover_plan(
    iteration_id: str | None,
    iterations: list[dict[str, Any]],
) -> tuple[str, str]:
    # Look for a planned iteration that could be the one we were creating.
    planned = [it for it in iterations if it.get("status") == "planned"]
    if len(planned) == 0:
        return RERUN, "no planned iteration found"
    if len(planned) == 1 and planned[0].get("hypothesis"):
        return ADOPT, f"adopting existing planned iteration {planned[0]['id']}"
    return RERUN, "ambiguous planned iterations or missing hypothesis"


# -- code -------------------------------------------------------------------

def _recover_code(
    iteration_id: str | None,
    iterations: list[dict[str, Any]],
) -> tuple[str, str]:
    if iteration_id is None:
        return FAIL, "current_iteration_id not bound"

    it = _get_iteration(iterations, iteration_id)
    if it is None:
        return FAIL, f"iteration {iteration_id} not found"

    status = it.get("status", "")
    if status in ("planned", "coding"):
        return RERUN, f"status={status}, code phase incomplete"
    if status == "training" and it.get("git_commit"):
        return ADOPT, "status=training with complete git_commit"
    return RERUN, f"status={status}, git_commit missing or incomplete"


# -- run_screening ----------------------------------------------------------

def _recover_run_screening(
    iteration_id: str | None,
    iterations: list[dict[str, Any]],
) -> tuple[str, str]:
    if iteration_id is None:
        return FAIL, "current_iteration_id not bound"

    it = _get_iteration(iterations, iteration_id)
    if it is None:
        return FAIL, f"iteration {iteration_id} not found"

    screening = it.get("screening", {})
    s_status = screening.get("status")
    if s_status in ("passed", "failed", "skipped"):
        return ADOPT, f"screening.status={s_status} (terminal)"
    if it.get("status") == "training":
        return RERUN, "screening record missing, iteration still training"
    return RERUN, f"screening incomplete, status={s_status}"


# -- run_full ---------------------------------------------------------------

def _recover_run_full(
    iteration_id: str | None,
    iterations: list[dict[str, Any]],
) -> tuple[str, str]:
    if iteration_id is None:
        return FAIL, "current_iteration_id not bound"

    it = _get_iteration(iterations, iteration_id)
    if it is None:
        return FAIL, f"iteration {iteration_id} not found"

    full_run = it.get("full_run", {})
    fr_status = full_run.get("status")

    if fr_status == "completed":
        return ADOPT, "full_run.status=completed"
    if fr_status == "failed":
        return ADOPT, "full_run.status=failed (terminal)"
    if fr_status == "recoverable_failed":
        return RERUN, "full_run.status=recoverable_failed, will retry"
    if it.get("status") == "training" and fr_status is None:
        return RERUN, "no full_run record, iteration still training"
    return RERUN, f"full_run incomplete, status={fr_status}"


# -- eval -------------------------------------------------------------------

def _recover_eval(
    iteration_id: str | None,
    iterations: list[dict[str, Any]],
) -> tuple[str, str]:
    if iteration_id is None:
        return FAIL, "current_iteration_id not bound"

    it = _get_iteration(iterations, iteration_id)
    if it is None:
        return FAIL, f"iteration {iteration_id} not found"

    if it.get("status") == "completed" and it.get("decision") and it.get("lessons"):
        return ADOPT, "iteration already completed with decision and lessons"
    return RERUN, "eval incomplete"


# ---------------------------------------------------------------------------
# RecoveryEngine
# ---------------------------------------------------------------------------

class RecoveryEngine:
    """Orchestrates recovery by combining state inspection with repository
    postcondition checks."""

    def __init__(self, validator: PostconditionValidator) -> None:
        self.validator = validator

    def recover(
        self,
        state: dict[str, Any],
        max_phase_attempts: int = 2,
    ) -> dict[str, Any]:
        """Inspect the current state and return a recovery plan.

        Returns a dict with:
        - ``action``: ``"rerun"`` | ``"adopt"`` | ``"fail"``
        - ``reason``: human-readable explanation
        - ``adopted_iteration_id``: set if action == adopt for plan phase
        - ``phase_key``: the phase being recovered
        """
        phase_key = state.get("current_phase_key", "plan")
        iteration_id = state.get("current_iteration_id")
        phase_attempt = state.get("phase_attempt", 1)

        log = self.validator.load_iteration_log()
        iterations = log.get("iterations", [])

        action, reason = recovery_action(
            phase_key=phase_key,
            iteration_id=iteration_id,
            iterations=iterations,
            phase_attempt=phase_attempt,
            max_phase_attempts=max_phase_attempts,
        )

        result: dict[str, Any] = {
            "action": action,
            "reason": reason,
            "phase_key": phase_key,
            "iteration_id": iteration_id,
        }

        # For plan phase adopt, extract the adopted iteration_id.
        if phase_key == "plan" and action == ADOPT:
            planned = [it for it in iterations if it.get("status") == "planned"]
            if planned:
                result["adopted_iteration_id"] = planned[0]["id"]

        return result
