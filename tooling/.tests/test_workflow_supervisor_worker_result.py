from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "workflow_supervisor" / "scripts"))

import workflow_ctl  # noqa: E402


def valid_worker_result() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "sup_20260605_000000",
        "node_id": "wf7_build_plan",
        "skill": "build-plan",
        "attempt": 1,
        "status": "success",
        "exit_code": 0,
        "started_at": "2026-06-05T00:00:00Z",
        "finished_at": "2026-06-05T00:01:00Z",
        "summary": "dry result",
        "artifact_refs": ["docs/Implementation_Roadmap.md"],
        "gate_ledger": [
            {
                "command": "python -m py_compile tooling/example.py",
                "result": "NOT_RUN",
                "reason": "fixture only",
                "artifacts": [],
            }
        ],
        "postcondition_claims": [],
        "interrupt_request": None,
        "observed_writes": ["docs/Implementation_Roadmap.md"],
        "stdout_ref": ".workflow_supervisor/runs/sup/runtime/stdout.log",
        "stderr_ref": ".workflow_supervisor/runs/sup/runtime/stderr.log",
        "contract_violations": [],
        "worker_warnings": [],
    }


def init_git_workspace(root: Path) -> str:
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
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test: initial"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit_paths(root: Path, message: str, *paths: str) -> str:
    subprocess.run(["git", "add", *paths], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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
                (
                    "| `S2_proxy_postprocess` | src/s2.py | py_compile | "
                    "`feat(slice/S2_proxy_postprocess): add metrics` | slice |"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_worker_result_accepts_valid_success() -> None:
    errors = workflow_ctl.validate_worker_result(REPO_ROOT, valid_worker_result())

    assert errors == []


def test_worker_result_rejects_runtime_ownership_violation() -> None:
    result = valid_worker_result()
    result["observed_writes"] = [".workflow_supervisor/state.json"]

    errors = workflow_ctl.validate_worker_result(REPO_ROOT, result)

    assert any("tool-owned path: .workflow_supervisor/state.json" in e for e in errors)


def test_worker_result_rejects_direct_evidence_write() -> None:
    result = valid_worker_result()
    result["observed_writes"] = [".evidence/chains/codebase_map/audit.json"]

    errors = workflow_ctl.validate_worker_result(REPO_ROOT, result)

    assert any(
        "tool-owned path: .evidence/chains/codebase_map/audit.json" in e
        for e in errors
    )


def test_worker_result_rejects_interrupt_without_payload() -> None:
    result = valid_worker_result()
    result["status"] = "interrupt_requested"

    errors = workflow_ctl.validate_worker_result(REPO_ROOT, result)

    assert "interrupt_requested requires interrupt_request" in errors


def test_worker_result_rejects_direct_user_question() -> None:
    result = valid_worker_result()
    result["summary"] = "I asked the user to provide the dataset path."

    errors = workflow_ctl.validate_worker_result(REPO_ROOT, result)

    assert "worker_direct_user_question" in errors


def test_codex_worker_handoff_path_avoids_supervisor_runtime() -> None:
    paths = workflow_ctl.worker_runtime_paths(
        REPO_ROOT,
        run_id="sup_20260605_000000",
        node_id="build_validate_run",
    )
    prompt = workflow_ctl.render_worker_prompt(
        workspace_root=REPO_ROOT,
        run_id="sup_20260605_000000",
        node={
            "node_id": "build_validate_run",
            "skill": "validate-run",
            "segment": "build",
            "postconditions": [
                {"type": "command_passes", "command": "validate-run verdict"}
            ],
            "evidence_tools": [
                {
                    "command": (
                        "python tooling/evidence/check_dynamic_context.py "
                        "--workspace-root . --stage wf10 --review-packet"
                    ),
                    "outputs": [".evidence/review_packets/"],
                }
            ],
            "allowed_worker_write_patterns": ["docs/Validate_Run_Report.md"],
        },
        goal="validate runnable build",
        result_ref=paths["handoff_result"],
    )

    assert paths["handoff_result"].startswith(
        ".agents/state/workflow_supervisor_worker_results/"
    )
    assert not paths["handoff_result"].startswith(".workflow_supervisor/")
    assert "temporary worker handoff" in prompt
    assert "Automation budget:" in prompt
    assert "Evidence tools for this node:" in prompt
    assert "check_dynamic_context.py" in prompt
    assert '"profile": "automation_build"' in prompt
    assert "Do not write docs/_site or docs/_views" in prompt
    assert "docs_site_boundary_report" in prompt
    assert "For each `command_passes` postcondition" in prompt
    assert "semantic git commit" in prompt
    assert "sliced commits" in prompt
    assert '"command": "validate-run verdict"' in prompt
    assert "Do not use apply_patch for this handoff file" in prompt


def test_command_passes_postcondition_requires_matching_gate() -> None:
    node = {
        "node_id": "build_validate_run",
        "postconditions": [
            {"type": "command_passes", "command": "validate-run verdict"}
        ],
    }
    missing_gate_result = workflow_ctl.evaluate_node_postconditions(
        REPO_ROOT,
        node,
        run_id="sup_20260605_000000",
        worker_result=valid_worker_result(),
    )

    assert missing_gate_result["ok"] is False
    assert missing_gate_result["gate_ledger"][0]["result"] == "NOT_RUN"

    worker = valid_worker_result()
    worker["gate_ledger"] = [
        {
            "command": "validate-run verdict",
            "result": "PASS",
            "reason": "semantic review and smoke chain passed",
            "artifacts": ["docs/Validate_Run_Report.md"],
        }
    ]
    passing_result = workflow_ctl.evaluate_node_postconditions(
        REPO_ROOT,
        node,
        run_id="sup_20260605_000000",
        worker_result=worker,
    )

    assert passing_result["ok"] is True
    assert passing_result["gate_ledger"][0]["result"] == "PASS"


def test_sliced_commits_recorded_requires_roadmap_slice_commits(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    base_commit = init_git_workspace(root)
    run_id = "sup_20260605_000000"
    write_run_manifest(root, run_id, base_commit)
    write_roadmap_commit_plan(root)
    node = {
        "node_id": "build_code_expert",
        "postconditions": [
            {
                "type": "sliced_commits_recorded",
                "roadmap_path": "docs/Implementation_Roadmap.md",
            }
        ],
    }

    missing_result = workflow_ctl.evaluate_node_postconditions(
        root,
        node,
        run_id=run_id,
        worker_result=valid_worker_result(),
    )

    assert missing_result["ok"] is False
    assert missing_result["gate_ledger"][0]["result"] == "FAIL"
    assert "missing semantic commits" in missing_result["gate_ledger"][0]["reason"]

    (root / "src").mkdir()
    (root / "src" / "s1.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit_paths(
        root,
        "feat(slice/S1_data_answer_contract): add records",
        "docs/Implementation_Roadmap.md",
        "src/s1.py",
    )
    (root / "src" / "s2.py").write_text("VALUE = 2\n", encoding="utf-8")
    commit_paths(
        root,
        "feat(slice/S2_proxy_postprocess): add metrics",
        "src/s2.py",
    )

    passing_result = workflow_ctl.evaluate_node_postconditions(
        root,
        node,
        run_id=run_id,
        worker_result=valid_worker_result(),
    )

    assert passing_result["ok"] is True
    assert passing_result["gate_ledger"][0]["result"] == "PASS"
    assert "S1_data_answer_contract" in "\n".join(
        passing_result["gate_ledger"][0]["artifacts"]
    )


def test_git_worktree_clean_ignores_tool_owned_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    init_git_workspace(root)
    node = {
        "node_id": "build_validate_run",
        "postconditions": [{"type": "git_worktree_clean"}],
    }
    (root / ".evidence" / "chains").mkdir(parents=True)
    (root / ".evidence" / "chains" / "trace.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    handoff_dir = root / ".agents" / "state" / "workflow_supervisor_worker_results"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / "handoff.json").write_text("{}\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "dirty.py").write_text("VALUE = 1\n", encoding="utf-8")

    dirty_result = workflow_ctl.evaluate_node_postconditions(
        root,
        node,
        run_id="sup_20260605_000000",
        worker_result=valid_worker_result(),
    )

    assert dirty_result["ok"] is False
    assert dirty_result["gate_ledger"][0]["artifacts"] == ["src/dirty.py"]

    commit_paths(root, "test: commit source", "src/dirty.py")
    clean_result = workflow_ctl.evaluate_node_postconditions(
        root,
        node,
        run_id="sup_20260605_000000",
        worker_result=valid_worker_result(),
    )

    assert clean_result["ok"] is True


def test_codex_worker_command_places_exec_before_exec_options() -> None:
    command = workflow_ctl.codex_worker_command("/usr/bin/codex", REPO_ROOT)

    assert command[:3] == ["/usr/bin/codex", "exec", "--full-auto"]
    assert command[-3:] == ["--cd", str(REPO_ROOT), "-"]


def test_codex_worker_synthesizes_success_when_handoff_missing_but_artifact_passes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "docs" / "Technical_Spec.md").write_text("# Spec\n", encoding="utf-8")

    class Completed:
        returncode = 0

    def fake_run(command, **kwargs):
        assert command[:3] == ["/usr/bin/codex", "exec", "--full-auto"]
        assert command[-3:] == ["--cd", str(root), "-"]
        return Completed()

    monkeypatch.setattr(workflow_ctl.shutil, "which", lambda _name: "/usr/bin/codex")
    monkeypatch.setattr(workflow_ctl.subprocess, "run", fake_run)

    result = workflow_ctl.run_codex_worker(
        root,
        args=argparse.Namespace(codex_home=None),
        run_id="sup_20260605_000000",
        node={
            "node_id": "build_refine_arch",
            "skill": "refine-arch",
            "segment": "build",
            "attempt": 1,
            "postconditions": [
                {"type": "artifact_exists", "path": "docs/Technical_Spec.md"},
                {"type": "no_forbidden_writes", "patterns": [".evidence/"]},
            ],
            "evidence_tools": [],
            "allowed_worker_write_patterns": ["docs/Technical_Spec.md"],
        },
        goal="write spec",
    )

    assert result["status"] == "success"
    assert "docs/Technical_Spec.md" in result["observed_writes"]
    assert "codex_worker_missing_handoff_synthesized_from_postconditions" in result[
        "worker_warnings"
    ]
    assert any(gate["result"] == "PASS" for gate in result["gate_ledger"])
    assert workflow_ctl.validate_worker_result(REPO_ROOT, result) == []


def test_codex_worker_does_not_synthesize_success_when_command_gate_missing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "docs" / "Validate_Run_Report.md").write_text(
        "# Validate\n",
        encoding="utf-8",
    )

    result = workflow_ctl.synthetic_codex_success_from_postconditions(
        root,
        run_id="sup_20260605_000000",
        node={
            "node_id": "build_validate_run",
            "skill": "validate-run",
            "segment": "build",
            "attempt": 1,
            "postconditions": [
                {"type": "artifact_exists", "path": "docs/Validate_Run_Report.md"},
                {"type": "command_passes", "command": "validate-run verdict"},
            ],
        },
        command=["codex", "exec"],
        paths={
            "prompt": ".workflow_supervisor/runs/sup/runtime/prompt.txt",
            "stdout": ".workflow_supervisor/runs/sup/runtime/stdout.log",
            "stderr": ".workflow_supervisor/runs/sup/runtime/stderr.log",
        },
    )

    assert result is None


def test_adopts_previous_missing_handoff_when_postconditions_pass(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    run_id = "sup_20260605_000000"
    node_id = "build_refine_arch"
    runtime = root / ".workflow_supervisor" / "runs" / run_id / "runtime"
    node_runs = root / ".workflow_supervisor" / "runs" / run_id / "node_runs"
    runtime.mkdir(parents=True)
    node_runs.mkdir(parents=True)
    worker_ref = (
        f".workflow_supervisor/runs/{run_id}/runtime/{node_id}.worker_result.json"
    )
    worker = valid_worker_result()
    worker.update(
        {
            "run_id": run_id,
            "node_id": node_id,
            "skill": "refine-arch",
            "status": "failed",
            "exit_code": 1,
            "summary": "codex worker did not write worker result JSON",
        }
    )
    (root / worker_ref).write_text(json.dumps(worker) + "\n", encoding="utf-8")
    record_path = node_runs / f"{node_id}.json"
    record_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "node_id": node_id,
                "skill": "refine-arch",
                "segment": "build",
                "status": "failed",
                "worker_result_ref": worker_ref,
                "postcondition_result": {"ok": True, "gate_ledger": []},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state = workflow_ctl.base_state(run_id, "build")
    state["status"] = "running"
    state["failed_nodes"] = [node_id]
    workflow_ctl.atomic_write_json(
        workflow_ctl.lock_path(root),
        {"run_id": run_id, "created_at": "2026-06-05T00:00:00Z"},
    )
    completed: list[str] = []

    adopted = workflow_ctl.adopt_previous_missing_handoff_success(
        root,
        run_id=run_id,
        state=state,
        segment="build",
        node={"node_id": node_id},
        completed=completed,
    )

    assert adopted is True
    assert completed == [node_id]
    assert state["completed_nodes"] == [node_id]
    assert state["failed_nodes"] == []
    updated_record = json.loads(record_path.read_text(encoding="utf-8"))
    assert updated_record["status"] == "success"
    assert (
        updated_record["adoption_reason"]
        == "codex_missing_handoff_but_postconditions_passed"
    )
    assert updated_record["adoption_worker_exit_code"] == 1


def test_worker_prompt_truncates_large_goal_context() -> None:
    prompt = workflow_ctl.render_worker_prompt(
        workspace_root=REPO_ROOT,
        run_id="sup_20260605_000000",
        node={
            "node_id": "prepare_data_prep",
            "skill": "data-prep",
            "segment": "prepare",
            "max_attempts": 1,
            "postconditions": [],
            "allowed_worker_write_patterns": ["docs/Dataset_Stats.md"],
            "automation_policy": {
                "goal_max_chars": 80,
                "json_context_max_chars": 500,
            },
        },
        goal="x" * 500,
        result_ref=(
            ".agents/state/workflow_supervisor_worker_results/"
            "sup_20260605_000000/prepare_data_prep.worker_result.json"
        ),
    )

    assert "truncated goal" in prompt
    assert '"profile": "automation_prepare"' in prompt
    assert '"node_retry_limit": 1' in prompt
    assert "x" * 200 not in prompt
