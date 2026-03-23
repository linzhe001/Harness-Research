"""Tests for the recovery engine and resume flow.

Tests cover:
- Stale lock detection and cleanup
- Resume after crash per phase (plan, code, run_screening, run_full, eval)
- Retry ceiling → manual_action_required
- Phase-specific recovery action determination
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tooling" / "auto_iterate" / "scripts"))

from auto_iterate.recovery import (
    ADOPT,
    FAIL,
    RERUN,
    RecoveryEngine,
    recovery_action,
)
from auto_iterate.postcondition import PostconditionValidator
from auto_iterate.state import atomic_write_json, load_json
from auto_iterate.lock import LockManager

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "auto_iterate"


# ===================================================================
# recovery_action unit tests
# ===================================================================

class TestRecoveryAction:
    # -- plan ---------------------------------------------------------------

    def test_plan_no_planned(self) -> None:
        action, reason = recovery_action("plan", None, [], 1, 2)
        assert action == RERUN

    def test_plan_one_planned_with_hypothesis(self) -> None:
        iters = [{"id": "iter1", "status": "planned", "hypothesis": "test"}]
        action, reason = recovery_action("plan", None, iters, 1, 2)
        assert action == ADOPT

    def test_plan_one_planned_no_hypothesis(self) -> None:
        iters = [{"id": "iter1", "status": "planned"}]
        action, reason = recovery_action("plan", None, iters, 1, 2)
        assert action == RERUN

    def test_plan_uses_existing_ids_binding_when_available(self) -> None:
        iters = [
            {"id": "iter_old", "status": "planned", "hypothesis": "old"},
            {"id": "iter_new", "status": "planned", "hypothesis": "new"},
        ]
        action, reason = recovery_action(
            "plan",
            None,
            iters,
            2,
            2,
            existing_ids={"iter_old"},
        )
        assert action == ADOPT
        assert "iter_new" in reason

    # -- code ---------------------------------------------------------------

    def test_code_status_planned(self) -> None:
        iters = [{"id": "iter1", "status": "planned"}]
        action, reason = recovery_action("code", "iter1", iters, 1, 2)
        assert action == RERUN

    def test_code_status_coding(self) -> None:
        iters = [{"id": "iter1", "status": "coding"}]
        action, reason = recovery_action("code", "iter1", iters, 1, 2)
        assert action == RERUN

    def test_code_status_training_with_commit(self) -> None:
        iters = [{"id": "iter1", "status": "training", "git_commit": "abc"}]
        action, reason = recovery_action("code", "iter1", iters, 1, 2)
        assert action == ADOPT

    def test_code_status_training_no_commit(self) -> None:
        iters = [{"id": "iter1", "status": "training"}]
        action, reason = recovery_action("code", "iter1", iters, 1, 2)
        assert action == RERUN

    # -- run_screening ------------------------------------------------------

    def test_screening_passed(self) -> None:
        iters = [{"id": "iter1", "status": "training",
                   "screening": {"status": "passed"}}]
        action, reason = recovery_action("run_screening", "iter1", iters, 1, 2)
        assert action == ADOPT

    def test_screening_missing(self) -> None:
        iters = [{"id": "iter1", "status": "training"}]
        action, reason = recovery_action("run_screening", "iter1", iters, 1, 2)
        assert action == RERUN

    # -- run_full -----------------------------------------------------------

    def test_full_completed(self) -> None:
        iters = [{"id": "iter1", "status": "training",
                   "full_run": {"status": "completed"}}]
        action, reason = recovery_action("run_full", "iter1", iters, 1, 2)
        assert action == ADOPT

    def test_full_recoverable_failed(self) -> None:
        iters = [{"id": "iter1", "status": "training",
                   "full_run": {"status": "recoverable_failed"}}]
        action, reason = recovery_action("run_full", "iter1", iters, 1, 2)
        assert action == RERUN

    def test_full_failed_terminal(self) -> None:
        iters = [{"id": "iter1", "status": "training",
                   "full_run": {"status": "failed"}}]
        action, reason = recovery_action("run_full", "iter1", iters, 1, 2)
        assert action == ADOPT

    def test_full_no_record(self) -> None:
        iters = [{"id": "iter1", "status": "training"}]
        action, reason = recovery_action("run_full", "iter1", iters, 1, 2)
        assert action == RERUN

    # -- eval ---------------------------------------------------------------

    def test_eval_completed(self) -> None:
        iters = [{"id": "iter1", "status": "completed",
                   "decision": "NEXT_ROUND", "lessons": ["x"],
                   "metrics": {"PSNR": 30.1}}]
        action, reason = recovery_action("eval", "iter1", iters, 1, 2)
        assert action == ADOPT

    def test_eval_incomplete(self) -> None:
        iters = [{"id": "iter1", "status": "training"}]
        action, reason = recovery_action("eval", "iter1", iters, 1, 2)
        assert action == RERUN

    def test_eval_missing_metrics(self) -> None:
        iters = [{"id": "iter1", "status": "completed",
                   "decision": "NEXT_ROUND", "lessons": ["x"]}]
        action, reason = recovery_action("eval", "iter1", iters, 1, 2)
        assert action == RERUN

    # -- retry ceiling ------------------------------------------------------

    def test_retry_ceiling_reached(self) -> None:
        iters = [{"id": "iter1", "status": "planned"}]
        action, reason = recovery_action("plan", None, iters, 3, 2)
        assert action == FAIL

    def test_retry_ceiling_not_reached(self) -> None:
        action, reason = recovery_action("plan", None, [], 1, 2)
        assert action == RERUN

    # -- edge cases ---------------------------------------------------------

    def test_unbound_iteration_code(self) -> None:
        action, reason = recovery_action("code", None, [], 1, 2)
        assert action == FAIL

    def test_unknown_phase(self) -> None:
        action, reason = recovery_action("bogus", "iter1", [], 1, 2)
        assert action == FAIL


# ===================================================================
# RecoveryEngine integration
# ===================================================================

class TestRecoveryEngine:
    def _make_engine(self, tmp_path: Path, iterations: list[dict]) -> RecoveryEngine:
        log = {"project": "test", "iterations": iterations}
        atomic_write_json(tmp_path / "iteration_log.json", log)
        validator = PostconditionValidator(tmp_path)
        return RecoveryEngine(validator)

    def test_recover_plan_adopt(self, tmp_path: Path) -> None:
        engine = self._make_engine(tmp_path, [
            {"id": "iter1", "status": "planned", "hypothesis": "test"},
        ])
        state = {"current_phase_key": "plan", "current_iteration_id": None, "phase_attempt": 1}
        result = engine.recover(state)
        assert result["action"] == ADOPT
        assert result["adopted_iteration_id"] == "iter1"

    def test_recover_plan_uses_bound_iteration_id(self, tmp_path: Path) -> None:
        engine = self._make_engine(tmp_path, [
            {"id": "iter_old", "status": "planned", "hypothesis": "old"},
            {"id": "iter_new", "status": "planned", "hypothesis": "new"},
        ])
        state = {
            "current_phase_key": "plan",
            "current_iteration_id": None,
            "phase_attempt": 2,
            "plan_binding": {"existing_ids": ["iter_old"]},
        }
        result = engine.recover(state)
        assert result["action"] == ADOPT
        assert result["adopted_iteration_id"] == "iter_new"

    def test_recover_code_rerun(self, tmp_path: Path) -> None:
        engine = self._make_engine(tmp_path, [
            {"id": "iter1", "status": "coding"},
        ])
        state = {"current_phase_key": "code", "current_iteration_id": "iter1", "phase_attempt": 1}
        result = engine.recover(state)
        assert result["action"] == RERUN

    def test_recover_over_ceiling(self, tmp_path: Path) -> None:
        engine = self._make_engine(tmp_path, [
            {"id": "iter1", "status": "coding"},
        ])
        state = {"current_phase_key": "code", "current_iteration_id": "iter1", "phase_attempt": 3}
        result = engine.recover(state, max_phase_attempts=2)
        assert result["action"] == FAIL


# ===================================================================
# Stale lock in resume context
# ===================================================================

class TestStaleLockResume:
    def test_stale_lock_cleared_on_resume(self, tmp_path: Path) -> None:
        """A stale lock should be cleared and resume should proceed."""
        # Create a stale lock.
        lm = LockManager(tmp_path / "lock.json", stale_threshold_sec=0)
        lm.acquire("old_loop", "codex", str(tmp_path))
        time.sleep(0.05)
        assert lm.is_stale()

        # Verify it can be cleared.
        cleared = lm.clear_stale()
        assert cleared is not None
        assert cleared["loop_id"] == "old_loop"
        assert not (tmp_path / "lock.json").exists()
