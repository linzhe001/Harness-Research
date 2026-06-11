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
    (root / "iteration_log.json").write_text("[]\n", encoding="utf-8")
    return root


def approved_contracts() -> dict[str, dict[str, object]]:
    return {
        "project_contract": {"exists": True, "approval_confirmed": True},
        "evaluation_contract": {"exists": True, "approval_confirmed": True},
        "baseline_contract": {"exists": True, "approval_confirmed": True},
        "claim_boundary": {"exists": True, "approval_confirmed": True},
    }


def fake_wf12_gate(
    exit_code: int,
    calls: list[dict[str, object]],
    *,
    dynamic_context: bool = True,
    contracts: dict[str, dict[str, object]] | None = None,
):
    def _gate(
        workspace_root: Path,
        *,
        stage: str,
        build_id: str,
        write_review_packet: bool,
    ) -> dict[str, object]:
        calls.append(
            {
                "stage": stage,
                "build_id": build_id,
                "write_review_packet": write_review_packet,
            }
        )
        packet = None
        if write_review_packet:
            packet_dir = (
                workspace_root / ".evidence" / "review_packets" / stage / build_id
            )
            packet_dir.mkdir(parents=True)
            markdown = packet_dir / "review_packet.md"
            packet_json = packet_dir / "review_packet.json"
            markdown.write_text("# WF12 packet\n", encoding="utf-8")
            packet_json.write_text("{}\n", encoding="utf-8")
            packet = {
                "markdown_path": markdown.relative_to(workspace_root).as_posix(),
                "json_path": packet_json.relative_to(workspace_root).as_posix(),
                "output_dir": packet_dir.relative_to(workspace_root).as_posix(),
            }
        return {
            "command": (
                "python tooling/evidence/check_dynamic_context.py "
                f"--workspace-root . --stage {stage} --json"
            ),
            "exit_code": exit_code,
            "stdout": {
                "ok": exit_code == 0,
                "stage": stage,
                "gates": {
                    "context": {
                        "ok": exit_code == 0,
                        "dynamic_context": dynamic_context,
                        "contracts": contracts or approved_contracts(),
                    }
                },
                "review_packet": packet,
            },
            "stderr": "",
        }

    return _gate


def write_release_worker(tmp_path: Path) -> Path:
    script = tmp_path / "fixture_release_worker.py"
    script.write_text(
        r'''
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    root = Path(args.workspace_root)
    if args.node_id != "release_final_exp_matrix":
        raise SystemExit(f"unexpected node {args.node_id}")
    matrix = root / "docs" / "Final_Experiment_Matrix.md"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text("# Final Experiment Matrix\n", encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "schema_version": 1,
        "run_id": args.run_id,
        "node_id": args.node_id,
        "skill": "final-exp",
        "attempt": 1,
        "status": "success",
        "exit_code": 0,
        "started_at": now,
        "finished_at": now,
        "summary": "fixture final experiment matrix",
        "artifact_refs": ["docs/Final_Experiment_Matrix.md"],
        "gate_ledger": [
            {
                "command": (
                    "python tooling/evidence/check_dynamic_context.py "
                    "--workspace-root . --stage wf11 --review-packet"
                ),
                "result": "PASS",
                "reason": "fixture wf11 gate",
                "artifacts": [".evidence/review_packets/wf11/build/review_packet.md"],
            },
            {
                "command": (
                    "python tooling/evidence/compile_doc.py --workspace-root . "
                    "--doc docs/Final_Experiment_Matrix.md "
                    "--source iteration_log.json docs/10_contract/Claim_Boundary.md"
                ),
                "result": "PASS",
                "reason": "fixture final matrix docchain",
                "artifacts": [
                    ".evidence/chains/final_experiment_matrix/evidence_chain.json",
                ],
            },
        ],
        "postcondition_claims": [],
        "interrupt_request": None,
        "observed_writes": ["docs/Final_Experiment_Matrix.md"],
        "stdout_ref": None,
        "stderr_ref": None,
        "contract_violations": [],
        "worker_warnings": [],
    }
    Path(args.result).write_text(json.dumps(result) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''.lstrip(),
        encoding="utf-8",
    )
    return script


def start_release(
    root: Path,
    goal: str,
    capsys,
    *,
    worker: Path | None = None,
) -> tuple[int, dict[str, object]]:
    command = [
        "--workspace-root",
        str(root),
        "start",
        "--segment",
        "release",
        "--goal",
        goal,
        "--json",
    ]
    if worker is not None:
        command.extend(
            [
                "--worker-command",
                (
                    f"{sys.executable} {worker} --workspace-root "
                    "{workspace_root} --run-id {run_id} --node-id {node_id} "
                    "--result {result_path}"
                ),
            ]
        )
    code = workflow_ctl.main(command)
    payload = json.loads(capsys.readouterr().out)
    return code, payload


def test_release_start_gate_pass_creates_exact_approval_interrupt(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    worker = write_release_worker(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        workflow_ctl,
        "run_dynamic_context_gate",
        fake_wf12_gate(0, calls),
    )

    code, payload = start_release(
        root,
        "package release artifacts",
        capsys,
        worker=worker,
    )

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["status"] == "paused"
    assert state["segment_status"] == "release_ready_for_approval"
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["type"] == "APPROVE_ACTION"
    assert pending["reason"] == "release_submission_approval_required"
    assert pending["exact_action"]["release_action"] == "package"
    assert "harness release package" in pending["exact_action"]["command"]
    assert workflow_ctl.exact_action_hash(pending["exact_action"]) == pending[
        "exact_action"
    ]["action_hash"]
    assert pending["request_snapshot_hash"] == workflow_ctl.request_snapshot_hash(
        pending
    )
    node_record = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "node_runs"
            / "release_claim_approval.json"
        ).read_text(encoding="utf-8")
    )
    assert node_record["gate_ledger"][0]["result"] == "PASS"
    assert node_record["release_action"] == "package"
    assert calls[0]["stage"] == "wf12"
    assert calls[0]["write_review_packet"] is True
    assert "release_final_exp_matrix" in state["completed_nodes"]


def test_release_approve_resume_reruns_gate_without_packaging(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    worker = write_release_worker(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        workflow_ctl,
        "run_dynamic_context_gate",
        fake_wf12_gate(0, calls),
    )
    _, payload = start_release(root, "submit release package", capsys, worker=worker)
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )

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
            "Release Reviewer",
            "--json",
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
    resumed = json.loads(capsys.readouterr().out)
    state = resumed["state"]
    assert state["status"] == "completed"
    assert state["segment_status"] == "release_approval_recorded"
    assert state["resolved_inputs_ref"].endswith(
        f"{pending['request_id']}.wf12_dynamic_context_after_approval.json"
    )
    assert len(calls) == 2
    assert calls[1]["write_review_packet"] is False
    assert not (root / "submission").exists()
    assert not (root / ".workflow_supervisor" / "pending_request.json").exists()
    assert payload["state"]["active_run_id"] == state["active_run_id"]


def test_release_gate_failure_fails_closed_to_steer(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    worker = write_release_worker(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        workflow_ctl,
        "run_dynamic_context_gate",
        fake_wf12_gate(1, calls),
    )

    code, payload = start_release(
        root,
        "package release artifacts",
        capsys,
        worker=worker,
    )

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["status"] == "paused"
    assert state["segment_status"] == "release_gate_failed"
    assert state["failed_nodes"] == ["release_claim_approval"]
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["type"] == "STEER"
    assert pending["reason"] == "release_gate_failed"
    assert pending["exact_action"] is None
    node_record = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "node_runs"
            / "release_claim_approval.json"
        ).read_text(encoding="utf-8")
    )
    assert node_record["gate_ledger"][0]["result"] == "FAIL"


def test_release_legacy_context_fails_closed_before_approval(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    worker = write_release_worker(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        workflow_ctl,
        "run_dynamic_context_gate",
        fake_wf12_gate(0, calls, dynamic_context=False),
    )

    code, payload = start_release(
        root,
        "package release artifacts",
        capsys,
        worker=worker,
    )

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    assert payload["state"]["segment_status"] == "release_gate_failed"
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["type"] == "STEER"
    assert pending["reason"] == "release_gate_failed"
    assert any(
        "dynamic_context_required_for_release" in item
        for item in pending["risk_summary"]
    )


def test_release_requires_explicit_action_before_gates(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("release gate should not run before action is scoped")

    monkeypatch.setattr(workflow_ctl, "run_dynamic_context_gate", fail_if_called)

    code, payload = start_release(root, "final handoff", capsys)

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    assert payload["state"]["segment_status"] == "release_action_unclear"
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["type"] == "STEER"
    assert pending["reason"] == "release_action_unclear"
    assert pending["allowed_responses"] == workflow_ctl.RELEASE_ACTION_RESPONSES


def test_release_resume_after_final_exp_input_continues_to_wf12(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    (root / "iteration_log.json").unlink()
    worker = write_release_worker(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        workflow_ctl,
        "run_dynamic_context_gate",
        fake_wf12_gate(0, calls),
    )

    code, payload = start_release(
        root,
        "package release artifacts",
        capsys,
        worker=worker,
    )
    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    assert payload["state"]["segment_status"] == "node_precondition_failed"
    original_pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert original_pending["node_id"] == "release_final_exp_matrix"
    assert calls == []

    (root / "iteration_log.json").write_text("[]\n", encoding="utf-8")
    answer_path = root / "answer.json"
    answer_path.write_text(
        json.dumps(
            {
                "request_id": original_pending["request_id"],
                "request_snapshot_hash": original_pending["request_snapshot_hash"],
                "idempotency_key": f"{original_pending['request_id']}:ack",
                "answered_by": "Release Reviewer",
                "answered_at": "2026-06-11T00:00:00Z",
                "answers": {"decision": "acknowledge"},
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
            original_pending["request_id"],
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
            original_pending["request_id"],
            "--json",
        ]
    )

    assert resume_code == workflow_ctl.EXIT_MANUAL_ACTION
    resumed = json.loads(capsys.readouterr().out)
    state = resumed["state"]
    assert state["status"] == "paused"
    assert state["segment_status"] == "release_ready_for_approval"
    assert state["completed_nodes"] == [
        "release_final_exp_matrix",
        "release_claim_approval",
    ]
    next_pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert next_pending["request_id"] != original_pending["request_id"]
    assert next_pending["reason"] == "release_submission_approval_required"
    assert calls[0]["stage"] == "wf12"
    assert calls[0]["write_review_packet"] is True
