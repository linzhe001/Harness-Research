from __future__ import annotations

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
            "postconditions": [],
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
