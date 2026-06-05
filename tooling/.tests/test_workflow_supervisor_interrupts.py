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
    (root / ".workflow_supervisor").mkdir()
    return root


def write_state_and_pending(root: Path, pending: dict[str, object]) -> None:
    workflow_ctl.atomic_write_json(
        root / ".workflow_supervisor" / "pending_request.json",
        pending,
    )
    state = workflow_ctl.base_state(str(pending["run_id"]), "prepare")
    state["status"] = "paused"
    state["pending_request_id"] = pending["request_id"]
    workflow_ctl.save_state(root, state)


def write_contract_fixture(root: Path) -> None:
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


def approve_pending_request() -> dict[str, object]:
    source = ".evidence/review_packets/wf5/build_001/review_packet.md"
    exact_action = {
        "command": (
            "python tooling/evidence/approve_contract.py --workspace-root . "
            "--contract evaluation_contract"
        ),
        "contract": "evaluation_contract",
        "approval_source": source,
    }
    exact_action["action_hash"] = workflow_ctl.exact_action_hash(exact_action)
    pending: dict[str, object] = {
        "schema_version": 1,
        "request_id": "req_20260605_000000",
        "run_id": "sup_20260605_000000",
        "node_id": "wf5_review_packet",
        "type": "APPROVE_ACTION",
        "reason": "evaluation_contract_approval_required",
        "question": "Approve the Evaluation Contract?",
        "allowed_responses": ["approve", "revise", "reject"],
        "exact_action": exact_action,
        "evidence_refs": [{"kind": "review_packet", "path": source}],
        "diff_refs": [],
        "gate_status_refs": [],
        "risk_summary": ["approval is exact-action scoped"],
        "rollback_plan": None,
        "escalation_policy": {"expires_at": None, "on_expire": "fail_closed"},
        "resume_strategy": "adopt_if_postconditions_pass_else_rerun",
        "created_at": "2026-06-05T00:00:00Z",
        "expires_at": None,
    }
    pending["request_snapshot_hash"] = workflow_ctl.request_snapshot_hash(pending)
    return pending


def test_answer_rejects_stale_request_snapshot(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    pending = approve_pending_request()
    write_state_and_pending(root, pending)
    answer_path = root / "answers.json"
    answer_path.write_text(
        json.dumps(
            {
                "request_id": pending["request_id"],
                "request_snapshot_hash": "sha256:stale",
                "idempotency_key": "req:operator:approve",
                "answered_by": "operator",
                "answered_at": "2026-06-05T00:01:00Z",
                "answers": {"decision": "approve"},
            }
        ),
        encoding="utf-8",
    )

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "answer",
            "--request-id",
            str(pending["request_id"]),
            "--json",
            str(answer_path),
        ]
    )

    assert code == workflow_ctl.EXIT_INVALID_INPUT


def test_approve_derives_single_review_packet_source(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    write_contract_fixture(root)
    pending = approve_pending_request()
    write_state_and_pending(root, pending)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "approve",
            "--request-id",
            str(pending["request_id"]),
            "--decision",
            "approve",
            "--approved-by",
            "Test Reviewer",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"]["status"] == "paused"
    answer_record = json.loads(
        next((root / ".workflow_supervisor" / "answers").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    answers = answer_record["answer"]["answers"]
    assert answers["decision"] == "approve"
    assert answers["approval_source"] == pending["evidence_refs"][0]["path"]
    assert answers["approval_execution"]["status"] == "PASS"
    project_state = json.loads((root / "PROJECT_STATE.json").read_text())
    assert project_state["contracts"]["evaluation_contract"]["status"] == "approved"
    contract_text = (
        root / "docs" / "10_contract" / "Evaluation_Contract.md"
    ).read_text(encoding="utf-8")
    assert "Status: approved" in contract_text
    events = workflow_ctl.read_events(root)
    assert events[-1]["event"] == "APPROVAL_RECORDED"


def test_approve_fails_closed_when_contract_state_missing(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    pending = approve_pending_request()
    write_state_and_pending(root, pending)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "approve",
            "--request-id",
            str(pending["request_id"]),
            "--decision",
            "approve",
            "--approved-by",
            "Test Reviewer",
        ]
    )

    assert code == workflow_ctl.EXIT_INVALID_INPUT
    assert not (root / ".workflow_supervisor" / "answers").exists()


def test_approve_idempotency_prevents_duplicate_execution(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    write_contract_fixture(root)
    pending = approve_pending_request()
    write_state_and_pending(root, pending)
    command = [
        "--workspace-root",
        str(root),
        "approve",
        "--request-id",
        str(pending["request_id"]),
        "--decision",
        "approve",
        "--approved-by",
        "Test Reviewer",
        "--json",
    ]

    assert workflow_ctl.main(command) == workflow_ctl.EXIT_OK
    capsys.readouterr()
    assert workflow_ctl.main(command) == workflow_ctl.EXIT_OK
    capsys.readouterr()

    events = workflow_ctl.read_events(root)
    assert [event["event"] for event in events].count("APPROVAL_RECORDED") == 1


def test_approve_rejects_stale_exact_action_hash(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    pending = approve_pending_request()
    pending["exact_action"]["approval_source"] = (
        ".evidence/review_packets/wf5/build_002/review_packet.md"
    )
    write_state_and_pending(root, pending)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "approve",
            "--request-id",
            str(pending["request_id"]),
            "--decision",
            "approve",
            "--approved-by",
            "Test Reviewer",
            "--approval-source",
            ".evidence/review_packets/wf5/build_002/review_packet.md",
        ]
    )

    assert code == workflow_ctl.EXIT_INVALID_INPUT
