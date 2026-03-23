"""Unit tests for auto-iterate V7 IO primitives.

Tests cover:
- Atomic write safety
- Schema version validation
- Lock lifecycle (acquire / release / stale / conflict)
- Event append and rotation
- State round-trip against fixtures
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Make the scripts/ package importable.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tooling" / "auto_iterate" / "scripts"))

from auto_iterate.state import (
    SchemaVersionError,
    StateLoadError,
    StateStore,
    atomic_write_json,
    load_json,
    validate_schema_version,
)
from auto_iterate.lock import LockConflictError, LockManager
from auto_iterate.events import EventLogger, iso_now

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "auto_iterate" / "contracts"


# ===================================================================
# Atomic write
# ===================================================================

class TestAtomicWrite:
    def test_basic_round_trip(self, tmp_path: Path) -> None:
        target = tmp_path / "data.json"
        payload = {"key": "value", "nested": {"a": 1}}
        atomic_write_json(target, payload)
        assert target.exists()
        assert load_json(target) == payload

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested" / "file.json"
        atomic_write_json(target, {"ok": True})
        assert load_json(target) == {"ok": True}

    def test_no_partial_file_on_error(self, tmp_path: Path) -> None:
        """If the serialization somehow fails, no partial file is left."""
        target = tmp_path / "fail.json"

        class BadObj:
            def __repr__(self) -> str:
                return "<bad>"

        with pytest.raises(TypeError):
            atomic_write_json(target, BadObj())
        assert not target.exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "data.json"
        atomic_write_json(target, {"v": 1})
        atomic_write_json(target, {"v": 2})
        assert load_json(target) == {"v": 2}

    def test_no_leftover_temp_files(self, tmp_path: Path) -> None:
        target = tmp_path / "data.json"
        atomic_write_json(target, {"ok": True})
        files = list(tmp_path.iterdir())
        assert files == [target], f"Unexpected files: {files}"


# ===================================================================
# Schema version validation
# ===================================================================

class TestSchemaVersion:
    def test_valid(self) -> None:
        validate_schema_version({"schema_version": 1})

    def test_wrong_version(self) -> None:
        with pytest.raises(SchemaVersionError, match="999"):
            validate_schema_version({"schema_version": 999})

    def test_missing_version(self) -> None:
        with pytest.raises(SchemaVersionError):
            validate_schema_version({})

    def test_fixture_valid_state(self) -> None:
        data = load_json(FIXTURES / "state.valid.json")
        validate_schema_version(data, label="state.valid.json")

    def test_fixture_invalid_state(self) -> None:
        data = load_json(FIXTURES / "state.invalid.schema_version.json")
        with pytest.raises(SchemaVersionError, match="999"):
            validate_schema_version(data)


# ===================================================================
# StateStore
# ===================================================================

class TestStateStore:
    def test_state_round_trip(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path / ".auto_iterate")
        store.ensure_dirs()

        data = load_json(FIXTURES / "state.valid.json")
        store.save_state(data)
        loaded = store.load_state()
        assert loaded == data

    def test_state_rejects_bad_version(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path / ".auto_iterate")
        store.ensure_dirs()

        data = load_json(FIXTURES / "state.invalid.schema_version.json")
        store.save_state(data)
        with pytest.raises(SchemaVersionError):
            store.load_state()

    def test_lock_round_trip(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path / ".auto_iterate")
        store.ensure_dirs()

        data = load_json(FIXTURES / "lock.valid.json")
        store.save_lock(data)
        loaded = store.load_lock()
        assert loaded == data

    def test_ensure_dirs(self, tmp_path: Path) -> None:
        root = tmp_path / ".auto_iterate"
        store = StateStore(root)
        store.ensure_dirs()
        assert root.is_dir()
        assert (root / "runtime").is_dir()
        assert (root / "logs").is_dir()

    def test_load_missing_state(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path / ".auto_iterate")
        with pytest.raises(StateLoadError, match="not found"):
            store.load_state()

    def test_fixture_state_has_required_fields(self) -> None:
        """Verify the valid state fixture contains all required top-level fields."""
        data = load_json(FIXTURES / "state.valid.json")
        required = {
            "schema_version", "loop_id", "status", "tool",
            "current_round_index", "current_phase_key",
            "current_iteration_id", "phase_attempt",
            "goal", "objective", "best", "patience",
            "budget", "llm_budget", "accounts",
            "last_decision", "halt_reason", "last_failure",
        }
        assert required.issubset(data.keys()), f"Missing: {required - data.keys()}"

    def test_fixture_budget_sub_fields(self) -> None:
        data = load_json(FIXTURES / "state.valid.json")
        budget = data["budget"]
        for field in ["max_rounds", "completed_rounds", "gpu_count",
                       "max_gpu_hours", "used_gpu_hours", "tracking_method"]:
            assert field in budget, f"budget.{field} missing"

        llm = data["llm_budget"]
        for field in ["max_calls", "used_calls", "max_cost_usd",
                       "used_cost_usd", "tracking_method"]:
            assert field in llm, f"llm_budget.{field} missing"

    def test_fixture_accounts_consistency(self) -> None:
        """llm_budget.used_calls == sum(by_account[*].used_calls)."""
        data = load_json(FIXTURES / "state.valid.json")
        total = sum(
            acc["used_calls"]
            for acc in data["accounts"]["by_account"].values()
        )
        assert data["llm_budget"]["used_calls"] == total


# ===================================================================
# LockManager
# ===================================================================

class TestLockManager:
    def test_acquire_and_release(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json")
        lock_data = lm.acquire("loop1", "codex", "/workspace")
        assert lock_data["loop_id"] == "loop1"
        assert lock_data["pid"] == os.getpid()
        assert (tmp_path / "lock.json").exists()

        lm.release()
        assert not (tmp_path / "lock.json").exists()

    def test_conflict_when_live(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json")
        lm.acquire("loop1", "codex", "/workspace")
        # Same process — lock is live.
        assert lm.check_conflict() == "live"
        with pytest.raises(LockConflictError):
            lm.acquire("loop2", "codex", "/workspace")

    def test_stale_detection(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json", stale_threshold_sec=0)
        lm.acquire("loop1", "codex", "/workspace")
        # With threshold=0, the lock is immediately stale.
        time.sleep(0.05)
        assert lm.is_stale()

    def test_clear_stale(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json", stale_threshold_sec=0)
        lm.acquire("loop1", "codex", "/workspace")
        time.sleep(0.05)
        cleared = lm.clear_stale()
        assert cleared is not None
        assert cleared["loop_id"] == "loop1"
        assert not (tmp_path / "lock.json").exists()

    def test_no_conflict_when_absent(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json")
        assert lm.check_conflict() == "none"

    def test_heartbeat_update(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json")
        lock_data = lm.acquire("loop1", "codex", "/workspace")
        old_hb = lock_data["heartbeat_at"]
        time.sleep(0.05)
        lm.update_heartbeat()
        updated = load_json(tmp_path / "lock.json")
        assert updated["heartbeat_at"] >= old_hb

    def test_stale_lock_with_dead_pid(self, tmp_path: Path) -> None:
        """A lock whose pid is not alive should be detected as stale."""
        lock_data = {
            "schema_version": 1,
            "loop_id": "loop_dead",
            "pid": 99999999,  # Almost certainly not a real PID
            "host": os.uname().nodename,
            "started_at": iso_now(),
            "heartbeat_at": iso_now(),
            "tool": "codex",
            "workspace_root": "/workspace",
        }
        lock_path = tmp_path / "lock.json"
        atomic_write_json(lock_path, lock_data)

        lm = LockManager(lock_path, stale_threshold_sec=9999)
        assert lm.check_conflict() == "stale"

    def test_acquire_after_stale_clear(self, tmp_path: Path) -> None:
        lm = LockManager(tmp_path / "lock.json", stale_threshold_sec=0)
        lm.acquire("loop1", "codex", "/workspace")
        time.sleep(0.05)
        lm.clear_stale()
        # Should be able to acquire again.
        lock_data = lm.acquire("loop2", "codex", "/workspace")
        assert lock_data["loop_id"] == "loop2"


# ===================================================================
# EventLogger
# ===================================================================

class TestEventLogger:
    def test_emit_and_tail(self, tmp_path: Path) -> None:
        el = EventLogger(tmp_path / "events.jsonl")
        el.emit("LOOP_STARTED", "loop1", "running", payload={"tool": "codex"})
        el.emit("ROUND_STARTED", "loop1", "running", round_index=1)

        events = el.tail(lines=10)
        assert len(events) == 2
        assert events[0]["event"] == "LOOP_STARTED"
        assert events[1]["round_index"] == 1

    def test_tail_jsonl_parseable(self, tmp_path: Path) -> None:
        el = EventLogger(tmp_path / "events.jsonl")
        for i in range(5):
            el.emit("PHASE_STARTED", "loop1", "running", round_index=1, phase_key="plan")

        events = el.tail(lines=3, jsonl=True)
        assert len(events) == 3
        for e in events:
            assert isinstance(e, dict)
            assert e["event"] == "PHASE_STARTED"

    def test_emit_creates_parent_dirs(self, tmp_path: Path) -> None:
        el = EventLogger(tmp_path / "deep" / "events.jsonl")
        el.emit("LOOP_STARTED", "loop1", "running")
        assert (tmp_path / "deep" / "events.jsonl").exists()

    def test_rotation(self, tmp_path: Path) -> None:
        el = EventLogger(tmp_path / "events.jsonl")
        # Write enough data to exceed threshold.
        for i in range(50):
            el.emit("PHASE_STARTED", "loop1", "running", round_index=i)

        size = el.size_bytes()
        # Set a very low threshold so rotation happens.
        archive = el.rotate_if_needed(max_bytes=10)
        assert archive is not None
        assert Path(archive).exists()
        # The new events.jsonl should be empty (or very small).
        assert el.size_bytes() < size

    def test_no_rotation_when_small(self, tmp_path: Path) -> None:
        el = EventLogger(tmp_path / "events.jsonl")
        el.emit("LOOP_STARTED", "loop1", "running")
        assert el.rotate_if_needed(max_bytes=1_000_000) is None

    def test_rotation_on_missing_file(self, tmp_path: Path) -> None:
        el = EventLogger(tmp_path / "events.jsonl")
        assert el.rotate_if_needed(max_bytes=10) is None

    def test_count(self, tmp_path: Path) -> None:
        el = EventLogger(tmp_path / "events.jsonl")
        assert el.count() == 0
        el.emit("LOOP_STARTED", "loop1", "running")
        el.emit("ROUND_STARTED", "loop1", "running", round_index=1)
        assert el.count() == 2

    def test_event_fields_match_contract(self, tmp_path: Path) -> None:
        """Every emitted event must have the frozen fields: v, ts, event, loop_id, status."""
        el = EventLogger(tmp_path / "events.jsonl")
        el.emit(
            "PHASE_COMPLETED", "loop1", "running",
            round_index=2, phase_key="plan",
            payload={"current_iteration_id": "iter2"},
        )
        events = el.tail(lines=1)
        e = events[0]
        assert e["v"] == 1
        assert "ts" in e
        assert e["event"] == "PHASE_COMPLETED"
        assert e["loop_id"] == "loop1"
        assert e["status"] == "running"
        assert e["round_index"] == 2
        assert e["phase_key"] == "plan"
        assert e["payload"]["current_iteration_id"] == "iter2"

    def test_fixture_events_parseable(self) -> None:
        """The sample events fixture must be valid JSONL."""
        fixture = FIXTURES / "events.sample.jsonl"
        with open(fixture) as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) >= 10
        for line in lines:
            obj = json.loads(line)
            assert "v" in obj
            assert "event" in obj
            assert "loop_id" in obj


# ===================================================================
# Fixture integrity checks
# ===================================================================

class TestFixtureIntegrity:
    def test_brief_valid_plan(self) -> None:
        data = load_json(FIXTURES / "brief.valid.plan.json")
        validate_schema_version(data, label="brief")
        assert data["phase_key"] == "plan"
        assert data["run_type"] is None
        assert data["auto_mode"] is True
        required = {
            "schema_version", "loop_id", "round_index",
            "phase_family", "phase_key", "run_type", "tool",
            "auto_mode", "recovery_mode", "round_type",
            "objective", "current_best", "recent_lessons",
            "failed_hypotheses", "budget_status",
            "screening_policy", "timeouts",
        }
        assert required.issubset(data.keys())

    def test_brief_invalid_run_type_mismatch(self) -> None:
        data = load_json(FIXTURES / "brief.invalid.run_type_mismatch.json")
        # phase_key says run_full but run_type says screening — contradiction.
        assert data["phase_key"] == "run_full"
        assert data["run_type"] == "screening"

    def test_result_valid(self) -> None:
        data = load_json(FIXTURES / "result.valid.success.json")
        validate_schema_version(data, label="result")
        assert data["runtime_exit_class"] == "success"
        assert data["timed_out"] is False
        required = {
            "schema_version", "phase_family", "phase_key", "run_type",
            "account_id", "started_at", "finished_at", "duration_sec",
            "exit_code", "runtime_exit_class", "failure_reason",
            "timed_out", "stdout_path", "stderr_path",
        }
        assert required.issubset(data.keys())

    def test_lock_valid(self) -> None:
        data = load_json(FIXTURES / "lock.valid.json")
        validate_schema_version(data, label="lock")
        required = {
            "schema_version", "loop_id", "pid", "host",
            "started_at", "heartbeat_at", "tool", "workspace_root",
        }
        assert required.issubset(data.keys())
