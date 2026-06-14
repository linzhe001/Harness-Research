from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "workflow_supervisor" / "scripts"))

import workflow_ctl  # noqa: E402


def init_git_workspace(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Harness Test"],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test: initial supervisor fixture"],
        cwd=root,
        check=True,
        capture_output=True,
    )


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
    (root / "docs").mkdir()
    (root / "docs" / "Baseline_Report.md").write_text(
        "# Baseline\n",
        encoding="utf-8",
    )
    init_git_workspace(root)
    return root


def write_fixture_worker(tmp_path: Path) -> Path:
    script = tmp_path / "fixture_build_worker.py"
    script.write_text(
        r'''
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ARTIFACTS = {
    "build_refine_arch": ["docs/Technical_Spec.md"],
    "build_plan": [
        "docs/Implementation_Roadmap.md",
        "project_map.json",
        "docs/20_facts/Codebase_Map.md",
    ],
    "build_code_expert": [
        "project_map.json",
        "docs/20_facts/Codebase_Map.md",
    ],
    "build_code_debug": [
        "project_map.json",
        "docs/20_facts/Codebase_Map.md",
    ],
    "build_validate_run": [
        "docs/Validate_Run_Report.md",
        "docs/30_evidence/Validation_Table.md",
    ],
}

SKILLS = {
    "build_refine_arch": "refine-arch",
    "build_plan": "build-plan",
    "build_code_expert": "code-expert",
    "build_code_debug": "code-debug",
    "build_validate_run": "validate-run",
}


def git_commit(root: Path, message: str, paths: list[str]) -> str:
    subprocess.run(["git", "add", *paths], cwd=root, check=True)
    status = subprocess.run(
        ["git", "status", "--short", "--", *paths],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if not status.stdout.strip():
        return ""
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_roadmap(root: Path) -> None:
    target = root / "docs/Implementation_Roadmap.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
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
                (
                    "| `S2_proxy_postprocess` | src/s2.py | py_compile | "
                    "`feat(slice/S2_proxy_postprocess): add metrics` | slice |"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_artifact(root: Path, path: str, node_id: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if path == "docs/Implementation_Roadmap.md":
        write_roadmap(root)
    elif target.suffix == ".json":
        target.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "detail_policy": {},
                    "structure": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        target.write_text(f"# {node_id}\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    root = Path(args.workspace_root)
    artifacts = ARTIFACTS[args.node_id]
    for artifact in artifacts:
        write_artifact(root, artifact, args.node_id)

    gates = []
    commit_refs = []
    if args.node_id in {"build_code_expert", "build_code_debug"}:
        if args.node_id == "build_code_expert":
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src/s1.py").write_text("VALUE = 1\n", encoding="utf-8")
            commit_refs.append(
                git_commit(
                    root,
                    "feat(slice/S1_data_answer_contract): add records",
                    [
                        "project_map.json",
                        "docs/20_facts/Codebase_Map.md",
                        "src/s1.py",
                    ],
                )
            )
            (root / "src/s2.py").write_text("VALUE = 2\n", encoding="utf-8")
            commit_refs.append(
                git_commit(
                    root,
                    "feat(slice/S2_proxy_postprocess): add metrics",
                    ["src/s2.py"],
                )
            )
            artifacts = [*artifacts, "src/s1.py", "src/s2.py"]
        else:
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src/debug_fix.py").write_text("VALUE = 3\n", encoding="utf-8")
            commit_refs.append(
                git_commit(
                    root,
                    "fix(build): debug validation fixture",
                    [
                        "project_map.json",
                        "docs/20_facts/Codebase_Map.md",
                        "src/debug_fix.py",
                    ],
                )
            )
        gates.append(
            {
                "command": (
                    "python tooling/evidence/compile_doc.py --workspace-root . "
                    "--doc docs/20_facts/Codebase_Map.md --source project_map.json"
                ),
                "result": "PASS",
                "reason": "fixture docchain gate",
                "artifacts": [".evidence/chains/codebase_map/evidence_chain.json"],
            }
        )
        gates.append(
            {
                "command": "roadmap implementation completeness",
                "result": "PASS",
                "reason": "fixture roadmap slices committed",
                "artifacts": [ref for ref in commit_refs if ref],
            }
        )
    elif args.node_id == "build_refine_arch":
        commit_refs.append(
            git_commit(root, "docs(build): add WF6 technical spec", artifacts)
        )
    elif args.node_id == "build_plan":
        commit_refs.append(
            git_commit(root, "docs(build): add WF7 implementation roadmap", artifacts)
        )
    if args.node_id == "build_validate_run":
        commit_refs.append(
            git_commit(root, "docs(build): record validate run report", artifacts)
        )
        gates.append(
            {
                "command": (
                    "python tooling/evidence/check_dynamic_context.py "
                    "--workspace-root . --stage wf10 --review-packet"
                ),
                "result": "PASS",
                "reason": "fixture wf10 dynamic context gate",
                "artifacts": [".evidence/review_packets/wf10/build/review_packet.md"],
            }
        )
        gates.append(
            {
                "command": "validate-run verdict",
                "result": "PASS",
                "reason": "fixture validation passed",
                "artifacts": [*artifacts, *[ref for ref in commit_refs if ref]],
            }
        )

    now = datetime.now(timezone.utc).isoformat()
    result = {
        "schema_version": 1,
        "run_id": args.run_id,
        "node_id": args.node_id,
        "skill": SKILLS[args.node_id],
        "attempt": 1,
        "status": "success",
        "exit_code": 0,
        "started_at": now,
        "finished_at": now,
        "summary": f"fixture {args.node_id}",
        "artifact_refs": artifacts,
        "gate_ledger": gates,
        "postcondition_claims": [],
        "interrupt_request": None,
        "observed_writes": artifacts,
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


def write_recovery_fixture_worker(tmp_path: Path) -> Path:
    script = tmp_path / "fixture_recovery_worker.py"
    script.write_text(
        r'''
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SKILLS = {
    "build_refine_arch": "refine-arch",
    "build_plan": "build-plan",
    "build_code_expert": "code-expert",
    "build_code_debug": "code-debug",
    "build_validate_run": "validate-run",
}


def git_commit(root: Path, message: str, paths: list[str]) -> str:
    subprocess.run(["git", "add", *paths], cwd=root, check=True)
    status = subprocess.run(
        ["git", "status", "--short", "--", *paths],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if not status.stdout.strip():
        return ""
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_text(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def write_roadmap(root: Path) -> None:
    write_text(
        root,
        "docs/Implementation_Roadmap.md",
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
                (
                    "| `S2_proxy_postprocess` | src/s2.py | py_compile | "
                    "`feat(slice/S2_proxy_postprocess): add metrics` | slice |"
                ),
            ]
        )
        + "\n",
    )


def write_project_map(root: Path) -> None:
    (root / "project_map.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "detail_policy": {},
                "structure": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_text(root, "docs/20_facts/Codebase_Map.md", "# Codebase\n")


def result_payload(args: argparse.Namespace, *, status: str, artifacts, gates, writes):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 1,
        "run_id": args.run_id,
        "node_id": args.node_id,
        "skill": SKILLS[args.node_id],
        "attempt": 1,
        "status": status,
        "exit_code": 0 if status == "success" else 1,
        "started_at": now,
        "finished_at": now,
        "summary": f"fixture {args.node_id} {status}",
        "artifact_refs": list(artifacts),
        "gate_ledger": list(gates),
        "postcondition_claims": [],
        "interrupt_request": None,
        "observed_writes": list(writes),
        "stdout_ref": None,
        "stderr_ref": None,
        "contract_violations": [],
        "worker_warnings": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    root = Path(args.workspace_root)
    gates = []
    artifacts = []
    writes = []
    status = "success"
    marker = root / ".workflow_supervisor" / "fixture_recovery_debug_ran"

    if args.node_id == "build_refine_arch":
        artifacts = ["docs/Technical_Spec.md"]
        writes = artifacts
        write_text(root, "docs/Technical_Spec.md", "# Spec\n")
        commit_ref = git_commit(root, "docs(build): add WF6 technical spec", writes)
        gates.append(
            {
                "command": "semantic git commit build_refine_arch",
                "result": "PASS",
                "reason": "fixture build_refine_arch committed",
                "artifacts": [commit_ref] if commit_ref else [],
            }
        )
    elif args.node_id == "build_plan":
        write_roadmap(root)
        write_project_map(root)
        artifacts = ["docs/Implementation_Roadmap.md", "project_map.json"]
        writes = [*artifacts, "docs/20_facts/Codebase_Map.md"]
        commit_ref = git_commit(
            root,
            "docs(build): add WF7 implementation roadmap",
            writes,
        )
        gates.append(
            {
                "command": "semantic git commit build_plan",
                "result": "PASS",
                "reason": "fixture build_plan committed",
                "artifacts": [commit_ref] if commit_ref else [],
            }
        )
    elif args.node_id == "build_code_expert":
        write_project_map(root)
        (root / "src").mkdir(parents=True, exist_ok=True)
        write_text(root, "src/s1.py", "VALUE = 1\n")
        commit_s1 = git_commit(
            root,
            "feat(slice/S1_data_answer_contract): add records",
            ["project_map.json", "docs/20_facts/Codebase_Map.md", "src/s1.py"],
        )
        write_text(root, "src/s2.py", "VALUE = 2\n")
        commit_s2 = git_commit(
            root,
            "feat(slice/S2_proxy_postprocess): add metrics",
            ["src/s2.py"],
        )
        artifacts = [
            "project_map.json",
            "docs/20_facts/Codebase_Map.md",
            "src/s1.py",
            "src/s2.py",
        ]
        writes = artifacts
        gates.append(
            {
                "command": (
                    "python tooling/evidence/compile_doc.py --workspace-root . "
                    "--doc docs/20_facts/Codebase_Map.md --source project_map.json"
                ),
                "result": "PASS",
                "reason": "fixture docchain",
                "artifacts": [".evidence/chains/codebase_map/evidence_chain.json"],
            }
        )
        gates.append(
            {
                "command": "roadmap implementation completeness",
                "result": "PASS",
                "reason": "fixture roadmap slices committed",
                "artifacts": [commit_s1, commit_s2],
            }
        )
    elif args.node_id == "build_validate_run" and not marker.exists():
        status = "failed"
        artifacts = []
        writes = []
        gates.append(
            {
                "command": "project smoke",
                "result": "FAIL",
                "reason": "fixture validation failure before debug",
                "artifacts": [],
            }
        )
    elif args.node_id == "build_code_debug":
        marker.write_text("debugged\n", encoding="utf-8")
        write_project_map(root)
        (root / "src").mkdir(parents=True, exist_ok=True)
        write_text(root, "src/debug_fix.py", "VALUE = 3\n")
        commit_ref = git_commit(
            root,
            "fix(build): debug validation fixture",
            ["project_map.json", "docs/20_facts/Codebase_Map.md", "src/debug_fix.py"],
        )
        artifacts = [
            "project_map.json",
            "docs/20_facts/Codebase_Map.md",
            "src/debug_fix.py",
        ]
        writes = artifacts
        gates.append(
            {
                "command": (
                    "python tooling/evidence/compile_doc.py --workspace-root . "
                    "--doc docs/20_facts/Codebase_Map.md --source project_map.json"
                ),
                "result": "PASS",
                "reason": "fixture debug docchain",
                "artifacts": [".evidence/chains/codebase_map/evidence_chain.json"],
            }
        )
        gates.append(
            {
                "command": "roadmap implementation completeness",
                "result": "PASS",
                "reason": "fixture debug committed",
                "artifacts": [commit_ref] if commit_ref else [],
            }
        )
    elif args.node_id == "build_validate_run":
        artifacts = [
            "docs/Validate_Run_Report.md",
            "docs/30_evidence/Validation_Table.md",
        ]
        writes = artifacts
        write_text(root, "docs/Validate_Run_Report.md", "# Validate\n")
        write_text(root, "docs/30_evidence/Validation_Table.md", "# Validation\n")
        commit_ref = git_commit(
            root,
            "docs(build): record validate run report",
            writes,
        )
        gates.append(
            {
                "command": (
                    "python tooling/evidence/check_dynamic_context.py "
                    "--workspace-root . --stage wf10 --review-packet"
                ),
                "result": "PASS",
                "reason": "fixture wf10 gate after debug",
                "artifacts": [".evidence/review_packets/wf10/build/review_packet.md"],
            }
        )
        gates.append(
            {
                "command": "validate-run verdict",
                "result": "PASS",
                "reason": "fixture validation passed",
                "artifacts": [*artifacts, commit_ref],
            }
        )

    payload = result_payload(
        args,
        status=status,
        artifacts=artifacts,
        gates=gates,
        writes=writes,
    )
    Path(args.result).write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''.lstrip(),
        encoding="utf-8",
    )
    return script


def test_build_runs_all_nodes_until_ready_for_iterate(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    worker = write_fixture_worker(tmp_path)
    command = (
        f"{sys.executable} {worker} --workspace-root {{workspace_root}} "
        "--run-id {run_id} --node-id {node_id} --result {result_path}"
    )

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "build",
            "--goal",
            "build until runnable",
            "--worker-command",
            command,
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    assert state["status"] == "completed"
    assert state["segment_status"] == "build_ready_for_iterate"
    assert state["completed_nodes"] == [
        "build_refine_arch",
        "build_plan",
        "build_code_expert",
        "build_validate_run",
    ]
    run_id = state["active_run_id"]
    assert (
        root
        / ".workflow_supervisor"
        / "runs"
        / run_id
        / "node_runs"
        / "build_validate_run.json"
    ).exists()
    assert (root / "docs" / "Validate_Run_Report.md").exists()


def test_build_runs_code_debug_only_after_failure(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    worker = write_recovery_fixture_worker(tmp_path)
    command = (
        f"{sys.executable} {worker} --workspace-root {{workspace_root}} "
        "--run-id {run_id} --node-id {node_id} --result {result_path}"
    )

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "build",
            "--goal",
            "build with one validation failure",
            "--worker-command",
            command,
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    assert state["status"] == "completed"
    assert state["completed_nodes"] == [
        "build_refine_arch",
        "build_plan",
        "build_code_expert",
        "build_code_debug",
        "build_validate_run",
    ]
    run_id = state["active_run_id"]
    assert (
        root
        / ".workflow_supervisor"
        / "runs"
        / run_id
        / "node_runs"
        / "build_code_debug.json"
    ).exists()
    archive_dir = (
        root
        / ".workflow_supervisor"
        / "runs"
        / run_id
        / "attempts"
        / "build_validate_run"
        / "attempt_1"
    )
    archive_manifest = json.loads(
        (archive_dir / "archive_manifest.json").read_text(encoding="utf-8")
    )
    assert archive_manifest["reason"] == "node_postcondition_failed"
    archived_node = json.loads(
        (archive_dir / "node_record.json").read_text(encoding="utf-8")
    )
    current_node = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "node_runs"
            / "build_validate_run.json"
        ).read_text(encoding="utf-8")
    )
    assert archived_node["status"] == "failed"
    assert current_node["status"] == "success"
    assert (root / "docs" / "Validate_Run_Report.md").exists()


def test_prepare_complete_acquires_dataset_and_baseline(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "# Readiness\n",
        encoding="utf-8",
    )
    dataset_source = tmp_path / "dataset_source"
    dataset_source.mkdir()
    (dataset_source / "sample.txt").write_text("data\n", encoding="utf-8")
    dataset_target = root / "data" / "primary"
    dataset_target.mkdir(parents=True)
    baseline_source = tmp_path / "baseline_source"
    baseline_source.mkdir()
    (baseline_source / "train.py").write_text("print('baseline')\n", encoding="utf-8")

    def fake_protocol(workspace_root: Path, *, build_id: str) -> dict[str, object]:
        return {
            "command": "fake compile_protocol.py",
            "exit_code": 0,
            "stdout": {
                "output_root": f".evidence/protocol_compiler/{build_id}",
                "actions": [
                    {
                        "path": (
                            f".evidence/protocol_compiler/{build_id}/"
                            "docs/35_protocol/Research_Protocol.md"
                        )
                    }
                ],
            },
            "stdout_text": "{}",
            "stderr": "",
        }

    def fake_gate(
        workspace_root: Path,
        *,
        stage: str,
        build_id: str,
        write_review_packet: bool,
    ) -> dict[str, object]:
        packet_dir = (
            workspace_root
            / ".evidence"
            / "review_packets"
            / stage
            / build_id
        )
        packet_dir.mkdir(parents=True)
        markdown = packet_dir / "review_packet.md"
        payload = packet_dir / "review_packet.json"
        markdown.write_text("# Review\n", encoding="utf-8")
        payload.write_text("{}\n", encoding="utf-8")
        return {
            "command": "fake check_dynamic_context.py",
            "exit_code": 0,
            "stdout": {
                "review_packet": {
                    "markdown_path": markdown.relative_to(workspace_root).as_posix(),
                    "json_path": payload.relative_to(workspace_root).as_posix(),
                    "output_dir": packet_dir.relative_to(workspace_root).as_posix(),
                }
            },
            "stderr": "",
        }

    monkeypatch.setattr(workflow_ctl, "run_protocol_compiler", fake_protocol)
    monkeypatch.setattr(workflow_ctl, "run_dynamic_context_gate", fake_gate)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "prepare",
            "--goal",
            "prepare with local data and baseline",
            "--complete",
            "--dataset-source",
            str(dataset_source),
            "--dataset-target",
            "data/primary",
            "--baseline-repo",
            str(baseline_source),
            "--baseline-target",
            "baselines",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["status"] == "completed"
    assert state["segment_status"] == "prepare_complete"
    assert "prepare_data_prep" in state["completed_nodes"]
    assert "prepare_baseline_repro" in state["completed_nodes"]
    assert not (root / ".workflow_supervisor" / "pending_request.json").exists()
    assert (root / "data" / "primary" / "sample.txt").exists()
    assert (root / "baselines" / "baseline_source" / "train.py").exists()
    assert (root / "docs" / "Dataset_Stats.md").exists()
    assert (root / "docs" / "Baseline_Report.md").exists()
    dataset_manifest = json.loads(
        (root / "data" / "dataset_manifest.json").read_text(encoding="utf-8")
    )
    baseline_manifest = json.loads(
        (root / "baselines" / "baseline_manifest.json").read_text(encoding="utf-8")
    )
    run_manifest = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "run_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert run_manifest["policy"]["gate_profile"] == "automation_prepare"
    assert run_manifest["policy"]["gate_policy_ref"] == (
        "tooling/workflow_supervisor/config/gate_policy.yaml"
    )
    acquisition_plan = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "runtime"
            / "acquisition_plan.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["acquisition_plan_ref"] == (
        f".workflow_supervisor/runs/{run_id}/runtime/acquisition_plan.json"
    )
    assert "prepare_acquisition_plan" in state["completed_nodes"]
    assert acquisition_plan["kind"] == "prepare_acquisition_plan"
    assert acquisition_plan["policy"]["blocked_remote_sources"] == []
    assert (
        workflow_ctl.validate_schema(
            root,
            acquisition_plan,
            "acquisition_plan.schema.json",
            "acquisition_plan",
        )
        == []
    )
    assert dataset_manifest["kind"] == "dataset_acquisition"
    assert dataset_manifest["dataset_root"] == "data/primary"
    assert dataset_manifest["verification"]["result"] == "PASS"
    assert (
        workflow_ctl.validate_schema(
            root,
            dataset_manifest,
            "dataset_acquisition_manifest.schema.json",
            "dataset_manifest",
        )
        == []
    )
    assert baseline_manifest["kind"] == "baseline_acquisition"
    assert baseline_manifest["baseline_root"] == "baselines"
    assert str(baseline_source) in baseline_manifest["repos"]
    assert "baseline_source" in baseline_manifest["baselines"]
    assert (
        workflow_ctl.validate_schema(
            root,
            baseline_manifest,
            "baseline_acquisition_manifest.schema.json",
            "baseline_manifest",
        )
        == []
    )


def test_prepare_complete_blocks_unapproved_remote_sources_at_plan(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
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
            "prepare with remote inputs",
            "--complete",
            "--dataset-source",
            "https://example.com/dataset.zip",
            "--dataset-target",
            "data/remote",
            "--baseline-repo",
            "https://github.com/example/baseline",
            "--baseline-target",
            "baselines",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    run_id = state["active_run_id"]
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    plan_ref = f".workflow_supervisor/runs/{run_id}/runtime/acquisition_plan.json"
    plan = json.loads((root / plan_ref).read_text(encoding="utf-8"))
    assert state["segment_status"] == "acquisition_policy_approval_required"
    assert state["current_node_id"] == "prepare_acquisition_plan"
    assert payload["blocked_by"] == "acquisition_policy_approval_required"
    assert payload["acquisition_plan_ref"] == plan_ref
    assert pending["node_id"] == "prepare_acquisition_plan"
    assert pending["reason"] == "acquisition_policy_approval_required"
    assert set(plan["policy"]["blocked_remote_sources"]) == {
        "https://example.com/dataset.zip",
        "https://github.com/example/baseline",
    }
    assert len(plan["blockers"]) == 2
    assert not (root / "data" / "dataset_manifest.json").exists()
    assert not (root / "baselines" / "baseline_manifest.json").exists()
    assert (
        workflow_ctl.validate_schema(
            root,
            plan,
            "acquisition_plan.schema.json",
            "acquisition_plan",
        )
        == []
    )


def test_resume_acquisition_plan_with_local_answer_overrides_remote_bridge(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "# Readiness\n",
        encoding="utf-8",
    )
    dataset_source = tmp_path / "answered_dataset"
    dataset_source.mkdir()
    (dataset_source / "sample.txt").write_text("data\n", encoding="utf-8")
    baseline_source = tmp_path / "answered_baseline"
    baseline_source.mkdir()
    (baseline_source / "train.py").write_text("print('baseline')\n", encoding="utf-8")

    def fake_protocol(workspace_root: Path, *, build_id: str) -> dict[str, object]:
        return {
            "command": "fake compile_protocol.py",
            "exit_code": 0,
            "stdout": {
                "output_root": f".evidence/protocol_compiler/{build_id}",
                "actions": [
                    {
                        "path": (
                            f".evidence/protocol_compiler/{build_id}/"
                            "docs/35_protocol/Research_Protocol.md"
                        )
                    }
                ],
            },
            "stdout_text": "{}",
            "stderr": "",
        }

    def fake_gate(
        workspace_root: Path,
        *,
        stage: str,
        build_id: str,
        write_review_packet: bool,
    ) -> dict[str, object]:
        packet_dir = (
            workspace_root
            / ".evidence"
            / "review_packets"
            / stage
            / build_id
        )
        packet_dir.mkdir(parents=True)
        markdown = packet_dir / "review_packet.md"
        payload = packet_dir / "review_packet.json"
        markdown.write_text("# Review\n", encoding="utf-8")
        payload.write_text("{}\n", encoding="utf-8")
        return {
            "command": "fake check_dynamic_context.py",
            "exit_code": 0,
            "stdout": {
                "review_packet": {
                    "markdown_path": markdown.relative_to(workspace_root).as_posix(),
                    "json_path": payload.relative_to(workspace_root).as_posix(),
                    "output_dir": packet_dir.relative_to(workspace_root).as_posix(),
                }
            },
            "stderr": "",
        }

    monkeypatch.setattr(workflow_ctl, "run_protocol_compiler", fake_protocol)
    monkeypatch.setattr(workflow_ctl, "run_dynamic_context_gate", fake_gate)

    start_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "prepare",
            "--goal",
            "prepare with remote inputs",
            "--complete",
            "--dataset-source",
            "https://example.com/dataset.zip",
            "--dataset-target",
            "data/remote",
            "--baseline-repo",
            "https://github.com/example/baseline",
            "--baseline-target",
            "baselines",
            "--json",
        ]
    )
    assert start_code == workflow_ctl.EXIT_MANUAL_ACTION
    start_payload = json.loads(capsys.readouterr().out)
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert start_payload["state"]["segment_status"] == (
        "acquisition_policy_approval_required"
    )

    answer_path = tmp_path / "local_acquisition_answer.json"
    answer_path.write_text(
        json.dumps(
            {
                "request_id": pending["request_id"],
                "request_snapshot_hash": pending["request_snapshot_hash"],
                "idempotency_key": "local-acquisition-answer",
                "answered_by": "Test Operator",
                "answered_at": "2026-06-07T00:00:00Z",
                "answers": {
                    "decision": "provide_local_path",
                    "dataset_source": str(dataset_source),
                    "dataset_target": "data/answered",
                    "baseline_repo": str(baseline_source),
                    "baseline_target": "baselines",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        workflow_ctl.main(
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
        == workflow_ctl.EXIT_OK
    )
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
    state = payload["state"]
    run_id = state["active_run_id"]
    plan = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "runtime"
            / "acquisition_plan.json"
        ).read_text(encoding="utf-8")
    )
    assert state["segment_status"] == "prepare_complete"
    assert plan["policy"]["blocked_remote_sources"] == []
    assert plan["dataset"]["entries"][0]["source"] == str(dataset_source)
    assert [item["source"] for item in plan["baselines"]["repos"]] == [
        str(baseline_source)
    ]
    assert (root / "data" / "answered" / "sample.txt").exists()
    assert (root / "baselines" / "answered_baseline" / "train.py").exists()


def test_recover_auto_resume_answered_prepare_dataset_request(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "# Readiness\n",
        encoding="utf-8",
    )
    dataset_target = root / "data" / "answered"
    dataset_target.mkdir(parents=True)
    (dataset_target / "sample.txt").write_text("data\n", encoding="utf-8")
    baseline_target = root / "baselines" / "local_baseline"
    baseline_target.mkdir(parents=True)
    (baseline_target / "train.py").write_text(
        "print('baseline')\n",
        encoding="utf-8",
    )

    def fake_protocol(workspace_root: Path, *, build_id: str) -> dict[str, object]:
        return {
            "command": "fake compile_protocol.py",
            "exit_code": 0,
            "stdout": {
                "output_root": f".evidence/protocol_compiler/{build_id}",
                "actions": [
                    {
                        "path": (
                            f".evidence/protocol_compiler/{build_id}/"
                            "docs/35_protocol/Research_Protocol.md"
                        )
                    }
                ],
            },
            "stdout_text": "{}",
            "stderr": "",
        }

    def fake_gate(
        workspace_root: Path,
        *,
        stage: str,
        build_id: str,
        write_review_packet: bool,
    ) -> dict[str, object]:
        packet_dir = (
            workspace_root
            / ".evidence"
            / "review_packets"
            / stage
            / build_id
        )
        packet_dir.mkdir(parents=True)
        markdown = packet_dir / "review_packet.md"
        payload = packet_dir / "review_packet.json"
        markdown.write_text("# Review\n", encoding="utf-8")
        payload.write_text("{}\n", encoding="utf-8")
        return {
            "command": "fake check_dynamic_context.py",
            "exit_code": 0,
            "stdout": {
                "review_packet": {
                    "markdown_path": markdown.relative_to(workspace_root).as_posix(),
                    "json_path": payload.relative_to(workspace_root).as_posix(),
                    "output_dir": packet_dir.relative_to(workspace_root).as_posix(),
                }
            },
            "stderr": "",
        }

    monkeypatch.setattr(workflow_ctl, "run_protocol_compiler", fake_protocol)
    monkeypatch.setattr(workflow_ctl, "run_dynamic_context_gate", fake_gate)

    start_code = workflow_ctl.main(
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
    assert start_code == workflow_ctl.EXIT_MANUAL_ACTION
    start_payload = json.loads(capsys.readouterr().out)
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert start_payload["state"]["segment_status"] == "dataset_input_required"
    assert pending["reason"] == "dataset_input_required"

    answer_path = tmp_path / "dataset_answer.json"
    answer_path.write_text(
        json.dumps(
            {
                "request_id": pending["request_id"],
                "request_snapshot_hash": pending["request_snapshot_hash"],
                "idempotency_key": "dataset-answer",
                "answered_by": "Test Operator",
                "answered_at": "2026-06-07T00:00:00Z",
                "answers": {
                    "decision": "provide_dataset_path",
                    "dataset_target": "data/answered",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        workflow_ctl.main(
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
        == workflow_ctl.EXIT_OK
    )
    capsys.readouterr()

    recover_code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "recover",
            "--repair-stale-running",
            "--auto-resume-answered",
            "--json",
        ]
    )

    assert recover_code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    assert state["segment_status"] == "prepare_complete"
    assert "prepare_data_prep" in state["completed_nodes"]
    assert "prepare_baseline_repro" in state["completed_nodes"]
    assert "prepare_data_prep" not in state["failed_nodes"]
    assert not (root / ".workflow_supervisor" / "pending_request.json").exists()
    assert (root / "docs" / "Dataset_Stats.md").exists()
    assert (root / "docs" / "Baseline_Report.md").exists()
    assert (root / "data" / "dataset_manifest.json").exists()
    assert (root / "baselines" / "baseline_manifest.json").exists()
    events = workflow_ctl.read_events(root)
    assert any(
        event["event"] == "RUN_RESUMED"
        and event["payload"].get("mode") == "rerun_answered_node"
        for event in events
    )


def test_prepare_complete_bridges_grill_readiness_packet(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = make_workspace(tmp_path)
    dataset_source = tmp_path / "grill_dataset_source"
    dataset_source.mkdir()
    (dataset_source / "sample.txt").write_text("data\n", encoding="utf-8")
    baseline_source = tmp_path / "grill_baseline_source"
    baseline_source.mkdir()
    (baseline_source / "train.py").write_text("print('baseline')\n", encoding="utf-8")

    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "\n".join(
            [
                "# Execution Readiness Packet",
                "",
                (
                    "| Input | Redacted Value | Verification Status | "
                    "Verification Command |"
                ),
                "| --- | --- | --- | --- |",
                f"| dataset_source | {dataset_source} | candidate | not run |",
                "| dataset_target | data/from_grill | candidate | not run |",
                f"| baseline_repo | {baseline_source} | candidate | not run |",
                "| baseline_target | baselines/from_grill | candidate | not run |",
                "| external_download_policy | false | candidate | not run |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "docs" / "Research_Intent_Draft.md").write_text(
        "# Research Intent Draft\n",
        encoding="utf-8",
    )
    (root / "docs" / "Grill_Round_Log.md").write_text(
        "# Grill Round Log\n",
        encoding="utf-8",
    )

    def fake_protocol(workspace_root: Path, *, build_id: str) -> dict[str, object]:
        return {
            "command": "fake compile_protocol.py",
            "exit_code": 0,
            "stdout": {
                "output_root": f".evidence/protocol_compiler/{build_id}",
                "actions": [
                    {
                        "path": (
                            f".evidence/protocol_compiler/{build_id}/"
                            "docs/35_protocol/Research_Protocol.md"
                        )
                    }
                ],
            },
            "stdout_text": "{}",
            "stderr": "",
        }

    def fake_gate(
        workspace_root: Path,
        *,
        stage: str,
        build_id: str,
        write_review_packet: bool,
    ) -> dict[str, object]:
        packet_dir = (
            workspace_root
            / ".evidence"
            / "review_packets"
            / stage
            / build_id
        )
        packet_dir.mkdir(parents=True)
        markdown = packet_dir / "review_packet.md"
        payload = packet_dir / "review_packet.json"
        markdown.write_text("# Review\n", encoding="utf-8")
        payload.write_text("{}\n", encoding="utf-8")
        return {
            "command": "fake check_dynamic_context.py",
            "exit_code": 0,
            "stdout": {
                "review_packet": {
                    "markdown_path": markdown.relative_to(workspace_root).as_posix(),
                    "json_path": payload.relative_to(workspace_root).as_posix(),
                    "output_dir": packet_dir.relative_to(workspace_root).as_posix(),
                }
            },
            "stderr": "",
        }

    monkeypatch.setattr(workflow_ctl, "run_protocol_compiler", fake_protocol)
    monkeypatch.setattr(workflow_ctl, "run_dynamic_context_gate", fake_gate)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "prepare",
            "--goal",
            "prepare from grill output",
            "--complete",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["segment_status"] == "prepare_complete"
    bridge = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "runtime"
            / "grill_bridge.json"
        ).read_text(encoding="utf-8")
    )
    assert bridge["values"]["dataset_source"]["value"] == str(dataset_source)
    assert bridge["values"]["baseline_repo"]["value"] == str(baseline_source)
    assert not bridge["unresolved"]
    assert (root / "data" / "from_grill" / "sample.txt").exists()
    assert (
        root
        / "baselines"
        / "from_grill"
        / "grill_baseline_source"
        / "train.py"
    ).exists()
    assert (root / "data" / "dataset_manifest.json").exists()
    assert (root / "baselines" / "baseline_manifest.json").exists()


def test_grill_bridge_uses_readiness_dataset_root_wsl_without_candidate_url(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    dataset_root = tmp_path / "smoke_data"
    dataset_root.mkdir()
    readiness_dir = root / ".workflow_supervisor"
    readiness_dir.mkdir()
    workflow_ctl.atomic_write_json(
        readiness_dir / "readiness.json",
        {
            "schema_version": 1,
            "updated_at": "2026-06-07T08:15:07+08:00",
            "source": "grill",
            "inputs": [
                {
                    "key": "dataset_root_wsl",
                    "kind": "path",
                    "value": str(dataset_root),
                    "redacted_value": "recorded WSL dataset root",
                    "verification_status": "verified",
                    "verified_at": "2026-06-07T08:15:07+08:00",
                    "verification_command": f"test -d {dataset_root}",
                    "notes": "WSL-visible dataset storage root",
                }
            ],
        },
    )
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "\n".join(
            [
                "# Execution Readiness Packet",
                "",
                (
                    "| Input | Redacted Value | Verification Status | "
                    "Verification Command |"
                ),
                "| --- | --- | --- | --- |",
                (
                    "| dataset_root_wsl | Windows F drive dataset root via WSL mount "
                    "| verified | path check through readiness tooling |"
                ),
                "",
                "## Candidate Dataset Manifest",
                "",
                "| Dataset ID | Dataset | Role | Source | Local Status | First Use |",
                "| --- | --- | --- | --- | --- | --- |",
                (
                    "| dataset_selfsvd_lsvd | LSVD / SelfSVD | real pre-smoke "
                    "video desmoking | https://github.com/ZcsrenlongZ/SelfSVD "
                    "| operator-reported unavailable; not local | reference only |"
                ),
                (
                    "| dataset_stsvd | STSVD | video desmoking | "
                    "https://example.com/stsvd | public download candidate "
                    "| future baseline |"
                ),
                "",
                "## Dataset Accessibility Verification",
                "",
                "| Dataset ID | Access Verdict | Action |",
                "| --- | --- | --- |",
                (
                    "| dataset_stsvd | not_publicly_verified | "
                    "Exclude from early subset. |"
                ),
            ]
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        allow_external_downloads=False,
        baseline_repo=[],
        baseline_target=None,
        dataset_source=None,
        dataset_target=None,
    )
    bridge, _bridge_ref = workflow_ctl.build_grill_bridge(
        root,
        run_id="sup_test",
        args=args,
    )

    assert bridge["values"]["dataset_root"]["value"] == str(dataset_root)
    assert "dataset_source" not in bridge["values"]
    assert "baseline_repo" not in bridge["values"]
    assert "https://github.com/ZcsrenlongZ/SelfSVD" not in bridge["policy"][
        "remote_sources"
    ]
    rejected = [
        item
        for item in bridge["dataset_candidates"]
        if item.get("dataset_id") == "dataset_selfsvd_lsvd"
    ]
    assert rejected
    assert rejected[0]["decision"] == "rejected"
    deferred = [
        item
        for item in bridge["dataset_candidates"]
        if item.get("dataset_id") == "dataset_stsvd"
    ]
    assert deferred
    assert deferred[0]["decision"] == "deferred"
    assert "https://example.com/stsvd" not in bridge["policy"]["remote_sources"]
    assert workflow_ctl.dataset_target_from_args(root, args) == dataset_root


def test_grill_bridge_does_not_promote_deferred_table_urls_to_values(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    dataset_root = tmp_path / "smoke_data"
    dataset_root.mkdir()
    readiness_dir = root / ".workflow_supervisor"
    readiness_dir.mkdir()
    workflow_ctl.atomic_write_json(
        readiness_dir / "readiness.json",
        {
            "schema_version": 1,
            "inputs": [
                {
                    "key": "dataset_root_wsl",
                    "kind": "path",
                    "value": str(dataset_root),
                    "redacted_value": "recorded WSL dataset root",
                    "verification_status": "verified",
                    "verification_command": f"test -d {dataset_root}",
                },
            ],
        },
    )
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "\n".join(
            [
                "# Execution Readiness Packet",
                "",
                "| Intent Key | Redacted Policy Or Scope | Status | Notes |",
                "| --- | --- | --- | --- |",
                (
                    "| `hf_access_policy` | Use operator Hugging Face auth "
                    "for RealX3D and SeeThroughSmoke | candidate-clear | "
                    "Source-specific HF allowance only. |"
                ),
                (
                    "| `baseline_clone_policy` | Clone only the first baseline "
                    "set under `baselines/` during prepare | candidate-clear | "
                    "Does not authorize extra 2D/deferred baselines. |"
                ),
                (
                    "| `baseline_clone_scope` | Free-SurGS and Feature 3DGS | "
                    "candidate-clear | First baseline set only. |"
                ),
                "",
                "## Dataset Access Ledger",
                "",
                (
                    "| Dataset ID | Source URL Or Official Entrypoint | "
                    "Access Verdict | Non-Destructive Download Probe Result | "
                    "Execution Decision | Notes |"
                ),
                "| --- | --- | --- | --- | --- | --- |",
                (
                    "| `dataset_realx3d` | "
                    "https://huggingface.co/datasets/ToferFish/RealX3D | "
                    "`hf_page_reachable_not_verified_local` | HTTP 200 | "
                    "`candidate` | Future required HF download/check item. |"
                ),
                (
                    "| `dataset_see_through_smoke` | "
                    "https://huggingface.co/datasets/artJiang20/SeeThroughSmoke | "
                    "`hf_auth_accepted_not_local` | HTTP 200 | "
                    "`candidate` | Use operator HF auth only. |"
                ),
                (
                    "| `dataset_selfsvd_lsvd` | "
                    "https://github.com/ZcsrenlongZ/SelfSVD | "
                    "`operator_reported_unavailable` + `baidu_request_gated` | "
                    "Not reprobed. | `deferred` | Method reference only; "
                    "do not download in early plan. |"
                ),
                (
                    "| `dataset_desmoke_lap` | "
                    "https://github.com/yiroup20/DeSmoke-LAP | "
                    "`not_active_after_round16` | Not reprobed. | "
                    "`deferred` | Keep as baseline context; "
                    "do not download now. |"
                ),
            ]
        ),
        encoding="utf-8",
    )
    (root / "docs" / "Research_Intent_Draft.md").write_text(
        "\n".join(
            [
                "# Research Intent Draft",
                "",
                (
                    "| SfM-free surgical cold start | "
                    "[Free-SurGS](https://papers.miccai.org/miccai-2024/"
                    "341-Paper1818.html), "
                    "[code](https://github.com/wrld/Free-SurGS) | "
                    "baseline support |"
                ),
                (
                    "Clone only first baseline set under `baselines/`: "
                    "Free-SurGS and Feature 3DGS."
                ),
            ]
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        allow_external_downloads=False,
        baseline_repo=[],
        baseline_target=None,
        dataset_source=None,
        dataset_target=None,
    )
    bridge, _bridge_ref = workflow_ctl.build_grill_bridge(
        root,
        run_id="sup_test",
        args=args,
    )

    assert "dataset_source" not in bridge["values"]
    assert (
        bridge["values"]["baseline_repo"]["value"]
        == "https://github.com/wrld/Free-SurGS"
    )
    remote_sources = bridge["policy"]["remote_sources"]
    assert "https://huggingface.co/datasets/ToferFish/RealX3D" in remote_sources
    assert (
        "https://huggingface.co/datasets/artJiang20/SeeThroughSmoke"
        in remote_sources
    )
    assert "https://github.com/wrld/Free-SurGS" in remote_sources
    assert "https://github.com/ZcsrenlongZ/SelfSVD" not in remote_sources
    assert "https://github.com/yiroup20/DeSmoke-LAP" not in remote_sources
    assert bridge["unresolved"] == []


def test_grill_bridge_uses_executable_baseline_source_ledger(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "\n".join(
            [
                "# Execution Readiness Packet",
                "",
                "| Intent Key | Redacted Policy Or Scope | Status | Notes |",
                "| --- | --- | --- | --- |",
                (
                    "| `baseline_clone_scope` | Free-SurGS and Feature 3DGS | "
                    "candidate-clear | First baseline set only. |"
                ),
                "",
                "## Baseline Source Ledger",
                "",
                (
                    "| Baseline ID | Role | Code Repository Or Entrypoint | "
                    "Repo Probe | Execution Decision | Notes |"
                ),
                "| --- | --- | --- | --- | --- | --- |",
                (
                    "| `baseline_free_surgs` | SfM-free cold start | "
                    "https://github.com/wrld/Free-SurGS | HEAD not run | "
                    "`candidate` | First baseline set. |"
                ),
                (
                    "| `baseline_selfsvd` | 2D video desmoking reference | "
                    "https://github.com/ZcsrenlongZ/SelfSVD | not run | "
                    "`deferred` | Data access separately required. |"
                ),
                (
                    "| `baseline_mars_gan` | reported method | pending | "
                    "not run | baseline_repo_missing | no code repo found. |"
                ),
            ]
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        allow_external_downloads=False,
        baseline_repo=[],
        baseline_target=None,
        dataset_source=None,
        dataset_target=None,
    )

    bridge, _bridge_ref = workflow_ctl.build_grill_bridge(
        root,
        run_id="sup_test",
        args=args,
    )
    setattr(args, "_grill_bridge", bridge)

    assert (
        bridge["values"]["baseline_repo"]["value"]
        == "https://github.com/wrld/Free-SurGS"
    )
    candidates = bridge["baseline_candidates"]
    assert [
        item["source"]
        for item in candidates
        if item.get("decision") == "candidate"
    ] == ["https://github.com/wrld/Free-SurGS"]
    assert "https://github.com/ZcsrenlongZ/SelfSVD" not in bridge["policy"][
        "remote_sources"
    ]
    assert workflow_ctl.baseline_repos_from_args(root, args) == [
        "https://github.com/wrld/Free-SurGS"
    ]


def test_grill_bridge_uses_structured_readiness_approvals(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    readiness_dir = root / ".workflow_supervisor"
    readiness_dir.mkdir()
    (readiness_dir / "readiness.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-06-07T00:00:00Z",
                "source": "grill",
                "external_download_policy": "allow_if_approved",
                "approved_datasets": [
                    {
                        "id": "realx3d",
                        "source": "https://huggingface.co/datasets/example/realx3d",
                        "target": "data/realx3d",
                        "license": "unknown",
                        "max_size_gb": 50,
                        "access_status": "approved",
                        "source_ref": "operator input",
                        "notes": "operator selected baseline dataset",
                    }
                ],
                "approved_baselines": [
                    {
                        "id": "free_surgs",
                        "repo": "https://github.com/example/Free-SurGS",
                        "ref": "main",
                        "target": "baselines/Free-SurGS",
                        "access_status": "approved",
                        "role": "baseline",
                        "source_ref": "operator input",
                        "notes": "operator selected first baseline",
                    }
                ],
                "target_paths": {
                    "dataset_root": "data",
                    "baseline_cache": "baselines",
                },
                "unknowns": [],
                "operator_approved_at": "2026-06-07T00:00:00Z",
                "inputs": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        allow_external_downloads=False,
        baseline_repo=[],
        baseline_target=None,
        dataset_source=None,
        dataset_target=None,
    )

    bridge, _bridge_ref = workflow_ctl.build_grill_bridge(
        root,
        run_id="sup_test",
        args=args,
    )

    assert bridge["values"]["external_download_policy"]["value"] == (
        "allow_if_approved"
    )
    assert bridge["values"]["dataset_root"]["value"] == "data"
    assert bridge["values"]["baseline_cache"]["value"] == "baselines"
    assert bridge["dataset_candidates"][0]["source"] == (
        "https://huggingface.co/datasets/example/realx3d"
    )
    assert bridge["baseline_candidates"][0]["source"] == (
        "https://github.com/example/Free-SurGS"
    )
    assert bridge["policy"]["allowed_remote_sources"] == [
        "https://huggingface.co/datasets/example/realx3d",
        "https://github.com/example/Free-SurGS",
    ]
    assert bridge["unresolved"] == []


def test_grill_bridge_uses_source_specific_hf_and_baseline_clone_policy(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "\n".join(
            [
                "# Execution Readiness Packet",
                "",
                (
                    "| Input | Redacted Value | Verification Status | "
                    "Verification Command |"
                ),
                "| --- | --- | --- | --- |",
                (
                    "| hf_access_policy | Use operator HF auth for RealX3D "
                    "and SeeThroughSmoke | candidate-clear | operator input |"
                ),
                "| dataset_target | data/from_grill | candidate | not run |",
                (
                    "| baseline_repo | https://github.com/wrld/Free-SurGS "
                    "| candidate | not run |"
                ),
                "| baseline_target | baselines/from_grill | candidate | not run |",
                "",
                "## Dataset Access Ledger",
                "",
                (
                    "| Dataset ID | Source URL Or Official Entrypoint | Access "
                    "Verdict | Non-Destructive Download Probe Result | "
                    "Execution Decision | Notes |"
                ),
                "| --- | --- | --- | --- | --- | --- |",
                (
                    "| dataset_realx3d | "
                    "https://huggingface.co/datasets/ToferFish/RealX3D "
                    "| hf_page_reachable_not_verified_local | HTTP 200 | "
                    "candidate | Future required HF download/check item. |"
                ),
                (
                    "| dataset_selfsvd_lsvd | "
                    "https://github.com/ZcsrenlongZ/SelfSVD | "
                    "operator_reported_unavailable | not reprobed | "
                    "deferred | Method reference only. |"
                ),
                (
                    "| dataset_stereomis | https://zenodo.org/records/7727692 "
                    "| local_probe_verified | local directory exists | "
                    "candidate | Already local; do not download. |"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "docs" / "Research_Intent_Draft.md").write_text(
        "\n".join(
            [
                "# Research Intent Draft",
                "",
                (
                    "8. Clone only first baseline set under `baselines/`: "
                    "Free-SurGS and Feature 3DGS; clone extra 2D baselines "
                    "only after active HF dataset cards clarify the benchmark task."
                ),
                (
                    "| GAN surgical smoke baseline | "
                    "[MARS-GAN](https://doi.org/10.1109/TMI.2023.3245298) | "
                    "reported-method baseline only |"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "docs" / "Grill_Round_Log.md").write_text(
        "# Grill Round Log\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        allow_external_downloads=False,
        baseline_repo=[],
        baseline_target=None,
        dataset_source=None,
        dataset_target=None,
    )

    bridge, _bridge_ref = workflow_ctl.build_grill_bridge(
        root,
        run_id="sup_test",
        args=args,
    )
    setattr(args, "_grill_bridge", bridge)

    policy = bridge["policy"]
    assert policy["allow_external_downloads"] is False
    assert policy["allowed_remote_hosts"] == ["huggingface.co"]
    assert "free_surgs" in policy["allowed_baseline_repo_markers"]
    assert "feature_3dgs" in policy["allowed_baseline_repo_markers"]
    realx3d = [
        item
        for item in bridge["dataset_candidates"]
        if item.get("dataset_id") == "dataset_realx3d"
    ]
    assert realx3d
    assert realx3d[0]["decision"] == "candidate"
    assert (
        realx3d[0]["source"]
        == "https://huggingface.co/datasets/ToferFish/RealX3D"
    )
    assert "https://huggingface.co/datasets/ToferFish/RealX3D" in policy[
        "remote_sources"
    ]
    stereomis = [
        item
        for item in bridge["dataset_candidates"]
        if item.get("dataset_id") == "dataset_stereomis"
    ]
    assert stereomis
    assert stereomis[0]["local_status"] == "local_existing"
    assert stereomis[0]["official_source"] == "https://zenodo.org/records/7727692"
    assert "source" not in stereomis[0]
    assert "https://zenodo.org/records/7727692" not in policy["remote_sources"]
    assert "https://doi.org/10.1109/TMI.2023.3245298" not in policy[
        "remote_sources"
    ]
    assert bridge["unresolved"] == []
    assert workflow_ctl.external_source_allowed(
        args,
        "https://huggingface.co/datasets/ToferFish/RealX3D",
    )
    assert workflow_ctl.external_source_allowed(
        args,
        "https://github.com/wrld/Free-SurGS",
    )
    assert not workflow_ctl.external_source_allowed(
        args,
        "https://github.com/ZcsrenlongZ/SelfSVD",
    )


def test_grill_bridge_does_not_treat_literature_baseline_url_as_repo(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    (root / "docs" / "Execution_Readiness_Packet.md").write_text(
        "\n".join(
            [
                "# Execution Readiness Packet",
                "",
                (
                    "| Input | Redacted Value | Verification Status | "
                    "Verification Command |"
                ),
                "| --- | --- | --- | --- |",
                "| dataset_root | data/from_grill | candidate | not run |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "docs" / "Research_Intent_Draft.md").write_text(
        "\n".join(
            [
                "# Research Intent Draft",
                "",
                (
                    "| GAN surgical smoke baseline | "
                    "[MARS-GAN](https://doi.org/10.1109/TMI.2023.3245298) | "
                    "reported-method baseline only |"
                ),
                (
                    "Clone only first baseline set under `baselines/`: "
                    "Free-SurGS and Feature 3DGS."
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "docs" / "Grill_Round_Log.md").write_text(
        "# Grill Round Log\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        allow_external_downloads=False,
        baseline_repo=[],
        baseline_target=None,
        dataset_source=None,
        dataset_target=None,
    )

    bridge, _bridge_ref = workflow_ctl.build_grill_bridge(
        root,
        run_id="sup_test",
        args=args,
    )

    assert "baseline_repo" not in bridge["values"]
    assert "https://doi.org/10.1109/TMI.2023.3245298" not in bridge["policy"][
        "remote_sources"
    ]
    assert bridge["unresolved"] == [
        "baseline repo or existing baseline cache is not explicit in Grill outputs"
    ]


def test_resume_args_approve_clone_sets_external_download_permission(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    run_id = "sup_test"
    manifest = workflow_ctl.run_manifest(
        workspace_root=root,
        run_id=run_id,
        segment="prepare",
        goal="resume baseline clone",
        entrypoint="harness prepare",
        allow_external_downloads=False,
        complete_prepare=True,
    )
    workflow_ctl.write_run_manifest(root, manifest)
    state = {"active_run_id": run_id}
    answer_record = {
        "answer": {
            "answers": {
                "decision": "approve_clone",
            }
        }
    }

    args = workflow_ctl.resume_args_from_answer(
        root,
        state=state,
        answer_record=answer_record,
        as_json=True,
    )

    assert args.allow_external_downloads is True


def test_data_prep_records_failed_candidate_and_tries_next(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)
    dataset_root = root / "data"
    dataset_root.mkdir()
    local_source = tmp_path / "local_candidate"
    local_source.mkdir()
    (local_source / "sample.txt").write_text("data\n", encoding="utf-8")
    node = {
        "node_id": "prepare_data_prep",
        "skill": "data-prep",
        "timeout_seconds": 120,
    }
    args = argparse.Namespace(
        allow_external_downloads=False,
        dataset_source=None,
        dataset_target=str(dataset_root),
        _grill_bridge={
            "dataset_candidates": [
                {
                    "dataset_id": "dataset_selfsvd_lsvd",
                    "name": "LSVD / SelfSVD",
                    "source": "https://github.com/ZcsrenlongZ/SelfSVD",
                    "decision": "rejected",
                    "reason": "operator_reported_unavailable baidu_request_gated",
                    "source_ref": "docs/Execution_Readiness_Packet.md",
                },
                {
                    "dataset_id": "dataset_missing_remote",
                    "name": "Missing Remote",
                    "source": "https://example.invalid/missing.zip",
                    "decision": "candidate",
                    "reason": "candidate public url",
                    "source_ref": "docs/Execution_Readiness_Packet.md",
                },
                {
                    "dataset_id": "dataset_local_fallback",
                    "name": "Local Fallback",
                    "source": str(local_source),
                    "decision": "candidate",
                    "reason": "verified local fallback",
                    "source_ref": "docs/Execution_Readiness_Packet.md",
                },
            ]
        },
    )

    result = workflow_ctl.run_data_prep_worker(
        root,
        args=args,
        run_id="sup_test",
        node=node,
    )

    assert result["status"] == "success"
    gate_results = [gate["result"] for gate in result["gate_ledger"]]
    assert gate_results[:3] == ["NOT_RUN", "FAIL", "PASS"]
    assert "dataset_selfsvd_lsvd not executable" in result["gate_ledger"][0][
        "reason"
    ]
    assert (
        root / "data" / "local_candidate" / "sample.txt"
    ).read_text(encoding="utf-8") == "data\n"
    assert (root / "docs" / "Dataset_Stats.md").exists()
