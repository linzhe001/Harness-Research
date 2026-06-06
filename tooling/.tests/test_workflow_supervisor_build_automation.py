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
    (root / "docs").mkdir()
    (root / "docs" / "Baseline_Report.md").write_text(
        "# Baseline\n",
        encoding="utf-8",
    )
    return root


def write_fixture_worker(tmp_path: Path) -> Path:
    script = tmp_path / "fixture_build_worker.py"
    script.write_text(
        r'''
from __future__ import annotations

import argparse
import json
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


def write_artifact(root: Path, path: str, node_id: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix == ".json":
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
    if args.node_id in {"build_code_expert", "build_code_debug"}:
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
    if args.node_id == "build_validate_run":
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
        / "build_validate_run.json"
    ).exists()
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

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    assert state["status"] == "paused"
    assert state["segment_status"] == "prepare_waiting_for_approval"
    assert "prepare_data_prep" in state["completed_nodes"]
    assert "prepare_baseline_repro" in state["completed_nodes"]
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["reason"] == "prepare_complete_approval_required"
    assert (root / "data" / "primary" / "sample.txt").exists()
    assert (root / "baselines" / "baseline_source" / "train.py").exists()
    assert (root / "docs" / "Dataset_Stats.md").exists()
    assert (root / "docs" / "Baseline_Report.md").exists()


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

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["segment_status"] == "prepare_waiting_for_approval"
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
