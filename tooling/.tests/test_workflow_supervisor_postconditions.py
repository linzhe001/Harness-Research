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


def worker_result(
    *,
    run_id: str,
    node_id: str,
    gate_ledger: list[dict[str, object]] | None = None,
    observed_writes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "node_id": node_id,
        "skill": "validate-run",
        "attempt": 1,
        "status": "success",
        "exit_code": 0,
        "started_at": "2026-06-05T00:00:00Z",
        "finished_at": "2026-06-05T00:01:00Z",
        "summary": "fixture result",
        "artifact_refs": ["docs/Validate_Run_Report.md"],
        "gate_ledger": gate_ledger or [],
        "postcondition_claims": [],
        "interrupt_request": None,
        "observed_writes": observed_writes or ["docs/Validate_Run_Report.md"],
        "stdout_ref": ".workflow_supervisor/runs/sup/runtime/stdout.log",
        "stderr_ref": ".workflow_supervisor/runs/sup/runtime/stderr.log",
        "contract_violations": [],
        "worker_warnings": [],
    }


def test_validate_postconditions_records_pass_and_not_run(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    run_id = "sup_20260605_000000"
    (root / "docs").mkdir()
    (root / "docs" / "Validate_Run_Report.md").write_text(
        "# Validate\n",
        encoding="utf-8",
    )
    result_path = root / "worker_result.json"
    result_path.write_text(
        json.dumps(
            worker_result(
                run_id=run_id,
                node_id="build_validate_run",
                gate_ledger=[
                    {
                        "command": (
                            "python tooling/evidence/check_dynamic_context.py "
                            "--workspace-root . --stage wf10 --review-packet"
                        ),
                        "result": "PASS",
                        "reason": "fixture gate passed",
                        "artifacts": [
                            ".evidence/review_packets/wf10/build/review_packet.md"
                        ],
                    }
                ],
            )
        )
        + "\n",
        encoding="utf-8",
    )

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "validate-postconditions",
            "--node-id",
            "build_validate_run",
            "--run-id",
            run_id,
            "--worker-result",
            str(result_path),
            "--record",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert [gate["result"] for gate in payload["gate_ledger"]] == [
        "PASS",
        "PASS",
        "PASS",
    ]
    assert (root / payload["record_path"]).exists()


def test_validate_postconditions_records_not_run_for_missing_worker_gate(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    run_id = "sup_20260605_000000"
    (root / "project_map.json").write_text("{}\n", encoding="utf-8")
    result_path = root / "worker_result.json"
    payload = worker_result(run_id=run_id, node_id="build_code_debug")
    payload["skill"] = "code-debug"
    payload["artifact_refs"] = ["project_map.json"]
    payload["observed_writes"] = ["project_map.json"]
    result_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "validate-postconditions",
            "--node-id",
            "build_code_debug",
            "--run-id",
            run_id,
            "--worker-result",
            str(result_path),
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    result = json.loads(capsys.readouterr().out)
    assert [gate["result"] for gate in result["gate_ledger"]] == [
        "PASS",
        "NOT_RUN",
        "PASS",
    ]


def test_validate_postconditions_fails_missing_artifact(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    run_id = "sup_20260605_000000"

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "validate-postconditions",
            "--node-id",
            "build_validate_run",
            "--run-id",
            run_id,
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_INVALID_INPUT
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["failed_checks"][0]["result"] == "FAIL"
