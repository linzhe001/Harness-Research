"""Unit tests for goal parser, policy config, and account registry.

Tests cover:
- Goal parsing from valid/invalid markdown fixtures
- Metric identity change detection
- Staged goal activation
- Policy config loading and merge precedence
- Account selection, cooldown, and auth failure
"""

from __future__ import annotations

import json
import sys
import time
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tooling" / "auto_iterate" / "scripts"))

from auto_iterate.goal import (
    GoalManager,
    GoalMetricIdentityError,
    GoalParseError,
    check_metric_identity,
    parse,
    validate,
)
from auto_iterate.policy import DEFAULT_POLICY, PolicyConfig
from auto_iterate.accounts import AccountRegistry, NoAccountAvailableError
from auto_iterate.state import load_json

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "auto_iterate" / "contracts"


# ===================================================================
# Goal Parser
# ===================================================================

class TestGoalParse:
    def test_parse_valid_goal(self) -> None:
        result = parse(FIXTURES / "goal.valid.md")
        pm = result["objective"]["primary_metric"]
        assert pm["name"] == "PSNR"
        assert pm["direction"] == "maximize"
        assert pm["target"] == 32.0

    def test_parse_constraints(self) -> None:
        result = parse(FIXTURES / "goal.valid.md")
        constraints = result["objective"]["constraints"]
        assert len(constraints) >= 2
        assert any("FPS" in c for c in constraints)

    def test_parse_patience(self) -> None:
        result = parse(FIXTURES / "goal.valid.md")
        assert result["patience"]["max_no_improve_rounds"] == 5
        assert result["patience"]["min_primary_delta"] == 0.1

    def test_parse_budget(self) -> None:
        result = parse(FIXTURES / "goal.valid.md")
        assert result["budget"]["max_rounds"] == 20
        assert result["budget"]["max_gpu_hours"] == 100.0

    def test_parse_screening_policy(self) -> None:
        result = parse(FIXTURES / "goal.valid.md")
        sp = result["screening_policy"]
        assert sp["enabled"] is True
        assert sp["threshold_pct"] == 90
        assert sp["default_steps"] == 5000

    def test_parse_hypotheses(self) -> None:
        result = parse(FIXTURES / "goal.valid.md")
        assert len(result["initial_hypotheses"]) >= 3

    def test_parse_forbidden(self) -> None:
        result = parse(FIXTURES / "goal.valid.md")
        assert len(result["forbidden_directions"]) >= 1

    def test_parse_invalid_metric_change_file(self) -> None:
        result = parse(FIXTURES / "goal.invalid_metric_change.md")
        pm = result["objective"]["primary_metric"]
        assert pm["name"] == "SSIM"
        assert pm["direction"] == "maximize"

    def test_parse_missing_file(self) -> None:
        with pytest.raises(GoalParseError, match="not found"):
            parse("/nonexistent/goal.md")

    def test_parse_yaml_front_matter(self, tmp_path: Path) -> None:
        pytest.importorskip("yaml")
        goal_path = tmp_path / "goal.md"
        goal_path.write_text(textwrap.dedent("""\
        ---
        objective:
          primary_metric:
            name: PSNR
            direction: maximize
            target: 33.0
          constraints:
            - FPS >= 30
        patience:
          max_no_improve_rounds: 4
          min_primary_delta: 0.2
        budget:
          max_rounds: 10
          max_gpu_hours: 20.0
        screening_policy:
          enabled: true
          threshold_pct: 90
          default_steps: 4000
        initial_hypotheses:
          - Try a stronger encoder
        forbidden_directions:
          - Increase latency above 2x baseline
        ---
        """))

        parsed = parse(goal_path)
        assert parsed["objective"]["primary_metric"]["target"] == 33.0
        assert parsed["budget"]["max_rounds"] == 10
        assert parsed["screening_policy"]["default_steps"] == 4000


class TestGoalValidation:
    def test_valid_goal(self) -> None:
        parsed = parse(FIXTURES / "goal.valid.md")
        errors = validate(parsed)
        assert errors == []

    def test_missing_metric_name(self) -> None:
        parsed = parse(FIXTURES / "goal.valid.md")
        del parsed["objective"]["primary_metric"]["name"]
        errors = validate(parsed)
        assert any("name" in e for e in errors)

    def test_missing_max_rounds(self) -> None:
        parsed = parse(FIXTURES / "goal.valid.md")
        del parsed["budget"]["max_rounds"]
        errors = validate(parsed)
        assert any("max_rounds" in e for e in errors)

    def test_invalid_direction(self) -> None:
        parsed = parse(FIXTURES / "goal.valid.md")
        parsed["objective"]["primary_metric"]["direction"] = "bigger"
        errors = validate(parsed)
        assert any("direction" in e for e in errors)

    def test_missing_screening_enabled(self) -> None:
        parsed = parse(FIXTURES / "goal.valid.md")
        del parsed["screening_policy"]["enabled"]
        errors = validate(parsed)
        assert any("screening_policy.enabled" in e for e in errors)

    def test_missing_min_primary_delta(self) -> None:
        parsed = parse(FIXTURES / "goal.valid.md")
        del parsed["patience"]["min_primary_delta"]
        errors = validate(parsed)
        assert any("patience.min_primary_delta" in e for e in errors)


class TestMetricIdentity:
    def test_same_metric_passes(self) -> None:
        parsed = parse(FIXTURES / "goal.valid.md")
        state = load_json(FIXTURES / "state.valid.json")
        errors = check_metric_identity(parsed, state)
        assert errors == []

    def test_changed_metric_name(self) -> None:
        parsed = parse(FIXTURES / "goal.invalid_metric_change.md")
        state = load_json(FIXTURES / "state.valid.json")
        errors = check_metric_identity(parsed, state)
        assert any("name changed" in e for e in errors)

    def test_changed_direction(self) -> None:
        parsed = parse(FIXTURES / "goal.valid.md")
        state = load_json(FIXTURES / "state.valid.json")
        # Mutate direction.
        state["objective"]["primary_metric"]["direction"] = "minimize"
        errors = check_metric_identity(parsed, state)
        assert any("direction changed" in e for e in errors)

    def test_fresh_state_accepts_any_metric(self) -> None:
        """When current state has no metric yet, any goal metric is OK."""
        parsed = parse(FIXTURES / "goal.valid.md")
        state = {"objective": {"primary_metric": {}}}
        errors = check_metric_identity(parsed, state)
        assert errors == []


# ===================================================================
# GoalManager — snapshot & staged activation
# ===================================================================

class TestGoalManager:
    def test_snapshot(self, tmp_path: Path) -> None:
        gm = GoalManager(tmp_path / ".auto_iterate")
        gm.snapshot_to(FIXTURES / "goal.valid.md")
        assert gm.goal_path.exists()
        # Content should match.
        original = (FIXTURES / "goal.valid.md").read_text()
        assert gm.goal_path.read_text() == original

    def test_stage_next(self, tmp_path: Path) -> None:
        gm = GoalManager(tmp_path / ".auto_iterate")
        gm.stage_next(FIXTURES / "goal.valid.md")
        assert gm.has_staged()
        assert gm.goal_next_path.exists()

    def test_activate_staged_valid(self, tmp_path: Path) -> None:
        gm = GoalManager(tmp_path / ".auto_iterate")
        # First, set up an active goal so the directory exists.
        gm.snapshot_to(FIXTURES / "goal.valid.md")
        # Stage a new goal (same metric identity).
        gm.stage_next(FIXTURES / "goal.valid.md")

        state = load_json(FIXTURES / "state.valid.json")
        success, errors = gm.activate_staged(state)
        assert success
        assert errors == []
        assert not gm.has_staged()  # goal.next.md consumed

    def test_activate_staged_rejects_metric_change(self, tmp_path: Path) -> None:
        gm = GoalManager(tmp_path / ".auto_iterate")
        gm.snapshot_to(FIXTURES / "goal.valid.md")
        gm.stage_next(FIXTURES / "goal.invalid_metric_change.md")

        state = load_json(FIXTURES / "state.valid.json")
        success, errors = gm.activate_staged(state)
        assert not success
        assert any("name changed" in e for e in errors)
        # goal.next.md should NOT be consumed on failure.
        assert gm.has_staged()

    def test_activate_noop_when_nothing_staged(self, tmp_path: Path) -> None:
        gm = GoalManager(tmp_path / ".auto_iterate")
        success, errors = gm.activate_staged({"objective": {"primary_metric": {}}})
        assert success
        assert errors == []

    def test_snapshot_missing_source(self, tmp_path: Path) -> None:
        gm = GoalManager(tmp_path / ".auto_iterate")
        with pytest.raises(GoalParseError, match="not found"):
            gm.snapshot_to("/nonexistent/goal.md")


# ===================================================================
# PolicyConfig
# ===================================================================

class TestPolicyConfig:
    def test_defaults(self) -> None:
        pc = PolicyConfig()
        frozen = pc.freeze()
        assert frozen["timeouts"]["plan"] == 1800
        assert frozen["retry_policy"]["max_phase_attempts"] == 2
        assert frozen["heartbeat"]["stale_threshold_sec"] == 120

    def test_merge_with_goal(self) -> None:
        pc = PolicyConfig()
        parsed_goal = parse(FIXTURES / "goal.valid.md")
        pc.merge_with_goal(parsed_goal)
        frozen = pc.freeze()
        # Goal patience should override default.
        assert frozen["patience"]["max_no_improve_rounds"] == 5
        assert frozen["screening_policy"]["enabled"] is True

    def test_cli_overrides_win(self) -> None:
        pc = PolicyConfig()
        parsed_goal = parse(FIXTURES / "goal.valid.md")
        pc.merge_with_goal(parsed_goal)
        pc.merge_with_cli({"budget": {"max_rounds": 999}})
        frozen = pc.freeze()
        assert frozen["budget"]["max_rounds"] == 999

    def test_freeze_is_independent_copy(self) -> None:
        pc = PolicyConfig()
        f1 = pc.freeze()
        f2 = pc.freeze()
        f1["timeouts"]["plan"] = 9999
        assert f2["timeouts"]["plan"] == 1800

    def test_get_dotted_key(self) -> None:
        pc = PolicyConfig()
        assert pc.get("timeouts.plan") == 1800
        assert pc.get("nonexistent.key", 42) == 42

    def test_load_from_fixture_yaml(self) -> None:
        config_path = REPO_ROOT / "tooling" / "auto_iterate" / "config" / "auto_iterate_controller.example.yaml"
        try:
            pc = PolicyConfig.load(config_path)
        except ImportError:
            pytest.skip("PyYAML not installed")
        frozen = pc.freeze()
        assert frozen["timeouts"]["plan"] == 1800
        assert frozen["terminate_grace_sec"] == 30


# ===================================================================
# AccountRegistry
# ===================================================================

class TestAccountRegistry:
    def _make_registry(self) -> AccountRegistry:
        """Build a registry from the example YAML."""
        path = REPO_ROOT / "tooling" / "auto_iterate" / "config" / "auto_iterate_accounts.example.yaml"
        try:
            return AccountRegistry.load(path)
        except ImportError:
            pytest.skip("PyYAML not installed")
            raise  # unreachable, keeps type checker happy

    def test_load(self) -> None:
        reg = self._make_registry()
        assert len(reg.accounts) >= 2
        assert "codex_acc1" in reg.get_ids()

    def test_select_prefers_current(self) -> None:
        reg = self._make_registry()
        state = {"accounts": {"selected_account_id": "codex_acc1"}}
        selected = reg.select_account(state)
        assert selected["id"] == "codex_acc1"

    def test_select_fallback_on_cooldown(self) -> None:
        reg = self._make_registry()
        reg.mark_cooldown("codex_acc1", "quota", cooldown_sec=3600)
        state = {"accounts": {"selected_account_id": "codex_acc1"}}
        selected = reg.select_account(state)
        assert selected["id"] == "codex_acc2"

    def test_select_raises_when_all_unavailable(self) -> None:
        reg = self._make_registry()
        for aid in reg.get_ids():
            reg.mark_cooldown(aid, "quota", cooldown_sec=3600)
        with pytest.raises(NoAccountAvailableError):
            reg.select_account()

    def test_auth_failure_excludes(self) -> None:
        reg = self._make_registry()
        reg.mark_auth_failure("codex_acc1")
        assert not reg.is_ready("codex_acc1")
        selected = reg.select_account()
        assert selected["id"] == "codex_acc2"

    def test_get_codex_home(self) -> None:
        reg = self._make_registry()
        home = reg.get_codex_home("codex_acc1")
        assert "codex" in home.lower() or "acc1" in home.lower()

    def test_record_usage(self) -> None:
        reg = self._make_registry()
        reg.record_usage("codex_acc1", calls=5)
        sd = reg.to_state_dict()
        assert sd["by_account"]["codex_acc1"]["used_calls"] == 5
        assert sd["selected_account_id"] == "codex_acc1"
        assert sd["by_account"]["codex_acc1"]["last_used_at"] is not None

    def test_to_state_dict(self) -> None:
        reg = self._make_registry()
        sd = reg.to_state_dict()
        assert "selected_account_id" in sd
        assert "by_account" in sd
        assert "codex_acc1" in sd["by_account"]

    def test_empty_registry_raises(self) -> None:
        reg = AccountRegistry()
        with pytest.raises(NoAccountAvailableError):
            reg.select_account()

    def test_load_missing_file(self) -> None:
        reg = AccountRegistry.load("/nonexistent/accounts.yaml")
        assert len(reg.accounts) == 0

    def test_restore_runtime_from_state(self) -> None:
        reg = self._make_registry()
        reg.restore_runtime({
            "selected_account_id": "codex_acc2",
            "by_account": {
                "codex_acc1": {
                    "used_calls": 10,
                    "last_used_at": "2026-03-23T00:00:00Z",
                    "cooldown_until": "2999-01-01T00:00:00+00:00",
                    "status": "ready",
                },
                "codex_acc2": {
                    "used_calls": 1,
                    "last_used_at": "2026-03-23T00:00:01Z",
                    "cooldown_until": None,
                    "status": "ready",
                },
            },
        })

        selected = reg.select_account({"accounts": {"selected_account_id": "codex_acc2"}})
        assert selected["id"] == "codex_acc2"
        sd = reg.to_state_dict()
        assert sd["selected_account_id"] == "codex_acc2"
        assert sd["by_account"]["codex_acc1"]["used_calls"] == 10
