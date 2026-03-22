"""Repository postcondition validator.

Phase success is determined *only* by inspecting the repository state
(``iteration_log.json``, ``PROJECT_STATE.json``), never from runtime
stdout, chat prose, or runtime metadata.

See ``01_contract_freeze.md`` §4.4 for the frozen postcondition table
and §4.5 for the ``current_iteration_id`` binding algorithm.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .state import load_json, StateLoadError


# ---------------------------------------------------------------------------
# Result dataclass (plain dict for simplicity)
# ---------------------------------------------------------------------------

def _ok(phase_key: str, classification: str, iteration_id: str | None,
        payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "phase_key": phase_key,
        "classification": classification,
        "iteration_id": iteration_id,
        "payload": payload or {},
    }


def _fail(phase_key: str, classification: str, iteration_id: str | None,
          payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "phase_key": phase_key,
        "classification": classification,
        "iteration_id": iteration_id,
        "payload": payload or {},
    }


# ---------------------------------------------------------------------------
# current_iteration_id binding (01§4.5)
# ---------------------------------------------------------------------------

def bind_iteration_id(
    pre_ids: set[str],
    post_ids: set[str],
) -> tuple[str | None, str | None]:
    """Return ``(iteration_id, error_message)``.

    Exactly one new ID must appear; otherwise return an error.
    """
    new_ids = post_ids - pre_ids
    if len(new_ids) == 0:
        return None, "plan did not create a new iteration entry"
    if len(new_ids) > 1:
        return None, f"plan created {len(new_ids)} entries (ambiguous): {sorted(new_ids)}"
    return new_ids.pop(), None


# ---------------------------------------------------------------------------
# Per-phase validators
# ---------------------------------------------------------------------------

def _get_iteration(iterations: list[dict], iteration_id: str) -> dict | None:
    for it in iterations:
        if it.get("id") == iteration_id:
            return it
    return None


def _get_ids(iterations: list[dict]) -> set[str]:
    return {it["id"] for it in iterations if "id" in it}


class PostconditionValidator:
    """Validates repository postconditions after each phase."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root)
        self.iter_log_path = self.root / "iteration_log.json"

    def load_iteration_log(self) -> dict[str, Any]:
        try:
            return load_json(self.iter_log_path)
        except StateLoadError:
            return {"iterations": []}

    def get_iteration_ids(self) -> set[str]:
        log = self.load_iteration_log()
        return _get_ids(log.get("iterations", []))

    def validate(
        self,
        phase_key: str,
        current_iteration_id: str | None,
        *,
        pre_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        """Run the postcondition check for *phase_key*.

        For ``plan``, *pre_ids* must be the set of iteration IDs before
        the phase ran; the validator computes new IDs and binds
        ``current_iteration_id``.

        For all other phases, *current_iteration_id* must already be
        bound (set during the ``plan`` phase).
        """
        log = self.load_iteration_log()
        iterations = log.get("iterations", [])

        if phase_key == "plan":
            return self._validate_plan(iterations, pre_ids or set())
        elif phase_key == "code":
            return self._validate_code(iterations, current_iteration_id)
        elif phase_key == "run_screening":
            return self._validate_run_screening(iterations, current_iteration_id)
        elif phase_key == "run_full":
            return self._validate_run_full(iterations, current_iteration_id)
        elif phase_key == "eval":
            return self._validate_eval(iterations, current_iteration_id)
        else:
            return _fail(phase_key, "unknown_phase", current_iteration_id,
                         {"error": f"Unknown phase_key: {phase_key}"})

    # -- plan ---------------------------------------------------------------

    def _validate_plan(
        self, iterations: list[dict], pre_ids: set[str],
    ) -> dict[str, Any]:
        post_ids = _get_ids(iterations)
        iter_id, err = bind_iteration_id(pre_ids, post_ids)
        if err:
            return _fail("plan", "postcondition_failed", None,
                         {"error": err})

        it = _get_iteration(iterations, iter_id)  # type: ignore[arg-type]
        if it is None:
            return _fail("plan", "postcondition_failed", iter_id,
                         {"error": "New iteration not found after binding"})

        if it.get("status") != "planned":
            return _fail("plan", "postcondition_failed", iter_id,
                         {"error": f"Expected status=planned, got {it.get('status')!r}"})

        # Check required plan fields
        missing = []
        if not it.get("hypothesis"):
            missing.append("hypothesis")
        if missing:
            return _fail("plan", "postcondition_failed", iter_id,
                         {"missing_fields": missing})

        return _ok("plan", "planned", iter_id)

    # -- code ---------------------------------------------------------------

    def _validate_code(
        self, iterations: list[dict], iteration_id: str | None,
    ) -> dict[str, Any]:
        if iteration_id is None:
            return _fail("code", "postcondition_failed", None,
                         {"error": "current_iteration_id not bound"})

        it = _get_iteration(iterations, iteration_id)
        if it is None:
            return _fail("code", "postcondition_failed", iteration_id,
                         {"error": f"Iteration {iteration_id} not found"})

        if it.get("status") != "training":
            return _fail("code", "postcondition_failed", iteration_id,
                         {"error": f"Expected status=training, got {it.get('status')!r}"})

        if not it.get("git_commit"):
            return _fail("code", "postcondition_failed", iteration_id,
                         {"missing_fields": ["git_commit"]})
        if not it.get("git_message"):
            return _fail("code", "postcondition_failed", iteration_id,
                         {"missing_fields": ["git_message"]})

        return _ok("code", "training", iteration_id)

    # -- run_screening ------------------------------------------------------

    def _validate_run_screening(
        self, iterations: list[dict], iteration_id: str | None,
    ) -> dict[str, Any]:
        if iteration_id is None:
            return _fail("run_screening", "postcondition_failed", None,
                         {"error": "current_iteration_id not bound"})

        it = _get_iteration(iterations, iteration_id)
        if it is None:
            return _fail("run_screening", "postcondition_failed", iteration_id,
                         {"error": f"Iteration {iteration_id} not found"})

        screening = it.get("screening", {})
        status = screening.get("status")
        if status not in ("passed", "failed", "skipped"):
            return _fail("run_screening", "postcondition_failed", iteration_id,
                         {"error": f"screening.status={status!r}, expected passed|failed|skipped"})

        return _ok("run_screening", status, iteration_id,
                    {"screening_status": status})

    # -- run_full -----------------------------------------------------------

    def _validate_run_full(
        self, iterations: list[dict], iteration_id: str | None,
    ) -> dict[str, Any]:
        if iteration_id is None:
            return _fail("run_full", "postcondition_failed", None,
                         {"error": "current_iteration_id not bound"})

        it = _get_iteration(iterations, iteration_id)
        if it is None:
            return _fail("run_full", "postcondition_failed", iteration_id,
                         {"error": f"Iteration {iteration_id} not found"})

        full_run = it.get("full_run", {})
        status = full_run.get("status")
        if status not in ("completed", "recoverable_failed", "failed"):
            return _fail("run_full", "postcondition_failed", iteration_id,
                         {"error": f"full_run.status={status!r}, expected completed|recoverable_failed|failed"})

        return _ok("run_full", status, iteration_id,
                    {"full_run_status": status})

    # -- eval ---------------------------------------------------------------

    def _validate_eval(
        self, iterations: list[dict], iteration_id: str | None,
    ) -> dict[str, Any]:
        if iteration_id is None:
            return _fail("eval", "postcondition_failed", None,
                         {"error": "current_iteration_id not bound"})

        it = _get_iteration(iterations, iteration_id)
        if it is None:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": f"Iteration {iteration_id} not found"})

        if it.get("status") != "completed":
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": f"Expected status=completed, got {it.get('status')!r}"})

        decision = it.get("decision")
        valid_decisions = {"NEXT_ROUND", "DEBUG", "CONTINUE", "PIVOT", "ABORT"}
        if decision not in valid_decisions:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": f"decision={decision!r}, expected one of {valid_decisions}"})

        lessons = it.get("lessons", [])
        if not lessons:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": "At least 1 lesson is required"})

        return _ok("eval", "completed", iteration_id,
                    {"decision": decision})
