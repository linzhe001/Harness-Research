from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_tool(name: str):
    path = REPO_ROOT / "tooling" / "evidence" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def base_project_state() -> dict:
    return {
        "current_stage": {
            "workflow_id": 10,
            "workflow_name": "iterate",
            "status": "in_progress",
            "latest_iteration": "iter1",
        },
        "evaluation_protocol": {
            "primary_metric": "accuracy",
            "tracked_metrics": [{"name": "accuracy", "goal": "max"}],
        },
    }


def base_iteration_log() -> dict:
    return {
        "schema_version": "2",
        "project": "test",
        "evaluation_protocol": {
            "primary_metric": "accuracy",
            "tracked_metrics": [{"name": "accuracy", "goal": "max"}],
        },
        "baseline_metrics": {"accuracy": 0.7},
        "best_iteration": "iter1",
        "iterations": [
            {
                "id": "iter1",
                "date": "2026-04-30",
                "hypothesis": "A small reviewed change improves accuracy.",
                "changes_summary": "Test fixture iteration.",
                "config_diff": {},
                "status": "completed",
                "decision": "CONTINUE",
                "git_commit": "abc123",
                "git_message": "test: fixture iteration",
                "action_state": {
                    "next_action": "stop",
                    "last_action": "eval",
                    "reason": "Test fixture completed.",
                    "blocked_by": [],
                },
                "implementation": {
                    "scope": "config_only",
                    "code_manifest_path": None,
                    "touched_paths": [],
                    "stable_api_changed": False,
                    "delegated_build_run_id": None,
                    "promotion": {
                        "status": "not_applicable",
                        "plan_path": None,
                    },
                },
                "run_manifest": {
                    "artifact_contract_version": "1",
                    "run_type": "full",
                    "command": "python train.py --config configs/test.yaml",
                    "config_path": "configs/test.yaml",
                    "resolved_config_path": "experiments/iter1/run_param.yaml",
                    "exp_dir": "experiments/iter1",
                    "stdout_log_path": "experiments/iter1/stdout+stderr.log",
                    "git_snapshot_path": "experiments/iter1/git_status/commit.txt",
                    "git_commit": "abc123",
                    "eval_artifact_paths": ["experiments/iter1/epochs/1/eval.jsonl"],
                    "checkpoint_path": "experiments/iter1/checkpoints/1/model.pth",
                },
                "metrics": {"accuracy": 0.8},
                "lessons": ["Accuracy improved under the reviewed protocol."],
            }
        ],
    }


def base_project_map() -> dict:
    return {
        "version": 1,
        "updated_at": "2026-04-30T00:00:00Z",
        "detail_policy": "stable_files_only",
        "structure": {
            "src": {
                "type": "directory",
                "description": "Source package.",
                "children": {
                    "model.py": {
                        "type": "file",
                        "description": "Model definition.",
                    }
                },
            }
        },
    }


def write_required_stage_artifacts(root: Path) -> None:
    docs = {
        "Feasibility_Report.md": "# Feasibility\n",
        "Idea_Debate.md": "# Idea Debate\n",
        "Refined_Idea.md": "# Refined Idea\n",
        "Dataset_Stats.md": "# Dataset Stats\n",
        "Baseline_Report.md": "# Baseline Report\n",
        "Technical_Spec.md": "# Technical Spec\n",
        "Implementation_Roadmap.md": "# Implementation Roadmap\n",
        "Validate_Run_Report.md": "# Validate Run Report\n",
    }
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    for name, text in docs.items():
        (docs_dir / name).write_text(text, encoding="utf-8")
    iterations_dir = docs_dir / "iterations"
    iterations_dir.mkdir(parents=True, exist_ok=True)
    (iterations_dir / "iter1.md").write_text("# iter1\n", encoding="utf-8")
    src_dir = root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "model.py").write_text("# source marker\n", encoding="utf-8")
    write_run_artifact_bundle(root)


def write_run_artifact_bundle(root: Path, commit: str = "abc123") -> None:
    exp_dir = root / "experiments" / "iter1"
    (exp_dir / "git_status").mkdir(parents=True, exist_ok=True)
    (exp_dir / "epochs" / "1").mkdir(parents=True, exist_ok=True)
    (exp_dir / "checkpoints" / "1").mkdir(parents=True, exist_ok=True)
    (exp_dir / "run_param.yaml").write_text("seed: 1\n", encoding="utf-8")
    (exp_dir / "stdout+stderr.log").write_text("completed\n", encoding="utf-8")
    (exp_dir / "git_status" / "commit.txt").write_text(
        f"{commit}\n",
        encoding="utf-8",
    )
    (exp_dir / "epochs" / "1" / "eval.jsonl").write_text(
        '{"accuracy": 0.8}\n',
        encoding="utf-8",
    )
    (exp_dir / "checkpoints" / "1" / "model.pth").write_text(
        "checkpoint marker\n",
        encoding="utf-8",
    )


def test_workflow_state_valid_cross_file_set_passes(tmp_path: Path) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    write_json(tmp_path / "iteration_log.json", base_iteration_log())
    write_json(tmp_path / "project_map.json", base_project_map())
    report_path = tmp_path / "docs" / "iterations" / "iter1.md"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("# iter1\n", encoding="utf-8")
    write_run_artifact_bundle(tmp_path)
    write_json(
        tmp_path / ".auto_iterate" / "state.json",
        {"current_iteration_id": "iter1", "current_phase_key": "eval"},
    )

    result = checker.gate_result(tmp_path)

    assert result["ok"] is True
    assert result["error_count"] == 0


def test_workflow_state_rejects_legacy_iteration_log(tmp_path: Path) -> None:
    checker = load_tool("check_workflow_state")
    legacy = base_iteration_log()
    legacy.pop("schema_version")
    legacy.pop("project")
    legacy.pop("baseline_metrics")
    for iteration in legacy["iterations"]:
        iteration.pop("action_state")
        iteration.pop("implementation")
    write_json(tmp_path / "iteration_log.json", legacy)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_log_schema_version" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_stage_name_id_mismatch(tmp_path: Path) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["current_stage"]["workflow_id"] = 8
    write_json(tmp_path / "PROJECT_STATE.json", state)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "project_state_stage_consistency" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_dynamic_project_that_skipped_wf2(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["context_model_version"] = "dynamic-protocol-v1"
    write_json(tmp_path / "PROJECT_STATE.json", state)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "wf2_required_for_new_project" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_standard_project_that_skipped_wf2(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["workflow_mode"] = "standard"
    write_json(tmp_path / "PROJECT_STATE.json", state)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "wf2_required_for_new_project" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_allows_compatibility_project_without_wf2(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["workflow_mode"] = "compatibility"
    write_json(tmp_path / "PROJECT_STATE.json", state)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is True
    assert not any(
        check["name"] == "wf2_required_for_new_project" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_standard_project_missing_prior_stage_artifacts(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["workflow_mode"] = "standard"
    state["history"] = [{"workflow_id": 2, "workflow_name": "idea_debate"}]
    write_json(tmp_path / "PROJECT_STATE.json", state)
    write_json(tmp_path / "iteration_log.json", base_iteration_log())
    write_json(tmp_path / "project_map.json", base_project_map())

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "stage_artifact_present"
        and not check["ok"]
        and "WF5 requires baseline_report" in check["detail"]
        for check in result["checks"]
    )


def test_workflow_state_accepts_standard_project_with_required_stage_artifacts(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["workflow_mode"] = "standard"
    state["dataset_paths"] = {"train": "data/train.csv"}
    state["baseline_metrics"] = {"accuracy": 0.7}
    write_required_stage_artifacts(tmp_path)
    write_json(tmp_path / "PROJECT_STATE.json", state)
    write_json(tmp_path / "iteration_log.json", base_iteration_log())
    write_json(tmp_path / "project_map.json", base_project_map())

    result = checker.gate_result(tmp_path)

    assert result["ok"] is True
    assert not any(
        check["name"].startswith("stage_artifact")
        and check["severity"] == "error"
        and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_invalid_workflow_mode(tmp_path: Path) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["workflow_mode"] = "new_non_dynamic"
    write_json(tmp_path / "PROJECT_STATE.json", state)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "workflow_mode_valid" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_invalid_lesson_candidates(tmp_path: Path) -> None:
    checker = load_tool("check_workflow_state")
    log = base_iteration_log()
    log["iterations"][0]["lesson_candidates"] = [
        {
            "claim": "Candidate missing reviewed evidence.",
            "level": "lesson",
            "confidence": "medium",
            "promotion_status": "candidate",
        }
    ]
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "lesson_candidates_schema" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_completed_iteration_without_git_commit(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    del log["iterations"][0]["git_commit"]
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_completed_git_commit" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_completed_iteration_without_run_manifest(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    del log["iterations"][0]["run_manifest"]
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_completed_run_manifest" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_completed_iteration_with_incomplete_run_manifest(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    log["iterations"][0]["run_manifest"] = {"command": "python train.py"}
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_completed_run_manifest"
        and not check["ok"]
        and "exp_dir" in check["detail"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_completed_iteration_missing_run_artifacts(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    write_json(tmp_path / "iteration_log.json", base_iteration_log())
    report_path = tmp_path / "docs" / "40_iterations" / "iter1.md"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("# iter1\n", encoding="utf-8")

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_run_artifact_bundle"
        and not check["ok"]
        and "resolved_config_path" in check["detail"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_duplicate_completed_run_exp_dirs(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    duplicate = deepcopy(log["iterations"][0])
    duplicate["id"] = "iter2"
    log["iterations"].append(duplicate)
    write_json(tmp_path / "iteration_log.json", log)
    write_run_artifact_bundle(tmp_path)
    for iteration_id in ("iter1", "iter2"):
        report_path = tmp_path / "docs" / "40_iterations" / f"{iteration_id}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(f"# {iteration_id}\n", encoding="utf-8")

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_run_exp_dirs_unique"
        and not check["ok"]
        and "experiments/iter1" in check["detail"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_screening_and_full_run_same_exp_dir(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    run_manifest = deepcopy(log["iterations"][0]["run_manifest"])
    run_manifest["run_type"] = "screening"
    log["iterations"][0]["screening"] = {
        "recommended": True,
        "status": "passed",
        "metrics": {"accuracy": 0.7},
        "run_manifest": run_manifest,
    }
    log["iterations"][0]["full_run"] = {
        "status": "completed",
        "metrics": {"accuracy": 0.8},
    }
    write_json(tmp_path / "iteration_log.json", log)
    write_run_artifact_bundle(tmp_path)
    report_path = tmp_path / "docs" / "40_iterations" / "iter1.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("# iter1\n", encoding="utf-8")

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_run_exp_dirs_unique"
        and not check["ok"]
        and "must differ" in check["detail"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_untracked_screening_metric(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    log["iterations"] = [
        {
            "id": "iter1",
            "status": "ready_to_run",
            "git_commit": "abc123",
            "screening": {
                "recommended": True,
                "status": "passed",
                "metrics": {"NOT_TRACKED": 1.0},
                "run_manifest": {
                    "artifact_contract_version": "1",
                    "run_type": "screening",
                    "command": "python train.py --config configs/test.yaml",
                    "config_path": "configs/test.yaml",
                    "resolved_config_path": "experiments/iter1/run_param.yaml",
                    "exp_dir": "experiments/iter1",
                    "stdout_log_path": "experiments/iter1/stdout+stderr.log",
                    "git_snapshot_path": "experiments/iter1/git_status/commit.txt",
                    "git_commit": "abc123",
                    "eval_artifact_paths": [
                        "experiments/iter1/epochs/1/eval.jsonl"
                    ],
                },
            },
        }
    ]
    write_json(tmp_path / "iteration_log.json", log)
    write_run_artifact_bundle(tmp_path)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_screening_metric_protocol_consistency"
        and not check["ok"]
        and "NOT_TRACKED" in check["detail"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_screening_missing_run_manifest(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    log["iterations"] = [
        {
            "id": "iter1",
            "status": "ready_to_run",
            "screening": {
                "recommended": True,
                "status": "passed",
                "metrics": {"accuracy": 0.8},
            },
        }
    ]
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_screening_run_manifest"
        and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_completed_iteration_missing_primary_metric(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    log["evaluation_protocol"]["tracked_metrics"].append({"name": "loss"})
    log["iterations"][0]["metrics"] = {"loss": 0.5}
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_primary_metric_required"
        and not check["ok"]
        and "accuracy" in check["detail"]
        for check in result["checks"]
    )


def test_workflow_state_rejects_non_numeric_primary_metric(
    tmp_path: Path,
) -> None:
    checker = load_tool("check_workflow_state")
    write_json(tmp_path / "PROJECT_STATE.json", base_project_state())
    log = base_iteration_log()
    log["iterations"][0]["metrics"] = {"accuracy": "0.8"}
    write_json(tmp_path / "iteration_log.json", log)

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_primary_metric_numeric"
        and not check["ok"]
        and "accuracy" in check["detail"]
        for check in result["checks"]
    )


def test_workflow_state_requires_dual_approval_markers(tmp_path: Path) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["contracts"] = {
        "evaluation_contract": {
            "path": "docs/10_contract/Evaluation_Contract.md",
            "status": "approved",
            "approved_at": "2026-04-30T00:00:00Z",
            "approved_by": "expert",
            "approval_source": "review packet",
        }
    }
    write_json(tmp_path / "PROJECT_STATE.json", state)
    contract = tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Evaluation Contract\n\nStatus: approved\nHuman approved: no\n",
        encoding="utf-8",
    )

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "evaluation_contract_markdown_approval" and not check["ok"]
        for check in result["checks"]
    )


def test_workflow_state_checks_baseline_contract_markers(tmp_path: Path) -> None:
    checker = load_tool("check_workflow_state")
    state = base_project_state()
    state["contracts"] = {
        "baseline_contract": {
            "path": "docs/10_contract/Baseline_Contract.md",
            "status": "approved",
            "approved_at": "2026-04-30T00:00:00Z",
            "approved_by": "expert",
            "approval_source": "review packet",
        }
    }
    write_json(tmp_path / "PROJECT_STATE.json", state)
    contract = tmp_path / "docs" / "10_contract" / "Baseline_Contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Baseline Contract\n\nStatus: approved\nHuman approved: no\n",
        encoding="utf-8",
    )

    result = checker.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(
        check["name"] == "baseline_contract_markdown_approval" and not check["ok"]
        for check in result["checks"]
    )
