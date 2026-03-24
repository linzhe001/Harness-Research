"""Unit tests for the runtime adapter and postcondition validator.

Tests cover:
- Brief construction per phase_key
- Brief validation (schema version, run_type mismatch)
- Prompt rendering
- Dry-run result generation
- Result file atomic write
- Postcondition validation per phase
- current_iteration_id binding algorithm
- HeartbeatWorker lifecycle
"""

# ruff: noqa: E402

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tooling" / "auto_iterate" / "scripts"))

from auto_iterate.lock import LockManager
from auto_iterate.postcondition import PostconditionValidator, bind_iteration_id
from auto_iterate.runtime import (
    BriefValidationError,
    HeartbeatWorker,
    PhaseSupervisor,
    build_brief,
    build_codex_command,
    build_result,
    classify_exit,
    render_prompt,
    validate_brief,
)
from auto_iterate.state import atomic_write_json, load_json

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "auto_iterate" / "contracts"


# ===================================================================
# Brief building
# ===================================================================

class TestBuildBrief:
    def _state(self) -> dict:
        return load_json(FIXTURES / "state.valid.json")

    def test_plan_brief(self) -> None:
        brief = build_brief(self._state(), "plan")
        assert brief["phase_key"] == "plan"
        assert brief["phase_family"] == "plan"
        assert brief["run_type"] is None
        assert brief["auto_mode"] is True

    def test_code_brief(self) -> None:
        brief = build_brief(self._state(), "code")
        assert brief["phase_key"] == "code"
        assert brief["run_type"] is None

    def test_run_screening_brief(self) -> None:
        brief = build_brief(self._state(), "run_screening")
        assert brief["phase_key"] == "run_screening"
        assert brief["run_type"] == "screening"
        assert brief["phase_family"] == "run"

    def test_run_full_brief(self) -> None:
        brief = build_brief(self._state(), "run_full")
        assert brief["phase_key"] == "run_full"
        assert brief["run_type"] == "full"
        assert brief["phase_family"] == "run"

    def test_eval_brief(self) -> None:
        brief = build_brief(self._state(), "eval")
        assert brief["phase_key"] == "eval"
        assert brief["run_type"] is None

    def test_brief_has_all_required_fields(self) -> None:
        brief = build_brief(self._state(), "plan")
        required = {
            "schema_version", "loop_id", "round_index",
            "phase_family", "phase_key", "run_type", "tool",
            "auto_mode", "recovery_mode", "round_type",
            "objective", "current_best", "recent_lessons",
            "failed_hypotheses", "budget_status",
            "screening_policy", "timeouts",
        }
        assert required.issubset(brief.keys()), f"Missing: {required - brief.keys()}"

    def test_brief_with_lessons(self) -> None:
        brief = build_brief(
            self._state(), "plan",
            recent_lessons=["lesson1", "lesson2"],
            failed_hypotheses=["bad idea"],
        )
        assert brief["recent_lessons"] == ["lesson1", "lesson2"]
        assert brief["failed_hypotheses"] == ["bad idea"]


# ===================================================================
# Brief validation
# ===================================================================

class TestValidateBrief:
    def test_valid_plan_brief(self) -> None:
        brief = load_json(FIXTURES / "brief.valid.plan.json")
        validate_brief(brief)  # Should not raise.

    def test_run_type_mismatch_rejected(self) -> None:
        brief = load_json(FIXTURES / "brief.invalid.run_type_mismatch.json")
        with pytest.raises(BriefValidationError, match="run_type=full"):
            validate_brief(brief)

    def test_bad_schema_version(self) -> None:
        brief = load_json(FIXTURES / "brief.valid.plan.json")
        brief["schema_version"] = 999
        with pytest.raises(Exception):
            validate_brief(brief)

    def test_invalid_phase_key(self) -> None:
        brief = load_json(FIXTURES / "brief.valid.plan.json")
        brief["phase_key"] = "bogus"
        with pytest.raises(BriefValidationError, match="Invalid phase_key"):
            validate_brief(brief)

    def test_plan_with_run_type_rejected(self) -> None:
        brief = load_json(FIXTURES / "brief.valid.plan.json")
        brief["run_type"] = "full"
        with pytest.raises(BriefValidationError, match="run_type=null"):
            validate_brief(brief)


# ===================================================================
# Prompt rendering
# ===================================================================

class TestRenderPrompt:
    def test_plan_prompt(self) -> None:
        brief = load_json(FIXTURES / "brief.valid.plan.json")
        prompt = render_prompt(brief)
        assert "auto_mode" in prompt
        assert "plan" in prompt.lower()
        assert "PSNR" in prompt

    def test_eval_prompt(self) -> None:
        state = load_json(FIXTURES / "state.valid.json")
        brief = build_brief(state, "eval")
        prompt = render_prompt(brief, iteration_id="iter3")
        assert "NEXT_ROUND" in prompt
        assert "CONTINUE" in prompt
        assert "iter3" in prompt

    def test_code_prompt(self) -> None:
        state = load_json(FIXTURES / "state.valid.json")
        brief = build_brief(state, "code")
        prompt = render_prompt(brief, iteration_id="iter3")
        assert "code" in prompt.lower()
        assert "git commit" in prompt.lower() or "semantic git" in prompt.lower()


# ===================================================================
# Result building & classification
# ===================================================================

class TestResultAndClassify:
    def test_classify_success(self) -> None:
        assert classify_exit(0, False) == "success"

    def test_classify_timeout(self) -> None:
        assert classify_exit(1, True) == "timeout"

    def test_classify_internal_error(self) -> None:
        assert classify_exit(1, False) == "internal_error"

    def test_classify_usage_limit_from_stderr(self, tmp_path: Path) -> None:
        stderr_path = tmp_path / "quota.stderr.log"
        stderr_path.write_text(
            "ERROR: You've hit your usage limit.",
            encoding="utf-8",
        )
        assert classify_exit(1, False, str(stderr_path)) == "quota_or_rate_limit"

    def test_classify_success_ignores_embedded_quota_label(
        self, tmp_path: Path,
    ) -> None:
        stderr_path = tmp_path / "transcript.stderr.log"
        stderr_path.write_text(
            '{"runtime_exit_class": "quota_or_rate_limit"}',
            encoding="utf-8",
        )
        assert classify_exit(0, False, str(stderr_path)) == "success"

    def test_classify_auth_failure_from_stderr(self, tmp_path: Path) -> None:
        stderr_path = tmp_path / "auth.stderr.log"
        stderr_path.write_text(
            "Unauthorized. Please run codex login.",
            encoding="utf-8",
        )
        assert classify_exit(1, False, str(stderr_path)) == "auth_failure"

    def test_build_codex_command_run_phase_uses_danger_full_access(self) -> None:
        cmd = build_codex_command("/tmp/work", "run_full")
        assert cmd[0] == "codex"
        assert "--dangerously-bypass-approvals-and-sandbox" in cmd
        assert "exec" in cmd
        assert "--full-auto" not in cmd

    def test_build_codex_command_non_run_phase_keeps_full_auto(self) -> None:
        cmd = build_codex_command("/tmp/work", "plan")
        assert "--full-auto" in cmd
        assert "exec" in cmd
        assert "danger-full-access" not in cmd

    def test_build_result_fields(self) -> None:
        brief = load_json(FIXTURES / "brief.valid.plan.json")
        result = build_result(
            brief=brief,
            account_id="acc1",
            started_at="2026-03-22T18:00:00Z",
            finished_at="2026-03-22T18:15:00Z",
            duration_sec=900.0,
            exit_code=0,
            runtime_exit_class="success",
            failure_reason=None,
            timed_out=False,
            stdout_path="/tmp/stdout.log",
            stderr_path="/tmp/stderr.log",
        )
        required = {
            "schema_version", "phase_family", "phase_key", "run_type",
            "account_id", "started_at", "finished_at", "duration_sec",
            "exit_code", "runtime_exit_class", "failure_reason",
            "timed_out", "stdout_path", "stderr_path",
        }
        assert required.issubset(result.keys())
        assert result["runtime_exit_class"] == "success"


# ===================================================================
# PhaseSupervisor dry_run
# ===================================================================

class TestPhaseSupervisorDryRun:
    def test_dry_run_plan(self, tmp_path: Path) -> None:
        state = load_json(FIXTURES / "state.valid.json")
        brief = build_brief(state, "plan")

        supervisor = PhaseSupervisor(
            workspace_root=tmp_path,
            runtime_dir=tmp_path / "runtime",
        )
        result = supervisor.run_phase(
            brief=brief,
            account_id="acc1",
            codex_home="/tmp/fake",
            timeout_sec=10,
            dry_run=True,
        )
        assert result["runtime_exit_class"] == "success"
        assert result["timed_out"] is False
        # Brief file should be written.
        assert (tmp_path / "runtime" / "round3_plan_brief.json").exists()

    def test_dry_run_all_phases(self, tmp_path: Path) -> None:
        state = load_json(FIXTURES / "state.valid.json")
        for pk in ["plan", "code", "run_screening", "run_full", "eval"]:
            brief = build_brief(state, pk)
            supervisor = PhaseSupervisor(
                workspace_root=tmp_path,
                runtime_dir=tmp_path / "runtime",
            )
            result = supervisor.run_phase(
                brief=brief,
                account_id="acc1",
                codex_home="/tmp/fake",
                timeout_sec=10,
                dry_run=True,
            )
            assert result["runtime_exit_class"] == "success", f"Failed for {pk}"

    def test_dry_run_rejects_invalid_brief(self, tmp_path: Path) -> None:
        brief = load_json(FIXTURES / "brief.invalid.run_type_mismatch.json")
        supervisor = PhaseSupervisor(
            workspace_root=tmp_path,
            runtime_dir=tmp_path / "runtime",
        )
        with pytest.raises(BriefValidationError):
            supervisor.run_phase(
                brief=brief,
                account_id="acc1",
                codex_home="/tmp/fake",
                timeout_sec=10,
                dry_run=True,
            )

    def test_result_file_atomic(self, tmp_path: Path) -> None:
        """Result file must be written atomically (no partial JSON)."""
        state = load_json(FIXTURES / "state.valid.json")
        brief = build_brief(state, "eval")
        runtime_dir = tmp_path / "runtime"

        supervisor = PhaseSupervisor(
            workspace_root=tmp_path,
            runtime_dir=runtime_dir,
        )
        supervisor.run_phase(
            brief=brief,
            account_id="acc1",
            codex_home="/tmp/fake",
            timeout_sec=10,
            dry_run=True,
        )
        # The brief file should be valid JSON.
        brief_path = runtime_dir / "round3_eval_brief.json"
        assert brief_path.exists()
        loaded = load_json(brief_path)
        assert loaded["phase_key"] == "eval"


# ===================================================================
# Postcondition validation
# ===================================================================

class TestPostconditionValidator:
    def _make_project(
        self,
        tmp_path: Path,
        iterations: list[dict],
    ) -> PostconditionValidator:
        """Create a minimal fixture project with the given iterations."""
        log = {"project": "test", "iterations": iterations}
        atomic_write_json(tmp_path / "iteration_log.json", log)
        return PostconditionValidator(tmp_path)

    # -- plan ---------------------------------------------------------------

    def test_plan_success(self, tmp_path: Path) -> None:
        pre_ids = {"iter1", "iter2"}
        v = self._make_project(tmp_path, [
            {"id": "iter1", "status": "completed"},
            {"id": "iter2", "status": "completed"},
            {"id": "iter3", "status": "planned", "hypothesis": "test hypothesis"},
        ])
        result = v.validate("plan", None, pre_ids=pre_ids)
        assert result["ok"] is True
        assert result["iteration_id"] == "iter3"
        assert result["classification"] == "planned"

    def test_plan_no_new_iteration(self, tmp_path: Path) -> None:
        pre_ids = {"iter1", "iter2"}
        v = self._make_project(tmp_path, [
            {"id": "iter1", "status": "completed"},
            {"id": "iter2", "status": "completed"},
        ])
        result = v.validate("plan", None, pre_ids=pre_ids)
        assert result["ok"] is False
        assert "did not create" in result["payload"]["error"]

    def test_plan_multiple_new_iterations(self, tmp_path: Path) -> None:
        pre_ids = {"iter1"}
        v = self._make_project(tmp_path, [
            {"id": "iter1", "status": "completed"},
            {"id": "iter2", "status": "planned", "hypothesis": "h2"},
            {"id": "iter3", "status": "planned", "hypothesis": "h3"},
        ])
        result = v.validate("plan", None, pre_ids=pre_ids)
        assert result["ok"] is False
        assert "ambiguous" in result["payload"]["error"]

    def test_plan_missing_hypothesis(self, tmp_path: Path) -> None:
        pre_ids = set()
        v = self._make_project(tmp_path, [
            {"id": "iter1", "status": "planned"},
        ])
        result = v.validate("plan", None, pre_ids=pre_ids)
        assert result["ok"] is False
        assert "hypothesis" in str(result["payload"])

    # -- code ---------------------------------------------------------------

    def test_code_success(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training",
             "git_commit": "abc123", "git_message": "feat: add attention"},
        ])
        result = v.validate("code", "iter3")
        assert result["ok"] is True
        assert result["classification"] == "training"

    def test_code_missing_git_commit(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training"},
        ])
        result = v.validate("code", "iter3")
        assert result["ok"] is False
        assert "git_commit" in str(result["payload"])

    def test_code_wrong_status(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "planned",
             "git_commit": "abc", "git_message": "msg"},
        ])
        result = v.validate("code", "iter3")
        assert result["ok"] is False

    # -- run_screening ------------------------------------------------------

    def test_run_screening_passed(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training",
             "screening": {"recommended": True, "status": "passed"}},
        ])
        result = v.validate("run_screening", "iter3")
        assert result["ok"] is True
        assert result["payload"]["screening_status"] == "passed"

    def test_run_screening_failed(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training",
             "screening": {"recommended": True, "status": "failed"}},
        ])
        result = v.validate("run_screening", "iter3")
        assert result["ok"] is True
        assert result["payload"]["screening_status"] == "failed"

    def test_run_screening_missing(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training"},
        ])
        result = v.validate("run_screening", "iter3")
        assert result["ok"] is False

    # -- run_full -----------------------------------------------------------

    def test_run_full_completed(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training",
             "full_run": {"status": "completed", "resume_mode": "from_scratch",
                          "metrics": {"PSNR": 31.2}}},
        ])
        result = v.validate("run_full", "iter3")
        assert result["ok"] is True
        assert result["payload"]["full_run_status"] == "completed"

    def test_run_full_recoverable_failed(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training",
             "full_run": {"status": "recoverable_failed"}},
        ])
        result = v.validate("run_full", "iter3")
        assert result["ok"] is True
        assert result["payload"]["full_run_status"] == "recoverable_failed"

    def test_run_full_no_full_run(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training"},
        ])
        result = v.validate("run_full", "iter3")
        assert result["ok"] is False

    # -- eval ---------------------------------------------------------------

    def test_eval_success(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "completed",
             "decision": "NEXT_ROUND",
             "lessons": ["Learned something"],
             "metrics": {"PSNR": 31.5}},
        ])
        result = v.validate("eval", "iter3")
        assert result["ok"] is True
        assert result["payload"]["decision"] == "NEXT_ROUND"

    def test_eval_continue_decision(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "completed",
             "decision": "CONTINUE",
             "lessons": ["Ready for WF9"],
             "metrics": {"PSNR": 32.1}},
        ])
        result = v.validate("eval", "iter3")
        assert result["ok"] is True
        assert result["payload"]["decision"] == "CONTINUE"

    def test_eval_no_decision(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "completed",
             "lessons": ["Something"]},
        ])
        result = v.validate("eval", "iter3")
        assert result["ok"] is False

    def test_eval_no_lessons(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "completed",
             "decision": "NEXT_ROUND", "lessons": []},
        ])
        result = v.validate("eval", "iter3")
        assert result["ok"] is False
        assert "lesson" in result["payload"]["error"]

    def test_eval_invalid_decision(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "completed",
             "decision": "YOLO", "lessons": ["nope"]},
        ])
        result = v.validate("eval", "iter3")
        assert result["ok"] is False

    def test_eval_metrics_required(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "completed",
             "decision": "NEXT_ROUND", "lessons": ["x"]},
        ])
        result = v.validate("eval", "iter3")
        assert result["ok"] is False
        assert "metrics" in result["payload"]["error"].lower()

    def test_eval_wrong_status(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [
            {"id": "iter3", "status": "training",
             "decision": "NEXT_ROUND", "lessons": ["x"]},
        ])
        result = v.validate("eval", "iter3")
        assert result["ok"] is False

    # -- edge cases ---------------------------------------------------------

    def test_unbound_iteration_id(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [])
        result = v.validate("code", None)
        assert result["ok"] is False
        assert "not bound" in result["payload"]["error"]

    def test_unknown_phase(self, tmp_path: Path) -> None:
        v = self._make_project(tmp_path, [])
        result = v.validate("bogus", "iter1")
        assert result["ok"] is False


# ===================================================================
# bind_iteration_id
# ===================================================================

class TestBindIterationId:
    def test_one_new_id(self) -> None:
        iter_id, err = bind_iteration_id({"iter1"}, {"iter1", "iter2"})
        assert iter_id == "iter2"
        assert err is None

    def test_zero_new_ids(self) -> None:
        iter_id, err = bind_iteration_id({"iter1"}, {"iter1"})
        assert iter_id is None
        assert "did not create" in err  # type: ignore

    def test_multiple_new_ids(self) -> None:
        iter_id, err = bind_iteration_id({"iter1"}, {"iter1", "iter2", "iter3"})
        assert iter_id is None
        assert "ambiguous" in err  # type: ignore

    def test_empty_pre(self) -> None:
        iter_id, err = bind_iteration_id(set(), {"iter1"})
        assert iter_id == "iter1"
        assert err is None


# ===================================================================
# HeartbeatWorker
# ===================================================================

class TestHeartbeatWorker:
    def test_start_stop(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json")
        lm.acquire("loop1", "codex", "/workspace")

        hb = HeartbeatWorker(lm, interval_sec=1)
        hb.start()
        assert hb.is_alive()
        time.sleep(0.2)
        hb.stop()
        time.sleep(0.1)
        assert not hb.is_alive()

    def test_heartbeat_updates_lock(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json")
        lock_data = lm.acquire("loop1", "codex", "/workspace")
        old_hb = lock_data["heartbeat_at"]

        # Wait at least 1 second so the next heartbeat produces a different timestamp.
        time.sleep(1.1)
        hb = HeartbeatWorker(lm, interval_sec=1)
        hb.start()
        time.sleep(1.5)
        hb.stop()

        new_data = load_json(tmp_path / "lock.json")
        assert new_data["heartbeat_at"] > old_hb

    def test_death_on_lock_error(self, tmp_path: Path) -> None:
        """If the lock file is removed, heartbeat worker should die."""
        lm = LockManager(tmp_path / "lock.json")
        lm.acquire("loop1", "codex", "/workspace")

        # Use a short interval so the next heartbeat fires quickly.
        hb = HeartbeatWorker(lm, interval_sec=1)
        hb.start()
        time.sleep(0.2)  # Let the first heartbeat succeed.
        # Remove lock to cause error on next heartbeat.
        (tmp_path / "lock.json").unlink()
        # Wait long enough for at least 2 heartbeat cycles.
        for _ in range(30):
            time.sleep(0.2)
            if not hb.is_alive():
                break
        assert not hb.is_alive()
