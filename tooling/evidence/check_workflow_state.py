#!/usr/bin/env python3
"""Validate workflow state files and their cross-file consistency."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
TOOLING_DIR = SCRIPT_DIR.parent
if str(TOOLING_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLING_DIR))

from dynamic_context import (  # noqa: E402
    VALID_WORKFLOW_MODES,
    is_new_workflow_project,
    workflow_mode,
)
from run_artifacts import run_artifact_errors  # noqa: E402

VALID_CONTRACT_STATUSES = {"missing", "draft", "approved", "superseded"}
VALID_STAGE_STATUSES = {"not_started", "in_progress", "completed", "blocked", "active"}
VALID_ITERATION_STATUSES = {
    "planned",
    "coding",
    "training",
    "running",
    "completed",
    "abandoned",
    "debug",
}
VALID_DECISIONS = {"NEXT_ROUND", "DEBUG", "CONTINUE", "PIVOT", "ABORT"}
VALID_LESSON_LEVELS = {"observation", "finding", "lesson", "invariant_candidate"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_PROMOTION_STATUS = {"candidate", "accepted", "rejected"}
TRUE_VALUES = {"yes", "true", "approved", "y", "1"}

CONTRACT_PATHS = {
    "project_contract": "docs/10_contract/Project_Contract.md",
    "evaluation_contract": "docs/10_contract/Evaluation_Contract.md",
    "baseline_contract": "docs/10_contract/Baseline_Contract.md",
    "claim_boundary": "docs/10_contract/Claim_Boundary.md",
}
WORKFLOW_IDS = {
    "survey_idea": 1,
    "survey": 1,
    "idea_debate": 2,
    "refine_idea": 3,
    "data_prep": 4,
    "data": 4,
    "baseline_repro": 5,
    "baseline": 5,
    "refine_arch": 6,
    "architecture_design": 6,
    "deep_check": 6,
    "build_plan": 7,
    "code_expert": 8,
    "validate_run": 9,
    "iterate": 10,
    "final_exp": 11,
    "release": 12,
}
STAGE_ARTIFACT_PATHS = {
    1: [("feasibility_report", ["docs/Feasibility_Report.md"], ["feasibility_report"])],
    2: [("idea_debate_report", ["docs/Idea_Debate.md"], ["idea_debate_report"])],
    3: [("refined_idea", ["docs/Refined_Idea.md"], ["refined_idea"])],
    4: [("dataset_stats", ["docs/Dataset_Stats.md"], ["dataset_stats"])],
    5: [("baseline_report", ["docs/Baseline_Report.md"], ["baseline_report"])],
    6: [("technical_spec", ["docs/Technical_Spec.md"], ["technical_spec"])],
    7: [
        (
            "implementation_roadmap",
            ["docs/Implementation_Roadmap.md"],
            ["implementation_roadmap"],
        ),
        ("project_map", ["project_map.json"], ["project_map"]),
    ],
    8: [("code_modules", ["src"], ["code_modules"])],
    9: [
        (
            "validate_run_report",
            ["docs/Validate_Run_Report.md"],
            ["validate_run_report"],
        )
    ],
    10: [("iteration_log", ["iteration_log.json"], ["iteration_log"])],
    11: [
        (
            "final_experiment_matrix",
            ["docs/Final_Experiment_Matrix.md"],
            ["experiment_matrix"],
        )
    ],
    12: [("release_manifest", ["submission/manifest.json"], ["release_manifest"])],
}


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    severity: str,
    detail: str,
    path: str | None = None,
) -> None:
    checks.append(
        {"name": name, "ok": ok, "severity": severity, "detail": detail, "path": path}
    )


def load_json_if_exists(
    path: Path, checks: list[dict[str, Any]], label: str, root: Path
) -> dict[str, Any] | None:
    if not path.exists():
        add_check(
            checks,
            f"{label}_exists",
            True,
            "info",
            f"{label} not found; skipping {label} checks.",
            relpath(path, root),
        )
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add_check(
            checks,
            f"{label}_json",
            False,
            "error",
            f"{label} is not valid JSON: {exc}.",
            relpath(path, root),
        )
        return None
    if not isinstance(data, dict):
        add_check(
            checks,
            f"{label}_object",
            False,
            "error",
            f"{label} must be a JSON object.",
            relpath(path, root),
        )
        return None
    add_check(
        checks,
        f"{label}_json",
        True,
        "info",
        f"{label} parses as a JSON object.",
        relpath(path, root),
    )
    return data


def read_header(path: Path, label: str) -> str | None:
    if not path.exists():
        return None
    prefix = f"{label.lower()}:"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:32]:
        if line.lower().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def markdown_status(path: Path) -> str:
    value = read_header(path, "Status")
    if value is None:
        return "missing" if not path.exists() else "draft"
    value = value.lower()
    return value if value in VALID_CONTRACT_STATUSES else "draft"


def markdown_human_approved(path: Path) -> bool:
    value = read_header(path, "Human approved")
    return value is not None and value.lower() in TRUE_VALUES


def approval_metadata_complete(entry: dict[str, Any]) -> bool:
    return all(
        bool(entry.get(field))
        for field in ("approved_at", "approved_by", "approval_source")
    )


def primary_metric_name(protocol: Any) -> str | None:
    if not isinstance(protocol, dict):
        return None
    metric = protocol.get("primary_metric")
    if isinstance(metric, str):
        return metric
    if isinstance(metric, dict):
        name = metric.get("name")
        return name if isinstance(name, str) else None
    return None


def tracked_metric_names(protocol: Any) -> set[str]:
    if not isinstance(protocol, dict):
        return set()
    metrics = protocol.get("tracked_metrics")
    if not isinstance(metrics, list):
        return set()
    names = set()
    for item in metrics:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.add(item["name"])
        elif isinstance(item, str):
            names.add(item)
    return names


def numeric_metric_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def iteration_metrics(iteration: dict[str, Any]) -> dict[str, Any]:
    top_level = iteration.get("metrics")
    if isinstance(top_level, dict) and top_level:
        return top_level
    full_run = iteration.get("full_run")
    if isinstance(full_run, dict):
        nested = full_run.get("metrics")
        if isinstance(nested, dict):
            return nested
    return {}


def iteration_metrics_conflict(iteration: dict[str, Any]) -> bool:
    top_level = iteration.get("metrics")
    if not isinstance(top_level, dict) or not top_level:
        return False
    full_run = iteration.get("full_run")
    if not isinstance(full_run, dict):
        return False
    nested = full_run.get("metrics")
    return isinstance(nested, dict) and bool(nested) and top_level != nested


def iteration_report_paths(root: Path, iteration_id: str) -> list[Path]:
    return [
        root / "docs" / "iterations" / f"{iteration_id}.md",
        root / "docs" / "40_iterations" / f"{iteration_id}.md",
    ]


def existing_iteration_report_path(root: Path, iteration_id: str) -> Path | None:
    for path in iteration_report_paths(root, iteration_id):
        if path.exists():
            return path
    return None


def iteration_report_candidates_detail(root: Path, iteration_id: str) -> str:
    return ", ".join(
        relpath(path, root)
        for path in iteration_report_paths(root, iteration_id)
    )


def check_project_state(
    root: Path, checks: list[dict[str, Any]]
) -> dict[str, Any] | None:
    state = load_json_if_exists(
        root / "PROJECT_STATE.json", checks, "PROJECT_STATE.json", root
    )
    if state is None:
        return None

    mode = workflow_mode(state)
    if mode is None:
        add_check(
            checks,
            "workflow_mode_present",
            True,
            "warn",
            "PROJECT_STATE.json has no workflow_mode; treating non-dynamic "
            "workspaces as compatibility for new-project-only gates.",
            "PROJECT_STATE.json",
        )
    elif mode not in VALID_WORKFLOW_MODES:
        add_check(
            checks,
            "workflow_mode_valid",
            False,
            "error",
            "workflow_mode must be one of "
            f"{sorted(VALID_WORKFLOW_MODES)}, got {mode!r}.",
            "PROJECT_STATE.json",
        )
    else:
        add_check(
            checks,
            "workflow_mode_valid",
            True,
            "info",
            f"workflow_mode is {mode!r}.",
            "PROJECT_STATE.json",
        )

    stage = state.get("current_stage")
    if isinstance(stage, dict):
        workflow_id = stage.get("workflow_id")
        workflow_name = stage.get("workflow_name")
        status = stage.get("status")
        if isinstance(workflow_id, int) and not 1 <= workflow_id <= 12:
            add_check(
                checks,
                "project_state_workflow_id_range",
                False,
                "error",
                "current_stage.workflow_id must be between 1 and 12.",
                "PROJECT_STATE.json",
            )
        if isinstance(status, str) and status not in VALID_STAGE_STATUSES:
            add_check(
                checks,
                "project_state_stage_status",
                False,
                "error",
                f"Unknown current_stage.status {status!r}.",
                "PROJECT_STATE.json",
            )
        if isinstance(workflow_name, str):
            expected_id = WORKFLOW_IDS.get(workflow_name)
            if expected_id is None:
                add_check(
                    checks,
                    "project_state_workflow_name",
                    False,
                    "error",
                    f"Unknown current_stage.workflow_name {workflow_name!r}.",
                    "PROJECT_STATE.json",
                )
            elif isinstance(workflow_id, int) and workflow_id != expected_id:
                add_check(
                    checks,
                    "project_state_stage_consistency",
                    False,
                    "error",
                    f"workflow_name {workflow_name!r} maps to WF{expected_id}, "
                    f"but workflow_id is {workflow_id}.",
                    "PROJECT_STATE.json",
                )
            else:
                add_check(
                    checks,
                    "project_state_stage_consistency",
                    True,
                    "info",
                    "current_stage.workflow_id and workflow_name are consistent.",
                    "PROJECT_STATE.json",
                )
        if isinstance(workflow_id, int):
            check_wf2_required_for_new_project(root, checks, state, workflow_id)
            check_stage_artifacts_for_new_project(
                root,
                checks,
                state,
                workflow_id,
                status if isinstance(status, str) else None,
            )
    else:
        add_check(
            checks,
            "project_state_current_stage",
            True,
            "warn",
            "PROJECT_STATE.json has no current_stage object; stage consistency "
            "cannot be checked.",
            "PROJECT_STATE.json",
        )

    contracts = state.get("contracts")
    if isinstance(contracts, dict):
        for key, expected_path in CONTRACT_PATHS.items():
            entry = contracts.get(key)
            if not isinstance(entry, dict):
                continue
            state_status = entry.get("status")
            if state_status not in VALID_CONTRACT_STATUSES:
                add_check(
                    checks,
                    f"{key}_state_status",
                    False,
                    "error",
                    f"contracts.{key}.status must be one of "
                    f"{sorted(VALID_CONTRACT_STATUSES)}.",
                    "PROJECT_STATE.json",
                )
                continue
            path = str(entry.get("path") or expected_path)
            if path != expected_path:
                add_check(
                    checks,
                    f"{key}_path",
                    False,
                    "error",
                    f"contracts.{key}.path should be {expected_path}, got {path!r}.",
                    "PROJECT_STATE.json",
                )
            doc_path = root / path
            doc_status = markdown_status(doc_path)
            if doc_path.exists() and doc_status != state_status:
                add_check(
                    checks,
                    f"{key}_status_consistency",
                    False,
                    "error",
                    f"{path} status {doc_status!r} does not match "
                    f"PROJECT_STATE.json status {state_status!r}.",
                    path,
                )
            if state_status == "approved":
                if not markdown_human_approved(doc_path):
                    add_check(
                        checks,
                        f"{key}_markdown_approval",
                        False,
                        "error",
                        f"{path} must contain Human approved: yes when "
                        "PROJECT_STATE marks it approved.",
                        path,
                    )
                if not approval_metadata_complete(entry):
                    add_check(
                        checks,
                        f"{key}_state_approval_metadata",
                        False,
                        "error",
                        f"contracts.{key} requires approved_at, approved_by, "
                        "and approval_source.",
                        "PROJECT_STATE.json",
                    )
    return state


def artifact_values(state: dict[str, Any], keys: list[str]) -> list[str]:
    artifacts = state.get("artifacts")
    if not isinstance(artifacts, dict):
        return []
    values: list[str] = []
    for key in keys:
        raw = artifacts.get(key)
        if isinstance(raw, str) and raw:
            values.append(raw)
        elif isinstance(raw, list):
            values.extend(item for item in raw if isinstance(item, str) and item)
    return values


def any_workspace_path_exists(root: Path, relatives: list[str]) -> bool:
    return any((root / relative).exists() for relative in relatives)


def check_stage_artifact_paths(
    root: Path,
    checks: list[dict[str, Any]],
    state: dict[str, Any],
    stage_id: int,
) -> None:
    for label, default_paths, artifact_keys in STAGE_ARTIFACT_PATHS.get(stage_id, []):
        candidates = [*default_paths, *artifact_values(state, artifact_keys)]
        if any_workspace_path_exists(root, candidates):
            add_check(
                checks,
                "stage_artifact_present",
                True,
                "info",
                f"WF{stage_id} artifact {label} is present.",
                candidates[0],
            )
        else:
            add_check(
                checks,
                "stage_artifact_present",
                False,
                "error",
                f"WF{stage_id} requires {label}; checked {', '.join(candidates)}.",
                candidates[0] if candidates else "PROJECT_STATE.json",
            )


def check_stage_artifact_fields(
    checks: list[dict[str, Any]],
    state: dict[str, Any],
    stage_id: int,
) -> None:
    if stage_id == 4:
        dataset_paths = state.get("dataset_paths")
        if not isinstance(dataset_paths, dict) or not dataset_paths:
            add_check(
                checks,
                "stage_artifact_field",
                False,
                "error",
                "WF4 requires PROJECT_STATE.json.dataset_paths.",
                "PROJECT_STATE.json",
            )
    if stage_id == 5:
        baseline_metrics = state.get("baseline_metrics")
        if not isinstance(baseline_metrics, dict) or not baseline_metrics:
            add_check(
                checks,
                "stage_artifact_field",
                False,
                "error",
                "WF5 requires populated PROJECT_STATE.json.baseline_metrics.",
                "PROJECT_STATE.json",
            )
        if not isinstance(state.get("evaluation_protocol"), dict):
            add_check(
                checks,
                "stage_artifact_field",
                False,
                "error",
                "WF5 requires PROJECT_STATE.json.evaluation_protocol for WF10 "
                "metric tracking.",
                "PROJECT_STATE.json",
            )


def stage_artifact_due(
    stage_id: int, current_workflow_id: int, current_status: str | None
) -> bool:
    if stage_id < current_workflow_id:
        return True
    if stage_id == current_workflow_id and current_status == "completed":
        return True
    if (
        stage_id == 10
        and current_workflow_id == 10
        and current_status in {"in_progress", "active", "completed"}
    ):
        return True
    return False


def check_stage_artifacts_for_new_project(
    root: Path,
    checks: list[dict[str, Any]],
    state: dict[str, Any],
    current_workflow_id: int,
    current_status: str | None,
) -> None:
    if not is_new_workflow_project(root, state):
        return
    for stage_id in sorted(STAGE_ARTIFACT_PATHS):
        if not stage_artifact_due(stage_id, current_workflow_id, current_status):
            continue
        check_stage_artifact_paths(root, checks, state, stage_id)
        check_stage_artifact_fields(checks, state, stage_id)


def check_wf2_required_for_new_project(
    root: Path, checks: list[dict[str, Any]], state: dict[str, Any], workflow_id: int
) -> None:
    if workflow_id <= 2 or not is_new_workflow_project(root, state):
        return
    artifacts = state.get("artifacts")
    artifact_path = None
    if isinstance(artifacts, dict) and isinstance(
        artifacts.get("idea_debate_report"), str
    ):
        artifact_path = artifacts["idea_debate_report"]
    history = state.get("history")
    history_has_wf2 = False
    if isinstance(history, list):
        for entry in history:
            if not isinstance(entry, dict):
                continue
            if (
                entry.get("workflow_id") == 2
                or entry.get("workflow_name") == "idea_debate"
            ):
                history_has_wf2 = True
                break
    doc_exists = (root / "docs" / "Idea_Debate.md").exists()
    artifact_exists = bool(artifact_path and (root / artifact_path).exists())
    if not (doc_exists or artifact_exists or history_has_wf2):
        add_check(
            checks,
            "wf2_required_for_new_project",
            False,
            "error",
            "New dynamic_context/standard projects past WF2 must show WF2 "
            "idea-debate completion via docs/Idea_Debate.md, "
            "artifacts.idea_debate_report, or PROJECT_STATE history.",
            "PROJECT_STATE.json",
        )


def check_lesson_candidates(
    checks: list[dict[str, Any]], iteration: dict[str, Any], path: str
) -> None:
    candidates = iteration.get("lesson_candidates")
    if candidates in (None, []):
        return
    if not isinstance(candidates, list):
        add_check(
            checks,
            "lesson_candidates_schema",
            False,
            "error",
            f"{iteration.get('id', '<unknown>')} lesson_candidates must be a list.",
            path,
        )
        return
    for index, candidate in enumerate(candidates, start=1):
        prefix = f"{iteration.get('id', '<unknown>')} lesson_candidates[{index}]"
        if not isinstance(candidate, dict):
            add_check(
                checks,
                "lesson_candidates_schema",
                False,
                "error",
                f"{prefix} must be an object.",
                path,
            )
            continue
        missing = [
            field
            for field in (
                "claim",
                "level",
                "confidence",
                "evidence",
                "promotion_status",
            )
            if field not in candidate
        ]
        if missing:
            add_check(
                checks,
                "lesson_candidates_schema",
                False,
                "error",
                f"{prefix} missing fields: {', '.join(missing)}.",
                path,
            )
        if candidate.get("level") not in VALID_LESSON_LEVELS:
            add_check(
                checks,
                "lesson_candidates_level",
                False,
                "error",
                f"{prefix}.level must be one of {sorted(VALID_LESSON_LEVELS)}.",
                path,
            )
        if candidate.get("confidence") not in VALID_CONFIDENCE:
            add_check(
                checks,
                "lesson_candidates_confidence",
                False,
                "error",
                f"{prefix}.confidence must be one of {sorted(VALID_CONFIDENCE)}.",
                path,
            )
        evidence = candidate.get("evidence")
        if (
            not isinstance(evidence, list)
            or not evidence
            or not all(isinstance(item, str) and item for item in evidence)
        ):
            add_check(
                checks,
                "lesson_candidates_evidence",
                False,
                "error",
                f"{prefix}.evidence must be a non-empty list of strings.",
                path,
            )
        if candidate.get("promotion_status") not in VALID_PROMOTION_STATUS:
            add_check(
                checks,
                "lesson_candidates_promotion_status",
                False,
                "error",
                f"{prefix}.promotion_status must be one of "
                f"{sorted(VALID_PROMOTION_STATUS)}.",
                path,
            )


def check_iteration_log(
    root: Path, checks: list[dict[str, Any]], state: dict[str, Any] | None
) -> dict[str, Any] | None:
    log = load_json_if_exists(
        root / "iteration_log.json", checks, "iteration_log.json", root
    )
    if log is None:
        return None

    iterations = log.get("iterations")
    if not isinstance(iterations, list):
        add_check(
            checks,
            "iteration_log_iterations",
            False,
            "error",
            "iteration_log.json iterations must be a list.",
            "iteration_log.json",
        )
        return log

    ids: list[str] = []
    completed_run_exp_dirs: dict[str, list[str]] = {}
    screening_run_exp_dirs: dict[str, list[str]] = {}
    tracked = tracked_metric_names(log.get("evaluation_protocol"))
    state_metric = None
    if state is not None:
        tracked |= tracked_metric_names(state.get("evaluation_protocol"))
        state_metric = primary_metric_name(state.get("evaluation_protocol"))
    log_metric = primary_metric_name(log.get("evaluation_protocol"))
    primary_metric = log_metric or state_metric
    if state_metric and log_metric and state_metric != log_metric:
        add_check(
            checks,
            "evaluation_protocol_primary_metric_consistency",
            False,
            "error",
            f"PROJECT_STATE primary metric {state_metric!r} does not match "
            f"iteration_log primary metric {log_metric!r}.",
            "iteration_log.json",
        )

    for iteration in iterations:
        if not isinstance(iteration, dict):
            add_check(
                checks,
                "iteration_entry_schema",
                False,
                "error",
                "Each iteration entry must be an object.",
                "iteration_log.json",
            )
            continue
        iteration_id = iteration.get("id")
        if not isinstance(iteration_id, str) or not iteration_id:
            add_check(
                checks,
                "iteration_id",
                False,
                "error",
                "Each iteration requires a non-empty string id.",
                "iteration_log.json",
            )
            continue
        ids.append(iteration_id)
        status = iteration.get("status")
        if status not in VALID_ITERATION_STATUSES:
            add_check(
                checks,
                "iteration_status",
                False,
                "error",
                f"{iteration_id} has unknown status {status!r}.",
                "iteration_log.json",
            )
        screening = iteration.get("screening")
        if isinstance(screening, dict) and screening.get("status") in {
            "passed",
            "failed",
        }:
            screening_metrics = screening.get("metrics")
            if not isinstance(screening_metrics, dict) or not screening_metrics:
                add_check(
                    checks,
                    "iteration_screening_metrics",
                    False,
                    "error",
                    f"{iteration_id} screening.metrics are required when "
                    "screening.status is passed or failed.",
                    "iteration_log.json",
                )
            elif tracked:
                unknown = sorted(set(screening_metrics) - tracked)
                if unknown:
                    add_check(
                        checks,
                        "iteration_screening_metric_protocol_consistency",
                        False,
                        "error",
                        f"{iteration_id} screening.metrics are not in tracked "
                        f"metric protocol: {', '.join(unknown)}.",
                        "iteration_log.json",
                    )
            screening_manifest = screening.get("run_manifest")
            if not isinstance(screening_manifest, dict) or not screening_manifest:
                add_check(
                    checks,
                    "iteration_screening_run_manifest",
                    False,
                    "error",
                    f"{iteration_id} screening.run_manifest is required.",
                    "iteration_log.json",
                )
            else:
                exp_dir = screening_manifest.get("exp_dir")
                if isinstance(exp_dir, str) and exp_dir.strip():
                    screening_run_exp_dirs.setdefault(
                        exp_dir.strip(),
                        [],
                    ).append(iteration_id)
                for artifact_error in run_artifact_errors(
                    root,
                    iteration,
                    run_manifest=screening_manifest,
                    manifest_name="screening.run_manifest",
                ):
                    add_check(
                        checks,
                        "iteration_screening_run_artifact_bundle",
                        False,
                        "error",
                        f"{iteration_id} {artifact_error}.",
                        "iteration_log.json",
                    )
        if status == "completed":
            decision = iteration.get("decision")
            if decision not in VALID_DECISIONS:
                add_check(
                    checks,
                    "iteration_completed_decision",
                    False,
                    "error",
                    f"{iteration_id} completed entry requires a valid decision.",
                    "iteration_log.json",
                )
            git_commit = iteration.get("git_commit")
            if not isinstance(git_commit, str) or not git_commit.strip():
                add_check(
                    checks,
                    "iteration_completed_git_commit",
                    False,
                    "error",
                    f"{iteration_id} completed entry requires git_commit.",
                    "iteration_log.json",
                )
            run_manifest = iteration.get("run_manifest")
            if not isinstance(run_manifest, dict) or not run_manifest:
                add_check(
                    checks,
                    "iteration_completed_run_manifest",
                    False,
                    "error",
                    f"{iteration_id} completed entry requires run_manifest.",
                    "iteration_log.json",
                )
            else:
                if (
                    not isinstance(run_manifest.get("command"), str)
                    or not run_manifest.get("command", "").strip()
                ):
                    add_check(
                        checks,
                        "iteration_completed_run_manifest",
                        False,
                        "error",
                        f"{iteration_id} run_manifest requires command.",
                        "iteration_log.json",
                    )
                if (
                    not isinstance(run_manifest.get("exp_dir"), str)
                    or not run_manifest.get("exp_dir", "").strip()
                ):
                    add_check(
                        checks,
                        "iteration_completed_run_manifest",
                        False,
                        "error",
                        f"{iteration_id} run_manifest requires exp_dir.",
                        "iteration_log.json",
                    )
                else:
                    exp_dir = run_manifest["exp_dir"].strip()
                    completed_run_exp_dirs.setdefault(exp_dir, []).append(iteration_id)
                    full_run = iteration.get("full_run")
                    screening_manifest = (
                        screening.get("run_manifest")
                        if isinstance(screening, dict)
                        else None
                    )
                    screening_exp_dir = (
                        screening_manifest.get("exp_dir")
                        if isinstance(screening_manifest, dict)
                        else None
                    )
                    if (
                        isinstance(full_run, dict)
                        and full_run.get("status") == "completed"
                        and isinstance(screening_exp_dir, str)
                        and screening_exp_dir.strip() == exp_dir
                    ):
                        add_check(
                            checks,
                            "iteration_run_exp_dirs_unique",
                            False,
                            "error",
                            (
                                f"{iteration_id} screening.run_manifest.exp_dir "
                                "must differ from run_manifest.exp_dir when "
                                "full_run.status=completed."
                            ),
                            "iteration_log.json",
                        )
                for artifact_error in run_artifact_errors(root, iteration):
                    add_check(
                        checks,
                        "iteration_run_artifact_bundle",
                        False,
                        "error",
                        f"{iteration_id} {artifact_error}.",
                        "iteration_log.json",
                    )
            if existing_iteration_report_path(root, iteration_id) is None:
                add_check(
                    checks,
                    "iteration_completed_report",
                    False,
                    "error",
                    (
                        f"{iteration_id} requires an iteration report at one of: "
                        f"{iteration_report_candidates_detail(root, iteration_id)}."
                    ),
                    "iteration_log.json",
                )
            if iteration_metrics_conflict(iteration):
                add_check(
                    checks,
                    "iteration_metric_location_conflict",
                    False,
                    "error",
                    f"{iteration_id} has conflicting metrics and full_run.metrics.",
                    "iteration_log.json",
                )
            metrics = iteration_metrics(iteration)
            if not isinstance(metrics, dict) or not metrics:
                add_check(
                    checks,
                    "iteration_completed_metrics",
                    False,
                    "error",
                    f"{iteration_id} completed entry requires metrics.",
                    "iteration_log.json",
                )
            elif tracked:
                unknown = sorted(set(metrics) - tracked)
                if unknown:
                    add_check(
                        checks,
                        "iteration_metric_protocol_consistency",
                        False,
                        "error",
                        f"{iteration_id} metrics are not in tracked metric "
                        f"protocol: {', '.join(unknown)}.",
                        "iteration_log.json",
                    )
            if primary_metric and isinstance(metrics, dict):
                if primary_metric not in metrics:
                    add_check(
                        checks,
                        "iteration_primary_metric_required",
                        False,
                        "error",
                        f"{iteration_id} metrics require primary metric "
                        f"{primary_metric!r}.",
                        "iteration_log.json",
                    )
                elif not numeric_metric_value(metrics[primary_metric]):
                    add_check(
                        checks,
                        "iteration_primary_metric_numeric",
                        False,
                        "error",
                        f"{iteration_id} primary metric {primary_metric!r} "
                        "must be numeric.",
                        "iteration_log.json",
                    )
            lessons = iteration.get("lessons")
            if not isinstance(lessons, list) or not lessons:
                add_check(
                    checks,
                    "iteration_completed_lessons",
                    False,
                    "error",
                    f"{iteration_id} completed entry requires lessons.",
                    "iteration_log.json",
                )
        check_lesson_candidates(checks, iteration, "iteration_log.json")

    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
    if duplicate_ids:
        add_check(
            checks,
            "iteration_ids_unique",
            False,
            "error",
            f"Duplicate iteration ids: {', '.join(duplicate_ids)}.",
            "iteration_log.json",
        )
    else:
        add_check(
            checks,
            "iteration_ids_unique",
            True,
            "info",
            "Iteration ids are unique.",
            "iteration_log.json",
        )

    duplicate_exp_dirs = {
        exp_dir: owners
        for exp_dir, owners in completed_run_exp_dirs.items()
        if len(owners) > 1
    }
    if duplicate_exp_dirs:
        detail = "; ".join(
            f"{exp_dir}: {', '.join(owners)}"
            for exp_dir, owners in sorted(duplicate_exp_dirs.items())
        )
        add_check(
            checks,
            "iteration_run_exp_dirs_unique",
            False,
            "error",
            f"Completed run_manifest.exp_dir values must be unique: {detail}.",
            "iteration_log.json",
        )

    duplicate_screening_exp_dirs = {
        exp_dir: owners
        for exp_dir, owners in screening_run_exp_dirs.items()
        if len(owners) > 1
    }
    if duplicate_screening_exp_dirs:
        detail = "; ".join(
            f"{exp_dir}: {', '.join(owners)}"
            for exp_dir, owners in sorted(duplicate_screening_exp_dirs.items())
        )
        add_check(
            checks,
            "iteration_screening_run_exp_dirs_unique",
            False,
            "error",
            "screening.run_manifest.exp_dir values must be unique: "
            f"{detail}.",
            "iteration_log.json",
        )

    best_iteration = log.get("best_iteration")
    if best_iteration and best_iteration not in ids:
        add_check(
            checks,
            "best_iteration_exists",
            False,
            "error",
            f"best_iteration {best_iteration!r} is not present in iterations.",
            "iteration_log.json",
        )

    if state is not None:
        stage = state.get("current_stage")
        if isinstance(stage, dict) and stage.get("workflow_name") == "iterate" and ids:
            latest = stage.get("latest_iteration")
            if latest and latest != ids[-1]:
                add_check(
                    checks,
                    "latest_iteration_consistency",
                    False,
                    "error",
                    f"PROJECT_STATE latest_iteration {latest!r} does not "
                    f"match latest iteration_log id {ids[-1]!r}.",
                    "PROJECT_STATE.json",
                )
    return log


def check_project_map(
    root: Path, checks: list[dict[str, Any]]
) -> dict[str, Any] | None:
    project_map = load_json_if_exists(
        root / "project_map.json", checks, "project_map.json", root
    )
    if project_map is None:
        return None
    for field in ("version", "updated_at", "detail_policy", "structure"):
        if field not in project_map:
            add_check(
                checks,
                "project_map_required_fields",
                False,
                "error",
                f"project_map.json missing required field {field}.",
                "project_map.json",
            )
    structure = project_map.get("structure")
    if isinstance(structure, dict):
        check_project_map_nodes(checks, structure, "project_map.json", "structure")
    elif "structure" in project_map:
        add_check(
            checks,
            "project_map_structure",
            False,
            "error",
            "project_map.json structure must be an object.",
            "project_map.json",
        )
    return project_map


def check_project_map_nodes(
    checks: list[dict[str, Any]], nodes: dict[str, Any], path: str, prefix: str
) -> None:
    for name, node in nodes.items():
        label = f"{prefix}.{name}"
        if not isinstance(node, dict):
            add_check(
                checks,
                "project_map_node_schema",
                False,
                "error",
                f"{label} must be an object.",
                path,
            )
            continue
        if node.get("type") not in {"directory", "file"}:
            add_check(
                checks,
                "project_map_node_type",
                False,
                "error",
                f"{label}.type must be directory or file.",
                path,
            )
        if not isinstance(node.get("description"), str) or not node.get("description"):
            add_check(
                checks,
                "project_map_node_description",
                False,
                "error",
                f"{label}.description is required.",
                path,
            )
        children = node.get("children")
        if children is not None:
            if isinstance(children, dict):
                check_project_map_nodes(checks, children, path, f"{label}.children")
            else:
                add_check(
                    checks,
                    "project_map_node_children",
                    False,
                    "error",
                    f"{label}.children must be an object.",
                    path,
                )


def check_auto_iterate_state(
    root: Path, checks: list[dict[str, Any]], log: dict[str, Any] | None
) -> None:
    auto_state = load_json_if_exists(
        root / ".auto_iterate" / "state.json", checks, ".auto_iterate/state.json", root
    )
    if auto_state is None:
        return
    iteration_id = auto_state.get("current_iteration_id")
    if not iteration_id:
        return
    ids = set()
    if isinstance(log, dict) and isinstance(log.get("iterations"), list):
        ids = {item.get("id") for item in log["iterations"] if isinstance(item, dict)}
    if iteration_id not in ids:
        add_check(
            checks,
            "auto_iterate_current_iteration_consistency",
            False,
            "error",
            ".auto_iterate/state.json current_iteration_id "
            f"{iteration_id!r} is not present in iteration_log.json.",
            ".auto_iterate/state.json",
        )


def gate_result(workspace_root: Path) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    checks: list[dict[str, Any]] = []
    state = check_project_state(workspace, checks)
    log = check_iteration_log(workspace, checks, state)
    check_project_map(workspace, checks)
    check_auto_iterate_state(workspace, checks, log)

    errors = [
        check for check in checks if check["severity"] == "error" and not check["ok"]
    ]
    warnings = [check for check in checks if check["severity"] == "warn"]
    return {
        "ok": not errors,
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def print_text(result: dict[str, Any]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print(f"{status} workflow state checks")
    for check in result["checks"]:
        marker = "OK" if check["ok"] else "NO"
        path = f" ({check['path']})" if check.get("path") else ""
        print(
            f"- [{marker}] {check['severity']}: {check['name']}{path} - "
            f"{check['detail']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Harness workflow state schemas and cross-file consistency."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = gate_result(args.workspace_root)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_text(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
