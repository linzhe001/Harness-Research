from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_tool(name: str):
    path = REPO_ROOT / "tooling" / "evidence" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_state() -> dict:
    return {
        "project_meta": {
            "name": "ToolFixture",
            "idea_summary": "test",
            "target_venue": "Other",
            "deadline": "2099-01-01",
            "dataset_name": "test",
            "created_at": "2026-04-29T00:00:00Z",
            "updated_at": "2026-04-29T00:00:00Z",
        },
        "current_stage": {
            "workflow_id": 10,
            "workflow_name": "iterate",
            "status": "in_progress",
        },
        "artifacts": {},
        "baseline_metrics": {},
        "evaluation_protocol": {
            "primary_metric": "accuracy",
            "tracked_metrics": [{"name": "accuracy", "goal": "max"}],
        },
        "decisions": [],
        "history": [],
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_init_context_copies_templates_without_overwrite(tmp_path: Path) -> None:
    init_context = load_tool("init_context")
    existing = tmp_path / "docs" / "10_contract" / "Project_Contract.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("custom contract\n", encoding="utf-8")

    summary = init_context.initialize_context(tmp_path, framework_root=REPO_ROOT)

    assert summary["ok"] is True
    assert (tmp_path / "docs" / "30_evidence" / "Evidence_Index.md").exists()
    assert (tmp_path / ".evidence" / "schemas" / "evidence_chain.schema.json").exists()
    assert existing.read_text(encoding="utf-8") == "custom contract\n"
    assert any(
        action["action"] == "skip_exists"
        and action["path"].endswith("Project_Contract.md")
        for action in summary["actions"]
    )


def test_init_context_can_set_project_state(tmp_path: Path) -> None:
    init_context = load_tool("init_context")
    write_json(tmp_path / "PROJECT_STATE.json", minimal_state())

    init_context.initialize_context(tmp_path, framework_root=REPO_ROOT, set_state=True)
    state = json.loads((tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8"))

    assert state["workflow_mode"] == "dynamic_context"
    assert state["context_model_version"] == "dynamic-protocol-v1"
    assert (
        state["contracts"]["evaluation_contract"]["path"]
        == "docs/10_contract/Evaluation_Contract.md"
    )
    assert state["contracts"]["evaluation_contract"]["status"] == "draft"
    assert (
        state["contracts"]["baseline_contract"]["path"]
        == "docs/10_contract/Baseline_Contract.md"
    )
    assert state["contracts"]["baseline_contract"]["status"] == "draft"


def test_context_gate_legacy_wf10_uses_evaluation_protocol(tmp_path: Path) -> None:
    gates = load_tool("check_context_gates")
    write_json(tmp_path / "PROJECT_STATE.json", minimal_state())

    result = gates.gate_result(tmp_path, stage="wf10-auto")

    assert result["ok"] is True
    assert result["dynamic_context"] is False


def test_context_gate_dynamic_wf10_requires_evaluation_contract(tmp_path: Path) -> None:
    gates = load_tool("check_context_gates")
    state = minimal_state()
    state["context_model_version"] = "dynamic-protocol-v1"
    write_json(tmp_path / "PROJECT_STATE.json", state)

    result = gates.gate_result(tmp_path, stage="wf10-auto")

    assert result["ok"] is False
    assert result["error_count"] == 1


def test_context_gate_dynamic_status_reports_missing_contracts_without_failing(
    tmp_path: Path,
) -> None:
    gates = load_tool("check_context_gates")
    state = minimal_state()
    state["context_model_version"] = "dynamic-protocol-v1"
    write_json(tmp_path / "PROJECT_STATE.json", state)

    result = gates.gate_result(tmp_path, stage="status")

    assert result["ok"] is True
    assert result["error_count"] == 0
    assert any(
        check["name"] == "evaluation_contract_status" and check["severity"] == "warn"
        for check in result["checks"]
    )


def test_context_gate_dynamic_wf10_accepts_approved_contract(tmp_path: Path) -> None:
    gates = load_tool("check_context_gates")
    state = minimal_state()
    state["context_model_version"] = "dynamic-protocol-v1"
    state["contracts"] = {
        "evaluation_contract": {
            "path": "docs/10_contract/Evaluation_Contract.md",
            "status": "approved",
            "approved_at": "2026-04-29T00:00:00Z",
            "approved_by": "human",
            "approval_source": "test",
        }
    }
    write_json(tmp_path / "PROJECT_STATE.json", state)
    contract = tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Evaluation Contract\n\nStatus: approved\nHuman approved: yes\n",
        encoding="utf-8",
    )

    result = gates.gate_result(tmp_path, stage="wf10-auto")

    assert result["ok"] is True
    assert result["contracts"]["evaluation_contract"]["status"] == "approved"


def test_context_gate_dynamic_wf5_blocks_missing_baseline_contract(
    tmp_path: Path,
) -> None:
    gates = load_tool("check_context_gates")
    state = minimal_state()
    state["context_model_version"] = "dynamic-protocol-v1"
    state["contracts"] = {
        "evaluation_contract": {
            "path": "docs/10_contract/Evaluation_Contract.md",
            "status": "approved",
            "approved_at": "2026-04-29T00:00:00Z",
            "approved_by": "human",
            "approval_source": "test",
        }
    }
    write_json(tmp_path / "PROJECT_STATE.json", state)
    contract = tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Evaluation Contract\n\nStatus: approved\nHuman approved: yes\n",
        encoding="utf-8",
    )

    result = gates.gate_result(tmp_path, stage="wf5-eval-contract")

    assert result["ok"] is False
    assert any(
        check["name"] == "baseline_contract_exists" and check["severity"] == "error"
        for check in result["checks"]
    )


def test_context_gate_dynamic_wf10_rejects_unconfirmed_approved_contract(
    tmp_path: Path,
) -> None:
    gates = load_tool("check_context_gates")
    state = minimal_state()
    state["context_model_version"] = "dynamic-protocol-v1"
    write_json(tmp_path / "PROJECT_STATE.json", state)
    contract = tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Evaluation Contract\n\nStatus: approved\nHuman approved: no\n",
        encoding="utf-8",
    )

    result = gates.gate_result(tmp_path, stage="wf10-auto")

    assert result["ok"] is False
    assert any(
        check["name"] == "evaluation_contract_approval_unconfirmed" and not check["ok"]
        for check in result["checks"]
    )


def test_context_gate_dynamic_wf10_can_allow_draft(tmp_path: Path) -> None:
    gates = load_tool("check_context_gates")
    state = minimal_state()
    state["context_model_version"] = "dynamic-protocol-v1"
    write_json(tmp_path / "PROJECT_STATE.json", state)
    contract = tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text("# Evaluation Contract\n\nStatus: draft\n", encoding="utf-8")

    result = gates.gate_result(tmp_path, stage="wf10-auto", allow_draft=True)

    assert result["ok"] is True
    assert result["warning_count"] == 1


def test_approve_contract_records_dual_approval_markers(tmp_path: Path) -> None:
    approve = load_tool("approve_contract")
    gates = load_tool("check_context_gates")
    state = minimal_state()
    state["context_model_version"] = "dynamic-protocol-v1"
    state["contracts"] = {
        "evaluation_contract": {
            "path": "docs/10_contract/Evaluation_Contract.md",
            "status": "draft",
        }
    }
    write_json(tmp_path / "PROJECT_STATE.json", state)
    contract = tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Evaluation Contract\n\nStatus: draft\nHuman approved: no\n", encoding="utf-8"
    )

    summary = approve.approve_contract(
        tmp_path,
        "evaluation_contract",
        approved_by="expert",
        approval_source=".evidence/review_packets/wf10/test/review_packet.md",
        approved_at="2026-04-30T00:00:00Z",
        approval_note="approved after packet review",
    )

    updated_state = json.loads(
        (tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8")
    )
    updated_contract = contract.read_text(encoding="utf-8")
    gate = gates.gate_result(tmp_path, stage="wf10-auto")
    assert summary["ok"] is True
    assert "Status: approved" in updated_contract
    assert "Human approved: yes" in updated_contract
    assert "Approved by: expert" in updated_contract
    assert updated_state["contracts"]["evaluation_contract"]["status"] == "approved"
    assert updated_state["contracts"]["evaluation_contract"][
        "approval_source"
    ].endswith("review_packet.md")
    assert gate["ok"] is True


def test_approve_contract_supports_baseline_contract(tmp_path: Path) -> None:
    approve = load_tool("approve_contract")
    checker = load_tool("check_workflow_state")
    state = minimal_state()
    state["workflow_mode"] = "compatibility"
    state["contracts"] = {
        "baseline_contract": {
            "path": "docs/10_contract/Baseline_Contract.md",
            "status": "draft",
        }
    }
    write_json(tmp_path / "PROJECT_STATE.json", state)
    contract = tmp_path / "docs" / "10_contract" / "Baseline_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Baseline Contract\n\nStatus: draft\nHuman approved: no\n",
        encoding="utf-8",
    )

    summary = approve.approve_contract(
        tmp_path,
        "baseline_contract",
        approved_by="expert",
        approval_source=".evidence/review_packets/wf5/test/review_packet.md",
        approved_at="2026-04-30T00:00:00Z",
    )

    updated_state = json.loads(
        (tmp_path / "PROJECT_STATE.json").read_text(encoding="utf-8")
    )
    workflow_gate = checker.gate_result(tmp_path)
    assert summary["ok"] is True
    assert "Status: approved" in contract.read_text(encoding="utf-8")
    assert updated_state["contracts"]["baseline_contract"]["status"] == "approved"
    assert workflow_gate["ok"] is True


def completed_iteration_log() -> dict:
    return {
        "evaluation_protocol": {
            "primary_metric": "accuracy",
            "tracked_metrics": [{"name": "accuracy", "goal": "max"}],
        },
        "best_iteration": "iter1",
        "iterations": [
            {
                "id": "iter1",
                "status": "completed",
                "decision": "CONTINUE",
                "git_commit": "abc123",
                "run_manifest": {
                    "command": "python train.py --config configs/test.yaml",
                    "exp_dir": "experiments/iter1",
                },
                "metrics": {"accuracy": 0.8},
                "lessons": ["Accuracy improved under the reviewed protocol."],
            }
        ],
    }


def test_workflow_state_requires_completed_iteration_git_commit(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", minimal_state())
    log = completed_iteration_log()
    del log["iterations"][0]["git_commit"]
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_completed_git_commit" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_requires_completed_iteration_run_manifest(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", minimal_state())
    log = completed_iteration_log()
    del log["iterations"][0]["run_manifest"]
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_completed_run_manifest" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_requires_completed_iteration_report(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", minimal_state())
    write_json(tmp_path / "iteration_log.json", completed_iteration_log())

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_completed_report" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_accepts_dynamic_context_iteration_report(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", minimal_state())
    write_json(tmp_path / "iteration_log.json", completed_iteration_log())
    report = tmp_path / "docs" / "40_iterations" / "iter1.md"
    report.parent.mkdir(parents=True)
    report.write_text("# iter1\n", encoding="utf-8")

    result = checker.gate_result(tmp_path)

    assert not any(
        check["name"] == "iteration_completed_report" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_conflicting_iteration_metrics(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", minimal_state())
    log = completed_iteration_log()
    log["iterations"][0]["full_run"] = {"metrics": {"accuracy": 0.7}}
    write_json(tmp_path / "iteration_log.json", log)
    report = tmp_path / "docs" / "iterations" / "iter1.md"
    report.parent.mkdir(parents=True)
    report.write_text("# iter1\n", encoding="utf-8")

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_metric_location_conflict" and not check["ok"]
        for check in result["checks"]
    )


def test_approve_contract_requires_approval_provenance(tmp_path: Path) -> None:
    approve = load_tool("approve_contract")
    write_json(tmp_path / "PROJECT_STATE.json", minimal_state())
    contract = tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text("# Evaluation Contract\n\nStatus: draft\n", encoding="utf-8")

    try:
        approve.approve_contract(
            tmp_path,
            "evaluation_contract",
            approved_by="expert",
            approval_source="",
        )
    except ValueError as exc:
        assert "approval_source" in str(exc)
    else:
        raise AssertionError("approval without provenance should fail")
