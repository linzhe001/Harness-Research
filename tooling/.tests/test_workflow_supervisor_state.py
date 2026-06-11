from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "workflow_supervisor" / "scripts"))

import workflow_ctl  # noqa: E402


def make_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas")
    config_dir = root / "tooling" / "workflow_supervisor" / "config"
    config_dir.mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "tooling" / "workflow_supervisor" / "config" / "default_nodes.json",
        config_dir / "default_nodes.json",
    )
    return root


def test_status_reports_missing_state(tmp_path: Path, capsys) -> None:
    root = make_workspace(tmp_path)

    code = workflow_ctl.main(
        ["--workspace-root", str(root), "status", "--json"]
    )

    assert code == workflow_ctl.EXIT_NO_STATE
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "missing"


def test_start_dry_run_writes_state_manifest_and_events(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "prepare",
            "--goal",
            "exercise supervisor dry run",
            "--dry-run",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["status"] == "completed"
    assert state["segment"] == "prepare"
    assert state["segment_status"] == "dry_run_readiness_passed"
    assert state["completed_nodes"] == ["prepare_readiness_preflight"]
    assert not (root / ".workflow_supervisor" / "lock.json").exists()
    assert (
        root
        / ".workflow_supervisor"
        / "runs"
        / run_id
        / "run_manifest.json"
    ).exists()
    manifest = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "run_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["policy"]["gate_policy_ref"] == (
        "tooling/workflow_supervisor/config/gate_policy.yaml"
    )
    assert manifest["policy"]["gate_profile"] == "default"
    summary = (
        root
        / ".workflow_supervisor"
        / "runs"
        / run_id
        / "stage_summary.md"
    )
    assert summary.exists()
    assert "prepare_readiness_preflight" in summary.read_text(encoding="utf-8")
    events = workflow_ctl.read_events(root)
    assert [event["seq"] for event in events] == [1, 2, 3]
    assert events[-1]["event"] == "RUN_COMPLETED"


def test_start_without_dry_run_pauses_with_typed_request(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "build",
            "--goal",
            "non dry run should not invoke skills in v0",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    assert state["status"] == "paused"
    assert state["segment_status"] == "node_precondition_failed"
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["type"] == "STEER"
    assert pending["node_id"] == "build_refine_arch"
    assert pending["request_snapshot_hash"] == workflow_ctl.request_snapshot_hash(
        pending
    )


def test_start_fails_closed_when_pending_request_exists(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    original_run_id = "sup_20260605_010000"
    request = workflow_ctl.create_node_pending_request(
        root,
        run_id=original_run_id,
        segment="build",
        node_id="build_validate_run",
        request_type="STEER",
        reason="validation_decision_required",
        question="Resolve validation failure.",
    )
    state = workflow_ctl.base_state(original_run_id, "build")
    state["status"] = "paused"
    state["segment_status"] = "validation_decision_required"
    state["pending_request_id"] = request["request_id"]
    workflow_ctl.save_state(root, state)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "build",
            "--goal",
            "new build should not overwrite pending request",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_INVALID_INPUT
    capsys.readouterr()
    loaded = json.loads(
        (root / ".workflow_supervisor" / "state.json").read_text(encoding="utf-8")
    )
    assert loaded["active_run_id"] == original_run_id
    assert loaded["pending_request_id"] == request["request_id"]


def test_state_invariants_reject_paused_without_pending() -> None:
    state = workflow_ctl.base_state("sup_20260605_000000", "prepare")
    state["status"] = "paused"
    state["pending_request_id"] = None

    errors = workflow_ctl.validate_state_invariants(state)

    assert "status=paused requires pending_request_id" in errors
