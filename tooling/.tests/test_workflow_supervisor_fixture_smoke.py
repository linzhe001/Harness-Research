from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "workflow_supervisor" / "scripts"))

import workflow_ctl  # noqa: E402


def make_fixture_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "target_workspace"
    root.mkdir()
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas")
    config_dir = root / "tooling" / "workflow_supervisor" / "config"
    config_dir.mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "tooling" / "workflow_supervisor" / "config" / "default_nodes.json",
        config_dir / "default_nodes.json",
    )
    return root


def install_supervisor_scripts(root: Path) -> Path:
    scripts_dir = root / "tooling" / "workflow_supervisor" / "scripts"
    scripts_dir.mkdir(parents=True)
    for name in ["workflow_ctl.py", "workflow_ctl.sh", "harness.sh"]:
        source = REPO_ROOT / "tooling" / "workflow_supervisor" / "scripts" / name
        target = scripts_dir / name
        shutil.copy2(source, target)
        target.chmod(0o755)
    shutil.copytree(
        REPO_ROOT / "tooling" / "grill",
        root / "tooling" / "grill",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    return scripts_dir


def test_supervisor_dry_run_on_fixture_target_workspace(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_fixture_workspace(tmp_path)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "build",
            "--goal",
            "fixture supervisor dry run",
            "--dry-run",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    assert state["status"] == "completed"
    assert state["segment"] == "build"
    assert state["segment_status"] == "dry_run_completed"
    assert state["completed_nodes"] == ["dry_run_bootstrap"]
    assert (root / ".workflow_supervisor" / "state.json").exists()
    assert not (root / ".auto_iterate").exists()
    assert not (REPO_ROOT / ".workflow_supervisor").exists()


def test_harness_sh_segment_shorthand_uses_fixture_workspace(
    tmp_path: Path,
) -> None:
    root = make_fixture_workspace(tmp_path)
    scripts_dir = install_supervisor_scripts(root)

    proc = subprocess.run(
        [
            str(scripts_dir / "harness.sh"),
            "build",
            "--goal",
            "fixture harness wrapper dry run",
            "--dry-run",
            "--json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == workflow_ctl.EXIT_OK, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["state"]["segment"] == "build"
    assert payload["state"]["segment_status"] == "dry_run_completed"
    assert (root / ".workflow_supervisor" / "state.json").exists()
    assert not (REPO_ROOT / ".workflow_supervisor").exists()


def test_harness_sh_grill_shorthand_uses_fixture_workspace(
    tmp_path: Path,
) -> None:
    root = make_fixture_workspace(tmp_path)
    scripts_dir = install_supervisor_scripts(root)

    proc = subprocess.run(
        [
            str(scripts_dir / "harness.sh"),
            "grill",
            "init",
            "--seed",
            "fixture research intent",
            "--json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == workflow_ctl.EXIT_OK, proc.stderr
    payload = json.loads(proc.stdout)
    assert "docs/Research_Intent_Draft.md" in payload["written"]
    assert (root / "docs" / "Research_Intent_Draft.md").exists()


def test_supervisor_interrupted_resumed_run_on_fixture_target_workspace(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_fixture_workspace(tmp_path)

    start_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "change",
            "--goal",
            "make it better",
            "--json",
        ]
    )

    assert start_code == workflow_ctl.EXIT_MANUAL_ACTION
    started = json.loads(capsys.readouterr().out)
    assert started["state"]["status"] == "paused"
    assert started["state"]["segment_status"] == "change_route_uncertain"
    pending_path = root / ".workflow_supervisor" / "pending_request.json"
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    assert pending["type"] == "STEER"
    assert pending["reason"] == "change_route_uncertain"
    answer_path = root / "operator_answer.json"
    answer_path.write_text(
        json.dumps(
            {
                "request_id": pending["request_id"],
                "request_snapshot_hash": pending["request_snapshot_hash"],
                "idempotency_key": "fixture-steer-route",
                "answered_by": "fixture",
                "answered_at": "2026-06-05T00:00:00Z",
                "answers": {"decision": "delta_grill"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    answer_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "answer",
            "--request-id",
            pending["request_id"],
            "--json",
            str(answer_path),
        ]
    )
    assert answer_code == workflow_ctl.EXIT_OK
    capsys.readouterr()

    resume_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "resume",
            "--request-id",
            pending["request_id"],
            "--json",
        ]
    )

    assert resume_code == workflow_ctl.EXIT_OK
    resumed = json.loads(capsys.readouterr().out)
    state = resumed["state"]
    assert state["status"] == "completed"
    assert state["segment_status"] == "change_routed_delta_grill"
    assert state["resolved_inputs_ref"].endswith(f"{pending['request_id']}.answer.json")
    assert not pending_path.exists()
    assert (root / ".workflow_supervisor" / "state.json").exists()
    assert not (root / ".auto_iterate").exists()
    assert not (REPO_ROOT / ".workflow_supervisor").exists()
