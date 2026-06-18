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
    return root


def write_evaluation_contract_fixture(root: Path) -> None:
    contract_dir = root / "docs" / "10_contract"
    contract_dir.mkdir(parents=True)
    (contract_dir / "Evaluation_Contract.md").write_text(
        "# Evaluation Contract\n\nStatus: draft\nHuman approved: no\n",
        encoding="utf-8",
    )
    workflow_ctl.atomic_write_json(
        root / "PROJECT_STATE.json",
        {
            "schema_version": 1,
            "contracts": {
                "evaluation_contract": {
                    "path": "docs/10_contract/Evaluation_Contract.md",
                    "status": "draft",
                }
            },
        },
    )


def start_prepare_poc(
    root: Path,
    capsys,
) -> tuple[dict[str, object], dict[str, object]]:
    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "prepare",
            "--goal",
            "exercise prepare HITL PoC",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    payload = json.loads(capsys.readouterr().out)
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    return payload, pending


def test_prepare_start_generates_review_packet_and_approval_interrupt(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    payload, pending = start_prepare_poc(root, capsys)

    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["status"] == "paused"
    assert state["segment_status"] == "prepare_waiting_for_approval"
    assert state["current_node_id"] == "prepare_review_packet"
    assert state["completed_nodes"] == [
        "prepare_readiness_preflight",
        "prepare_protocol_compiler",
        "prepare_review_packet",
    ]
    assert pending["type"] == "APPROVE_ACTION"
    assert pending["reason"] == "evaluation_contract_approval_required"
    assert pending["request_snapshot_hash"] == workflow_ctl.request_snapshot_hash(
        pending
    )
    assert workflow_ctl.exact_action_hash(pending["exact_action"]) == pending[
        "exact_action"
    ]["action_hash"]
    assert (
        root
        / ".evidence"
        / "protocol_compiler"
        / run_id
        / "docs"
        / "35_protocol"
        / "Research_Protocol.md"
    ).exists()
    assert (
        root
        / ".evidence"
        / "review_packets"
        / "wf5"
        / run_id
        / "review_packet.md"
    ).exists()
    readiness_record = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "node_runs"
            / "prepare_readiness_preflight.json"
        ).read_text(encoding="utf-8")
    )
    assert readiness_record["gate_ledger"][0]["result"] == "PASS"
    protocol_record = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "node_runs"
            / "prepare_protocol_compiler.json"
        ).read_text(encoding="utf-8")
    )
    assert protocol_record["gate_ledger"][0]["result"] == "PASS"
    node_record = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "node_runs"
            / "prepare_review_packet.json"
        ).read_text(encoding="utf-8")
    )
    assert node_record["gate_ledger"][0]["result"] == "PASS"
    assert ".evidence/review_packets/" in node_record["evidence_refs"][0]
    assert any(
        ref.endswith("prepare_protocol_compiler.json")
        for ref in node_record["input_refs"]
    )


def test_prepare_readiness_preflight_rejects_missing_path_before_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    readiness_dir = root / ".workflow_supervisor"
    readiness_dir.mkdir()
    (readiness_dir / "readiness.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-06-05T00:00:00Z",
                "source": "test",
                "inputs": [
                    {
                        "key": "dataset_root",
                        "kind": "path",
                        "value": "missing/data",
                        "redacted_value": "missing/<redacted>",
                        "verification_status": "candidate",
                        "verified_at": None,
                        "verification_command": None,
                        "notes": "missing fixture path",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "prepare",
            "--goal",
            "exercise prepare readiness preflight",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["status"] == "paused"
    assert state["segment_status"] == "prepare_readiness_input_required"
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["type"] == "ASK_INPUT"
    assert pending["reason"] == "execution_readiness_input_required"
    preflight = json.loads(
        (root / ".workflow_supervisor" / "readiness_preflight.json").read_text(
            encoding="utf-8"
        )
    )
    assert preflight["inputs"][0]["verification_status"] == "rejected"
    node_record = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "node_runs"
            / "prepare_readiness_preflight.json"
        ).read_text(encoding="utf-8")
    )
    assert node_record["gate_ledger"][0]["result"] == "FAIL"
    assert not (root / ".evidence").exists()


def test_status_json_includes_pending_request_details(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    (root / "docs").mkdir()
    config_dir = root / "tooling" / "workflow_supervisor" / "config"
    config_dir.mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "tooling" / "workflow_supervisor" / "config" / "default_nodes.json",
        config_dir / "default_nodes.json",
    )
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "# Readiness\n",
        encoding="utf-8",
    )

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "prepare",
            "--goal",
            "prepare waits for dataset input",
            "--complete",
            "--json",
        ]
    )
    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    capsys.readouterr()

    status_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "status",
            "--json",
        ]
    )

    assert status_code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    pending = payload["pending_request_ref"]
    assert pending["request_id"] == payload["state"]["pending_request_id"]
    assert pending["type"] == "STEER"
    assert pending["node_id"] == "prepare_data_prep"
    assert pending["reason"] == "node_precondition_failed"
    assert "Preconditions failed" in pending["question"]
    assert pending["allowed_responses"] == [
        "acknowledge",
        "revise",
        "reject",
    ]
    assert pending["request_snapshot_hash"]
    assert payload["blocked_by"] == "node_precondition_failed"
    assert payload["acquisition_plan_ref"].endswith(
        "/runtime/acquisition_plan.json"
    )
    assert payload["resume_command"] == (
        "tooling/workflow_supervisor/scripts/workflow_ctl.sh "
        f"answer --request-id {pending['request_id']} --json <answer.json>"
    )
    assert payload["recovery"]["after_answer_command"] == (
        "tooling/workflow_supervisor/scripts/workflow_ctl.sh "
        f"resume --request-id {pending['request_id']} --json"
    )
    assert payload["recovery"]["recover_command"] == (
        "tooling/workflow_supervisor/scripts/workflow_ctl.sh "
        "recover --repair-stale-running --auto-resume-answered --json"
    )


def test_prepare_approve_resume_records_contract_and_reruns_gate(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    payload, pending = start_prepare_poc(root, capsys)
    run_id = payload["state"]["active_run_id"]
    write_evaluation_contract_fixture(root)

    approve_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "approve",
            "--request-id",
            pending["request_id"],
            "--decision",
            "approve",
            "--approved-by",
            "Test Reviewer",
            "--json",
        ]
    )
    assert approve_code == workflow_ctl.EXIT_OK
    approval_status = json.loads(capsys.readouterr().out)
    assert approval_status["state"]["status"] == "paused"
    answer_record = json.loads(
        next((root / ".workflow_supervisor" / "answers").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    answers = answer_record["answer"]["answers"]
    assert answers["approval_execution"]["status"] == "PASS"
    project_state = json.loads((root / "PROJECT_STATE.json").read_text())
    assert project_state["contracts"]["evaluation_contract"]["status"] == "approved"

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
    resume_payload = json.loads(capsys.readouterr().out)
    state = resume_payload["state"]
    assert state["status"] == "completed"
    assert state["segment_status"] == "prepare_hitl_poc"
    assert state["resolved_inputs_ref"].endswith(
        f"{pending['request_id']}.wf5_dynamic_context_after_approval.json"
    )
    assert not (root / ".workflow_supervisor" / "pending_request.json").exists()
    assert (root / state["resolved_inputs_ref"]).exists()
    events = workflow_ctl.read_events(root)
    assert any(event["event"] == "DYNAMIC_CONTEXT_GATE_RERUN" for event in events)
    assert any(event["event"] == "APPROVAL_RECORDED" for event in events)
    assert run_id == state["active_run_id"]


def test_prepare_revise_resume_records_revision_status(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    _, pending = start_prepare_poc(root, capsys)

    approve_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "approve",
            "--request-id",
            pending["request_id"],
            "--decision",
            "revise",
            "--approved-by",
            "Test Reviewer",
        ]
    )
    assert approve_code == workflow_ctl.EXIT_OK
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
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"]["segment_status"] == "prepare_revision_requested"


def test_prepare_hitl_poc_does_not_unlock_build(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    _, pending = start_prepare_poc(root, capsys)
    write_evaluation_contract_fixture(root)
    assert (
        workflow_ctl.main(
            [
                "--workspace-root",
                str(root),
                "approve",
                "--request-id",
                pending["request_id"],
                "--decision",
                "approve",
                "--approved-by",
                "Test Reviewer",
            ]
        )
        == workflow_ctl.EXIT_OK
    )
    capsys.readouterr()
    assert (
        workflow_ctl.main(
            [
                "--workspace-root",
                str(root),
                "resume",
                "--request-id",
                pending["request_id"],
            ]
        )
        == workflow_ctl.EXIT_OK
    )
    capsys.readouterr()

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "build",
            "--goal",
            "must not unlock from prepare_hitl_poc",
            "--dry-run",
        ]
    )

    assert code == workflow_ctl.EXIT_INVALID_INPUT
    err = capsys.readouterr().err
    assert "prepare_hitl_poc cannot unlock build" in err
