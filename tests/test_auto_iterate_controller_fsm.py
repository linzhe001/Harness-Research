"""Tests for the controller state machine and CLI.

Tests cover:
- Decision transitions (NEXT_ROUND, DEBUG, CONTINUE, PIVOT, ABORT)
- Screening bypass logic
- Budget exhaustion
- Operator pause/stop signals
- CLI exit codes
- dry_run walk-through
- status --json output
"""

from __future__ import annotations

import json
import shutil
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tooling" / "auto_iterate" / "scripts"))

from auto_iterate.controller import (
    EXIT_BUDGET_EXHAUSTED,
    EXIT_GOAL_VALIDATION,
    EXIT_INVALID_ARGS,
    EXIT_LOCK_CONFLICT,
    EXIT_MANUAL_ACTION,
    EXIT_OK,
    EXIT_RESUMABLE,
    LoopController,
    _DECISION_HALT,
)
from auto_iterate.state import load_json, atomic_write_json
from auto_iterate.events import EventLogger

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "auto_iterate"
CONTRACTS = FIXTURES / "contracts"


def _setup_project(tmp_path: Path, fixture: str = "project_minimal") -> Path:
    """Copy a fixture project to tmp_path and return the project root."""
    src = FIXTURES / fixture
    dst = tmp_path / "project"
    shutil.copytree(src, dst)
    return dst


# ===================================================================
# Decision transitions
# ===================================================================

class TestDecisionTransitions:
    """Test that eval decisions produce the correct state transitions.

    These test the ``_apply_decision`` method directly, since the full
    start_loop path requires real Codex to modify iteration_log.json.
    """

    def _make_controller_at_eval(
        self, tmp_path: Path, decision: str,
    ) -> LoopController:
        """Create a controller with state positioned at eval completion."""
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        ctl.store.ensure_dirs()

        ctl.state = {
            "schema_version": 1,
            "loop_id": "test_loop",
            "status": "running",
            "tool": "codex",
            "current_round_index": 3,
            "current_phase_key": "eval",
            "current_iteration_id": "iter3",
            "phase_attempt": 1,
            "goal": {"source_path": "goal.md", "activated_at": "2026-01-01T00:00:00Z"},
            "objective": {"primary_metric": {"name": "PSNR", "direction": "maximize", "target": 32.0}},
            "best": {"iteration_id": "iter2", "round_index": 2, "primary_metric": 30.0, "updated_at": None},
            "patience": {"max_no_improve_rounds": 5, "min_primary_delta": 0.1, "consecutive_no_improve": 0},
            "budget": {"max_rounds": 20, "completed_rounds": 2, "gpu_count": 1,
                        "max_gpu_hours": 100, "used_gpu_hours": 5, "tracking_method": "wall_time_hours_x_gpu_count"},
            "llm_budget": {"max_calls": 200, "used_calls": 20, "max_cost_usd": 50,
                           "used_cost_usd": 5, "tracking_method": "runtime_invocation_count"},
            "accounts": {"selected_account_id": None, "by_account": {}},
            "last_decision": None,
            "halt_reason": None,
            "last_failure": None,
            "screening_policy": {"enabled": False},
        }

        # Write iteration_log with metrics for best-tracking.
        atomic_write_json(project / "iteration_log.json", {
            "project": "test",
            "iterations": [
                {"id": "iter3", "status": "completed", "decision": decision,
                 "lessons": ["x"], "metrics": {"PSNR": 30.5},
                 "hypothesis": "test"},
            ],
        })
        return ctl

    def test_next_round_keeps_running(self, tmp_path: Path) -> None:
        ctl = self._make_controller_at_eval(tmp_path, "NEXT_ROUND")
        ctl.state["last_decision"] = "NEXT_ROUND"  # Set by _run_one_phase
        validation = {"ok": True, "payload": {"decision": "NEXT_ROUND"}}
        ctl._apply_decision("NEXT_ROUND", 3, validation)

        assert ctl.state["status"] == "running"
        assert ctl.state["halt_reason"] is None
        assert ctl.state["current_phase_key"] == "plan"
        assert ctl.state["current_iteration_id"] is None
        assert ctl.state["budget"]["completed_rounds"] == 3

    def test_debug_keeps_running(self, tmp_path: Path) -> None:
        ctl = self._make_controller_at_eval(tmp_path, "DEBUG")
        ctl._apply_decision("DEBUG", 3, {"ok": True, "payload": {"decision": "DEBUG"}})

        assert ctl.state["status"] == "running"
        assert ctl.state["current_phase_key"] == "plan"

    def test_continue_stops_with_workflow_continue(self, tmp_path: Path) -> None:
        ctl = self._make_controller_at_eval(tmp_path, "CONTINUE")
        ctl._apply_decision("CONTINUE", 3, {"ok": True, "payload": {"decision": "CONTINUE"}})

        assert ctl.state["status"] == "stopped"
        assert ctl.state["halt_reason"] == "workflow_continue"

    def test_pivot_stops_with_workflow_pivot(self, tmp_path: Path) -> None:
        ctl = self._make_controller_at_eval(tmp_path, "PIVOT")
        ctl._apply_decision("PIVOT", 3, {"ok": True, "payload": {"decision": "PIVOT"}})

        assert ctl.state["status"] == "stopped"
        assert ctl.state["halt_reason"] == "workflow_pivot"

    def test_abort_stops_with_workflow_abort(self, tmp_path: Path) -> None:
        ctl = self._make_controller_at_eval(tmp_path, "ABORT")
        ctl._apply_decision("ABORT", 3, {"ok": True, "payload": {"decision": "ABORT"}})

        assert ctl.state["status"] == "stopped"
        assert ctl.state["halt_reason"] == "workflow_abort"


# ===================================================================
# Operator signals
# ===================================================================

class TestOperatorSignals:
    def test_stop_signal(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        # Create the stop signal file before starting.
        (project / ".auto_iterate_stop").touch()

        ctl = LoopController(project, dry_run=True)
        code = ctl.start_loop(
            goal_path=str(CONTRACTS / "goal.valid.md"),
        )
        state = load_json(project / ".auto_iterate" / "state.json")
        assert state["status"] == "stopped"
        assert state["halt_reason"] == "manual_stop"
        # Signal file should be consumed.
        assert not (project / ".auto_iterate_stop").exists()

    def test_pause_signal(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        (project / ".auto_iterate_pause").touch()

        ctl = LoopController(project, dry_run=True)
        code = ctl.start_loop(
            goal_path=str(CONTRACTS / "goal.valid.md"),
        )
        state = load_json(project / ".auto_iterate" / "state.json")
        assert state["status"] == "paused"
        assert state["halt_reason"] == "operator_pause"
        assert code == EXIT_RESUMABLE


# ===================================================================
# Budget exhaustion
# ===================================================================

class TestBudgetExhaustion:
    def test_max_rounds_reached(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        code = ctl.start_loop(
            goal_path=str(CONTRACTS / "goal.valid.md"),
            cli_overrides={"budget": {"max_rounds": 0}},
        )
        state = load_json(project / ".auto_iterate" / "state.json")
        assert state["halt_reason"] == "max_rounds_reached"

    def test_llm_budget_exhausted(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        # Set max_calls very low so budget check fires.
        code = ctl.start_loop(
            goal_path=str(CONTRACTS / "goal.valid.md"),
            cli_overrides={"llm_budget": {"max_calls": 1}},
        )
        state = load_json(project / ".auto_iterate" / "state.json")
        assert state["halt_reason"] == "llm_budget_exhausted"


# ===================================================================
# Goal validation
# ===================================================================

class TestGoalValidation:
    def test_invalid_goal_path(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        code = ctl.start_loop(goal_path="/nonexistent/goal.md")
        assert code == EXIT_GOAL_VALIDATION

    def test_goal_staged_override(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        # Override with a valid goal should succeed.
        ctl.store.ensure_dirs()
        code = ctl.override_goal(str(CONTRACTS / "goal.valid.md"))
        assert code == EXIT_OK
        assert (project / ".auto_iterate" / "goal.next.md").exists()

    def test_invalid_staged_goal_stops_before_round_start(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        ctl.store.ensure_dirs()
        ctl.goal_mgr.stage_next(CONTRACTS / "goal.invalid_metric_change.md")

        code = ctl.start_loop(goal_path=str(CONTRACTS / "goal.valid.md"))

        state = load_json(project / ".auto_iterate" / "state.json")
        events = [
            json.loads(line)
            for line in (project / ".auto_iterate" / "events.jsonl").read_text().splitlines()
            if line.strip()
        ]
        assert code == EXIT_MANUAL_ACTION
        assert state["status"] == "paused"
        assert state["halt_reason"] == "manual_action_required"
        assert state["current_round_index"] == 0
        assert any(e["event"] == "GOAL_ACTIVATION_FAILED" for e in events)
        assert not any(e["event"] == "ROUND_STARTED" for e in events)
        assert not any(e["event"] == "PHASE_STARTED" for e in events)

    def test_goal_activation_updates_all_goal_derived_fields(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        ctl.store.ensure_dirs()

        active_goal = tmp_path / "active_goal.md"
        active_goal.write_text((CONTRACTS / "goal.valid.md").read_text())
        staged_goal = tmp_path / "staged_goal.md"
        staged_goal.write_text(textwrap.dedent("""\
        # Auto-Iterate Goal

        ## Objective

        ### Primary Metric
        - **name**: PSNR
        - **direction**: maximize
        - **target**: 35.0

        ### Constraints
        - FPS >= 30

        ## Patience
        - **max_no_improve_rounds**: 2
        - **min_primary_delta**: 0.5

        ## Budget
        - **max_rounds**: 7
        - **max_gpu_hours**: 12.0

        ## Screening Policy
        - **enabled**: false
        - **threshold_pct**: 95
        - **default_steps**: 1234
        """))

        ctl.goal_mgr.snapshot_to(active_goal)
        ctl.goal_mgr.stage_next(staged_goal)
        ctl.state = {
            "loop_id": "loop1",
            "status": "running",
            "goal": {"source_path": str(active_goal), "activated_at": "2026-01-01T00:00:00Z"},
            "objective": {"primary_metric": {"name": "PSNR", "direction": "maximize", "target": 32.0}},
            "patience": {"max_no_improve_rounds": 5, "min_primary_delta": 0.1, "consecutive_no_improve": 1},
            "budget": {"max_rounds": 20, "completed_rounds": 3, "gpu_count": 1,
                       "max_gpu_hours": 100.0, "used_gpu_hours": 4.0},
            "screening_policy": {"enabled": True, "threshold_pct": 90, "default_steps": 5000},
        }

        assert ctl._activate_pending_goal() is True
        assert ctl.state["objective"]["primary_metric"]["target"] == 35.0
        assert ctl.state["patience"]["max_no_improve_rounds"] == 2
        assert ctl.state["patience"]["min_primary_delta"] == 0.5
        assert ctl.state["patience"]["consecutive_no_improve"] == 1
        assert ctl.state["budget"]["max_rounds"] == 7
        assert ctl.state["budget"]["max_gpu_hours"] == 12.0
        assert ctl.state["budget"]["completed_rounds"] == 3
        assert ctl.state["screening_policy"]["enabled"] is False
        assert ctl.state["screening_policy"]["default_steps"] == 1234


class TestRetryCeiling:
    def test_first_failure_still_allows_retry(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        ctl.store.ensure_dirs()
        ctl.policy = {"retry_policy": {"max_phase_attempts": 2}}
        ctl.state = {
            "loop_id": "loop1",
            "status": "running",
            "phase_attempt": 2,
            "halt_reason": None,
        }

        result = ctl._handle_phase_failure("code", 1)
        assert result is not None
        assert ctl.state["status"] == "running"
        assert ctl.state["halt_reason"] is None

    def test_second_failure_pauses(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        ctl = LoopController(project, dry_run=True)
        ctl.store.ensure_dirs()
        ctl.policy = {"retry_policy": {"max_phase_attempts": 2}}
        ctl.state = {
            "loop_id": "loop1",
            "status": "running",
            "phase_attempt": 3,
            "halt_reason": None,
        }

        result = ctl._handle_phase_failure("code", 1)
        assert result is None
        assert ctl.state["status"] == "paused"
        assert ctl.state["halt_reason"] == "manual_action_required"


# ===================================================================
# Status and tail
# ===================================================================

class TestStatusAndTail:
    def test_status_json(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        # Write a state file.
        state_data = load_json(CONTRACTS / "state.valid.json")
        auto_dir = project / ".auto_iterate"
        auto_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(auto_dir / "state.json", state_data)

        ctl = LoopController(project)
        result = ctl.status(as_json=True)
        assert isinstance(result, dict)
        assert result["loop_id"] == state_data["loop_id"]
        assert result["status"] == state_data["status"]
        required_keys = {
            "schema_version", "loop_id", "status", "halt_reason",
            "current_round_index", "current_phase_key",
            "current_iteration_id", "accounts", "objective",
            "best", "budget", "llm_budget",
            "last_decision", "last_failure",
        }
        assert required_keys.issubset(result.keys())

    def test_status_no_loop(self, tmp_path: Path) -> None:
        ctl = LoopController(tmp_path)
        result = ctl.status(as_json=True)
        assert "error" in result

    def test_tail_events(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        auto_dir = project / ".auto_iterate"
        auto_dir.mkdir(parents=True, exist_ok=True)
        el = EventLogger(auto_dir / "events.jsonl")
        el.emit("LOOP_STARTED", "loop1", "running")
        el.emit("ROUND_STARTED", "loop1", "running", round_index=1)

        ctl = LoopController(project)
        events = ctl.tail_events(lines=10)
        assert len(events) == 2


# ===================================================================
# CLI
# ===================================================================

class TestCLI:
    def test_cli_start_dry_run(self, tmp_path: Path) -> None:
        """Verify CLI entry point works."""
        from auto_iterate_ctl import main
        project = _setup_project(tmp_path)
        code = main([
            "--workspace-root", str(project),
            "start",
            "--goal", str(CONTRACTS / "goal.valid.md"),
            "--dry-run",
            "--max-rounds", "0",
        ])
        # Should exit cleanly (max_rounds=0 → immediate stop).
        assert code == EXIT_OK

    def test_cli_status_no_loop(self, tmp_path: Path) -> None:
        from auto_iterate_ctl import main
        code = main([
            "--workspace-root", str(tmp_path),
            "status", "--json",
        ])
        assert code == EXIT_OK

    def test_cli_no_command(self) -> None:
        from auto_iterate_ctl import main
        code = main([])
        assert code == EXIT_INVALID_ARGS
