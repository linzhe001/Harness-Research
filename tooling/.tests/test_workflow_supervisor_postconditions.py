from __future__ import annotations

import json
import shutil
import subprocess
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


def init_git_workspace(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
    )
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test: initial supervisor fixture"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Harness Test"],
        cwd=root,
        check=True,
    )


def commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=root,
            check=True,
            capture_output=True,
        )


def commit_paths(root: Path, message: str, *paths: str) -> None:
    subprocess.run(["git", "add", *paths], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        check=True,
        capture_output=True,
    )


def write_run_manifest(root: Path, run_id: str, base_commit: str) -> None:
    path = root / ".workflow_supervisor" / "runs" / run_id / "run_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "segment": "build",
                "base_git_commit": base_commit,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_roadmap_commit_plan(root: Path) -> None:
    path = root / "docs" / "Implementation_Roadmap.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Roadmap",
                "",
                "## 4b. commit_plan",
                "",
                "| commit_slice | Files | Validation | Commit Message | Reason |",
                "|---|---|---|---|---|",
                (
                    "| `S1_data_answer_contract` | src/s1.py | py_compile | "
                    "`feat(slice/S1_data_answer_contract): add records` | slice |"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


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
    init_git_workspace(root)
    run_id = "sup_20260605_000000"
    (root / "docs").mkdir()
    (root / "docs" / "Validate_Run_Report.md").write_text(
        "# Validate\n",
        encoding="utf-8",
    )
    commit_all(root, "test: validate fixture")
    result_path = root / ".workflow_supervisor" / "worker_result.json"
    result_path.parent.mkdir(parents=True)
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
                    },
                    {
                        "command": "validate-run verdict",
                        "result": "PASS",
                        "reason": "fixture verdict passed",
                        "artifacts": ["docs/Validate_Run_Report.md"],
                    },
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
        "PASS",
        "PASS",
    ]
    assert (root / payload["record_path"]).exists()


def test_validate_postconditions_records_not_run_for_missing_worker_gate(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    init_git_workspace(root)
    run_id = "sup_20260605_000000"
    base_commit = git_head(root)
    write_run_manifest(root, run_id, base_commit)
    (root / "project_map.json").write_text("{}\n", encoding="utf-8")
    (root / "src").mkdir()
    write_roadmap_commit_plan(root)
    (root / "src" / "s1.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit_paths(
        root,
        "feat(slice/S1_data_answer_contract): add records",
        "docs/Implementation_Roadmap.md",
        "project_map.json",
        "src/s1.py",
    )
    result_path = root / ".workflow_supervisor" / "worker_result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
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

    assert code == workflow_ctl.EXIT_INVALID_INPUT
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    gate_results = [gate["result"] for gate in result["gate_ledger"]]
    assert gate_results[0] == "PASS"
    assert "NOT_RUN" in gate_results


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
