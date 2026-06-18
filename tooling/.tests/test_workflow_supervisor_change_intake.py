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


def start_change(root: Path, goal: str, capsys) -> tuple[int, dict[str, object]]:
    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "change",
            "--goal",
            goal,
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    return code, payload


def load_change_request(root: Path, payload: dict[str, object]) -> dict[str, object]:
    state = payload["state"]
    assert isinstance(state, dict)
    ref = state["resolved_inputs_ref"]
    assert isinstance(ref, str)
    return json.loads((root / ref).read_text(encoding="utf-8"))


def test_change_intake_routes_bugfix_to_code_debug_and_validates_postcondition(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    code, payload = start_change(
        root,
        "Fix traceback in src/parser.py from a failing focused test.",
        capsys,
    )

    assert code == workflow_ctl.EXIT_OK
    state = payload["state"]
    assert state["status"] == "completed"
    assert state["segment_status"] == "change_routed_code_debug"
    change_request = load_change_request(root, payload)
    assert change_request["change_type"] == "bugfix"
    assert change_request["route"] == "code-debug"
    assert "src/parser.py" in change_request["affected_paths"]

    post_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "validate-postconditions",
            "--node-id",
            "change_classify_request",
            "--run-id",
            str(state["active_run_id"]),
            "--json",
        ]
    )

    assert post_code == workflow_ctl.EXIT_OK
    postcondition = json.loads(capsys.readouterr().out)
    assert postcondition["ok"] is True
    assert postcondition["gate_ledger"][0]["result"] == "PASS"


def test_change_intake_routes_evaluation_delta_to_review_packet(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    code, payload = start_change(
        root,
        "Change the primary metric, baseline set, and validation protocol.",
        capsys,
    )

    assert code == workflow_ctl.EXIT_OK
    assert payload["state"]["segment_status"] == "change_routed_review_packet"
    change_request = load_change_request(root, payload)
    assert change_request["change_type"] == "evaluation_delta"
    assert change_request["route"] == "review_packet"
    assert "Evaluation_Contract" in change_request["affected_contracts"]
    assert "Baseline_Contract" in change_request["affected_contracts"]
    assert any(
        "Human Approval" in item
        for item in change_request["gate_evidence_plan"]
    )


def test_change_intake_routes_claim_boundary_delta_to_claim_delta_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    code, payload = start_change(
        root,
        "Narrow the release claim and update the conclusion boundary.",
        capsys,
    )

    assert code == workflow_ctl.EXIT_OK
    assert payload["state"]["segment_status"] == "change_routed_claim_boundary_review"
    change_request = load_change_request(root, payload)
    assert change_request["change_type"] == "claim_boundary_delta"
    assert change_request["route"] == "claim_boundary_review"
    assert "Claim_Boundary" in change_request["affected_contracts"]
    assert "Claim Delta Evidence" in change_request["gate_evidence_plan"]
    assert not any(
        "Human Approval" in item for item in change_request["gate_evidence_plan"]
    )


def test_change_intake_routes_harness_guardrail_to_harness_maintenance(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    code, payload = start_change(
        root,
        "Update tooling/codex_hooks policy and .agents skill contract routing.",
        capsys,
    )

    assert code == workflow_ctl.EXIT_OK
    assert payload["state"]["segment_status"] == "change_routed_harness_maintenance"
    change_request = load_change_request(root, payload)
    assert change_request["change_type"] == "harness_guardrail_delta"
    assert change_request["route"] == "harness-maintenance"
    assert "Skill_Contracts" in change_request["affected_contracts"]


def test_change_intake_fails_closed_to_steer_and_resume_records_route(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    code, payload = start_change(root, "make it better", capsys)

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    state = payload["state"]
    assert state["status"] == "paused"
    assert state["segment_status"] == "change_route_uncertain"
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["type"] == "STEER"
    assert pending["reason"] == "change_route_uncertain"
    assert pending["request_snapshot_hash"] == workflow_ctl.request_snapshot_hash(
        pending
    )
    change_request = load_change_request(root, payload)
    assert change_request["route"] == "steer"
    answer_path = root / "answer.json"
    answer_path.write_text(
        json.dumps(
            {
                "request_id": pending["request_id"],
                "request_snapshot_hash": pending["request_snapshot_hash"],
                "idempotency_key": "fixture-change-route",
                "answered_by": "test",
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
    assert resumed["state"]["status"] == "completed"
    assert resumed["state"]["segment_status"] == "change_routed_delta_grill"
    assert not (root / ".workflow_supervisor" / "pending_request.json").exists()
