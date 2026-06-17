#!/usr/bin/env python3
"""Lightweight Harness workflow supervisor control CLI.

This controller owns only ``.workflow_supervisor/**``. It records typed state,
events, pending human requests, worker results, and validation results. It may
delegate nodes to structured workers, but it does not mark canonical workflow
stages complete or approve contracts by itself.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

EXIT_OK = 0
EXIT_INVALID_INPUT = 2
EXIT_NO_STATE = 3
EXIT_NO_ACTIVE_RUN = 4
EXIT_MANUAL_ACTION = 105
EXIT_FATAL = 109

SCHEMA_VERSION = 1
SUPERVISOR_DIR = ".workflow_supervisor"
DEFAULT_RECOVERY_STRATEGY = "adopt_if_postconditions_pass_else_rerun"
VALID_SEGMENTS = {"grill", "prepare", "build", "iterate", "release", "change"}
VALID_RUN_STATUSES = {
    "idle",
    "running",
    "paused",
    "failed",
    "completed",
    "stopped",
    "recovering",
}
VALID_PENDING_TYPES = {
    "ASK_INPUT",
    "APPROVE_ACTION",
    "STEER",
    "REVIEW_EDIT",
    "ESCALATE",
}
VALID_WORKER_STATUSES = {
    "success",
    "failed",
    "interrupt_requested",
    "not_run",
}
VALID_GATE_RESULTS = {"PASS", "FAIL", "NOT_RUN"}
VALID_WORKER_EVENT_PHASES = {
    "starting",
    "reading",
    "planning",
    "editing",
    "testing",
    "committing",
    "handoff",
    "blocked",
    "done",
}
WORKER_TELEMETRY_QUIET_AFTER_SECONDS = 300
WORKER_TELEMETRY_STALL_AFTER_SECONDS = 600
DIRECT_USER_QUESTION_MARKERS = (
    "asked the user",
    "ask the user",
    "asked you",
    "please provide",
    "can you provide",
    "could you provide",
    "请提供",
    "请告诉",
)
PREPARE_NON_UNLOCKING_STATUSES = {
    "prepare_hitl_poc",
    "prepare_revision_requested",
    "prepare_rejected",
}
AUTO_ITERATE_MANUAL_HALT_REASONS = {
    "manual_action_required": "auto_iterate_manual_action_required",
    "operator_pause": "auto_iterate_operator_pause",
}
RELEASE_ACTION_RESPONSES = ["validate", "package", "submit", "reject"]
VALID_CONDITION_TYPES = {
    "artifact_exists",
    "artifact_matches_schema",
    "command_passes",
    "docchain_gate_passes",
    "dynamic_context_gate_passes",
    "git_worktree_clean",
    "review_packet_exists",
    "approval_recorded",
    "auto_iterate_status",
    "no_forbidden_writes",
    "sliced_commits_recorded",
}
VALID_NODE_RUN_WHEN = {"always", "on_failure", "manual"}
FORBIDDEN_WORKER_WRITE_PREFIXES = (
    ".evidence/",
    ".auto_iterate/",
    ".workflow_supervisor/",
    "docs/_views/",
    "docs/_site/",
)
GIT_WORKTREE_CLEAN_IGNORE_PREFIXES = (
    *FORBIDDEN_WORKER_WRITE_PREFIXES,
    ".agents/state/workflow_supervisor_worker_results/",
)
CODEX_WORKER_SANDBOX_ARGS = ["--full-auto"]
DEFAULT_AUTOMATION_POLICY = {
    "profile": "default",
    "worker_prompt_max_chars": 6000,
    "goal_max_chars": 1200,
    "json_context_max_chars": 1800,
    "worker_result_max_chars": 4000,
    "gate_ledger_context_max_entries": 5,
    "gate_cycle_limit": 3,
}
GATE_POLICY_REF = "tooling/workflow_supervisor/config/gate_policy.yaml"
AUTOMATION_POLICY_INT_FIELDS = {
    "worker_prompt_max_chars",
    "goal_max_chars",
    "json_context_max_chars",
    "worker_result_max_chars",
    "gate_ledger_context_max_entries",
    "gate_cycle_limit",
    "node_retry_limit",
}
SEGMENT_AUTOMATION_POLICIES = {
    "prepare": {
        "profile": "automation_prepare",
        "goal_max_chars": 1000,
        "gate_cycle_limit": 2,
    },
    "build": {
        "profile": "automation_build",
        "goal_max_chars": 1400,
        "gate_cycle_limit": 3,
    },
    "iterate": {
        "profile": "automation_iterate",
        "goal_max_chars": 1200,
        "gate_cycle_limit": 2,
    },
    "release": {
        "profile": "conservative_release",
        "goal_max_chars": 1000,
        "gate_cycle_limit": 1,
    },
    "change": {
        "profile": "change_intake",
        "goal_max_chars": 1000,
        "gate_cycle_limit": 1,
    },
}
SEGMENT_GATE_PROFILES = {
    "build": "automation_build",
    "iterate": "automation_iterate",
    "release": "conservative_release",
    "change": "change_intake",
}
GRILL_ARTIFACT_REFS = (
    "docs/05_intake/Execution_Readiness_Packet.md",
    "docs/05_intake/Research_Intent_Draft.md",
    "docs/05_intake/Grill_Round_Log.md",
)
GRILL_BRIDGE_KEYS = {
    "dataset_source",
    "dataset_remote",
    "dataset_root",
    "dataset_root_wsl",
    "dataset_path",
    "dataset_target",
    "dataset_download_dir",
    "baseline_repo",
    "baseline_source",
    "baseline_cache",
    "baseline_target",
    "baseline_download_dir",
    "external_download_policy",
    "allow_external_downloads",
    "hf_access_policy",
    "baseline_clone_policy",
    "operator_approved_at",
}
GRILL_KEY_ALIASES = {
    "dataset_url": "dataset_source",
    "dataset_remote": "dataset_source",
    "dataset_source": "dataset_source",
    "dataset_download_url": "dataset_source",
    "data_source": "dataset_source",
    "data_url": "dataset_source",
    "dataset_root": "dataset_root",
    "dataset_root_wsl": "dataset_root",
    "dataset_path": "dataset_root",
    "dataset_target": "dataset_root",
    "dataset_download_dir": "dataset_root",
    "dataset_dir": "dataset_root",
    "data_root": "dataset_root",
    "data_path": "dataset_root",
    "data_dir": "dataset_root",
    "baseline_repo": "baseline_repo",
    "baseline_source": "baseline_repo",
    "baseline_url": "baseline_repo",
    "baseline_git": "baseline_repo",
    "baseline_repository": "baseline_repo",
    "baseline_clone": "baseline_repo",
    "baseline_cache": "baseline_cache",
    "baseline_target": "baseline_cache",
    "baseline_download_dir": "baseline_cache",
    "baseline_dir": "baseline_cache",
    "external_download_policy": "external_download_policy",
    "allow_external_downloads": "external_download_policy",
    "download_policy": "external_download_policy",
    "hf_access_policy": "hf_access_policy",
    "hf_auth_policy": "hf_access_policy",
    "hugging_face_access_policy": "hf_access_policy",
    "huggingface_access_policy": "hf_access_policy",
    "baseline_clone_policy": "baseline_clone_policy",
    "baseline_download_policy": "baseline_clone_policy",
    "operator_approved_at": "operator_approved_at",
    "operator_approval_time": "operator_approved_at",
}
STRUCTURED_READINESS_DEFAULTS: dict[str, Any] = {
    "external_download_policy": "unset",
    "approved_datasets": [],
    "approved_baselines": [],
    "target_paths": {},
    "unknowns": [],
    "operator_approved_at": None,
}
GRILL_REDACTED_VALUES = {
    "",
    "pending",
    "redacted",
    "<redacted>",
    "unknown",
    "none",
    "n/a",
    "na",
    "not run",
    "candidate",
}
CONTEXTUAL_DATASET_URL_LABELS = {
    "dataset_source",
    "dataset_url",
    "dataset_remote",
    "dataset_download_url",
    "data_source",
    "data_url",
}
CONTEXTUAL_BASELINE_URL_LABELS = {
    "baseline_repo",
    "baseline_source",
    "baseline_url",
    "baseline_git",
    "baseline_repository",
    "baseline_clone",
}
DATASET_TABLE_SOURCE_HEADERS = {
    "source",
    "source_url",
    "source_url_or_official_entrypoint",
    "url",
    "remote",
    "dataset_source",
    "download_source",
    "official_entrypoint",
    "repository",
    "repo",
}
DATASET_TABLE_ID_HEADERS = {"dataset_id", "dataset", "id", "name"}
BASELINE_TABLE_SOURCE_HEADERS = {
    "code_repository_or_entrypoint",
    "code_repository",
    "repository",
    "repo",
    "source",
    "official_code_entrypoint",
    "entrypoint",
    "baseline_repo",
}
BASELINE_TABLE_ID_HEADERS = {
    "baseline_id",
    "baseline",
    "baseline_id_name",
    "id",
    "name",
}
DATASET_REJECT_MARKERS = {
    "operator_reported_unavailable",
    "baidu_request_gated",
    "request_gated",
    "request_required",
    "registration_required",
    "challenge_gated",
    "challenge_account_gated",
    "challenge_gated_no_download",
    "do_not_download",
    "not_downloaded_under_current_policy",
    "excluded_from_download",
    "reference_future_approval",
    "future_approval_only",
    "method_reference_only",
    "reference_only",
    "p2_request_only",
    "not_executable",
    "not_executable_now",
    "no_accessible_source",
    "baseline_repo_missing",
    "repo_missing",
    "code_missing",
    "reported_method",
    "blocked_do_not",
    "rejected",
}
DATASET_REQUIRES_APPROVAL_MARKERS = {
    "requires_approval",
    "approval_required",
    "separate_approval",
    "separately_approved",
    "future_approval",
    "human_approval",
}
DATASET_DEFER_MARKERS = {
    "deferred",
    "not_publicly_verified",
    "public_download_not_verified",
    "exclude_from_early",
    "exclude_from_early_subset",
    "future_baseline",
    "future_dataset",
    "p2",
}
DATASET_CANDIDATE_MARKERS = {
    "hf_auth_accepted",
    "github_conference_set_available",
    "github_google_drive_candidate",
    "public_synthetic_candidate",
    "public_sample",
    "public_zenodo",
    "public_with_terms",
    "download_check_early",
    "use_early",
    "use_as",
    "p0",
    "p1",
    "candidate",
}
DATASET_LOCAL_SOURCE_MARKERS = {
    "already_local",
    "already_downloaded",
    "local_probe_verified",
    "operator_reported_downloaded",
}
DATASET_DECISION_PRIORITY = {
    "candidate": 0,
    "deferred": 1,
    "requires_approval": 2,
    "rejected": 3,
}
CREATABLE_READINESS_PATH_KEYS = {
    "dataset_root",
    "dataset_path",
    "dataset_target",
    "dataset_download_dir",
    "baseline_cache",
    "baseline_target",
    "baseline_download_dir",
}
CHANGE_CONTEXT_INPUTS = [
    "PROJECT_STATE.json",
    "project_map.json",
    "docs/20_facts/Codebase_Map.md",
    "docs/10_contract/Project_Contract.md",
    "docs/10_contract/Evaluation_Contract.md",
    "docs/10_contract/Baseline_Contract.md",
    "docs/10_contract/Claim_Boundary.md",
    "iteration_log.json",
]
CHANGE_ROUTE_BY_TYPE = {
    "bugfix": "code-debug",
    "experiment_delta": "iterate",
    "stable_code_delta": "build_delta",
    "architecture_delta": "delta_grill",
    "evaluation_delta": "review_packet",
    "claim_boundary_delta": "claim_boundary_review",
    "new_research_direction": "delta_grill",
    "harness_guardrail_delta": "harness-maintenance",
    "unknown": "steer",
}
CHANGE_PRIORITY = [
    "harness_guardrail_delta",
    "claim_boundary_delta",
    "evaluation_delta",
    "architecture_delta",
    "new_research_direction",
    "experiment_delta",
    "bugfix",
    "stable_code_delta",
]
CHANGE_KEYWORDS = {
    "bugfix": [
        "bug",
        "fix",
        "failing",
        "failed",
        "failure",
        "traceback",
        "exception",
        "error",
        "crash",
        "regression",
        "broken",
        "报错",
        "修复",
        "失败",
        "异常",
        "回归",
    ],
    "experiment_delta": [
        "experiment",
        "ablation",
        "hyperparam",
        "tune",
        "tuning",
        "loss",
        "schedule",
        "train",
        "training",
        "learning rate",
        "lr",
        "run another",
        "实验",
        "调参",
        "消融",
        "训练",
        "学习率",
    ],
    "stable_code_delta": [
        "feature",
        "helper",
        "refactor",
        "optimize",
        "performance",
        "config key",
        "data transform",
        "implementation",
        "implement",
        "add",
        "support",
        "新增",
        "支持",
        "重构",
        "优化",
        "实现",
    ],
    "architecture_delta": [
        "architecture",
        "model structure",
        "backbone",
        "public api",
        "interface",
        "data flow",
        "pipeline",
        "module boundary",
        "redesign",
        "架构",
        "核心模型",
        "数据流",
        "接口",
        "模块边界",
    ],
    "evaluation_delta": [
        "evaluation",
        "metric",
        "primary metric",
        "benchmark",
        "baseline",
        "validation protocol",
        "eval protocol",
        "evaluation contract",
        "baseline contract",
        "评估",
        "指标",
        "主指标",
        "基线",
        "验证协议",
    ],
    "claim_boundary_delta": [
        "claim",
        "claim boundary",
        "conclusion",
        "paper",
        "abstract",
        "release claim",
        "stronger claim",
        "result interpretation",
        "结论",
        "声明",
        "论文",
        "摘要",
        "更强 claim",
    ],
    "new_research_direction": [
        "new research",
        "new idea",
        "new direction",
        "pivot",
        "different task",
        "new task",
        "new branch",
        "new dataset",
        "new domain",
        "新方向",
        "新 idea",
        "新想法",
        "换方向",
        "另一个任务",
        "新分支",
    ],
    "harness_guardrail_delta": [
        "harness",
        "hook",
        "hooks",
        "codex hook",
        "skill contract",
        "skill contracts",
        "workflow supervisor",
        "grill",
        "permission policy",
        "guardrail",
        "routing",
        "change-intake",
        "harness-maintenance",
        "tooling/codex_hooks",
        ".agents",
        ".claude",
        "schemas/skill_contracts.json",
        "工作流监督",
        "护栏",
        "权限策略",
    ],
}
PATH_HINT_RE = re.compile(
    r"(?<![\w./-])"
    r"((?:\.?[A-Za-z0-9_-]+/)+[A-Za-z0-9_.-]+|"
    r"\.?[A-Za-z0-9_-]+\.(?:py|md|json|yaml|yml|toml|txt|sh))"
    r"(?![\w./-])"
)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def repo_root(cwd: str | Path | None = None) -> Path:
    start = Path(cwd or os.getcwd()).resolve()
    for path in [start, *start.parents]:
        if (path / ".git").exists() or (path / "schemas").exists():
            return path
    return start


def supervisor_root(workspace_root: Path) -> Path:
    return workspace_root / SUPERVISOR_DIR


def state_path(workspace_root: Path) -> Path:
    return supervisor_root(workspace_root) / "state.json"


def pending_request_path(workspace_root: Path) -> Path:
    return supervisor_root(workspace_root) / "pending_request.json"


def events_path(workspace_root: Path) -> Path:
    return supervisor_root(workspace_root) / "events.jsonl"


def lock_path(workspace_root: Path) -> Path:
    return supervisor_root(workspace_root) / "lock.json"


def config_path(workspace_root: Path) -> Path:
    return (
        workspace_root
        / "tooling"
        / "workflow_supervisor"
        / "config"
        / "default_nodes.json"
    )


def workflow_tooling_root() -> Path:
    return Path(__file__).resolve().parents[2]


def evidence_script_path(workspace_root: Path, script_name: str) -> Path:
    workspace_script = workspace_root / "tooling" / "evidence" / script_name
    if workspace_script.exists():
        return workspace_script
    framework_script = workflow_tooling_root() / "evidence" / script_name
    if framework_script.exists():
        return framework_script
    raise ValueError(f"missing evidence tooling script: {script_name}")


def auto_iterate_ctl_path(workspace_root: Path) -> Path:
    workspace_script = (
        workspace_root / "tooling" / "auto_iterate" / "scripts" / "auto_iterate_ctl.py"
    )
    if workspace_script.exists():
        return workspace_script
    framework_script = (
        workflow_tooling_root() / "auto_iterate" / "scripts" / "auto_iterate_ctl.py"
    )
    if framework_script.exists():
        return framework_script
    raise ValueError("missing auto-iterate controller CLI")


def schemas_root(workspace_root: Path) -> Path:
    return workspace_root / "schemas"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None


def load_json_if_exists(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return load_json(path)


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(data: Any) -> str:
    return sha256_text(canonical_json(data))


def request_snapshot_payload(request: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(request)
    payload.pop("answer_record", None)
    payload.pop("approval_record", None)
    return payload


def request_snapshot_hash(request: dict[str, Any]) -> str:
    payload = request_snapshot_payload(request)
    payload.pop("request_snapshot_hash", None)
    return sha256_json(payload)


def exact_action_hash(exact_action: dict[str, Any]) -> str:
    payload = copy.deepcopy(exact_action)
    payload.pop("action_hash", None)
    return sha256_json(payload)


def validate_schema(
    workspace_root: Path,
    data: dict[str, Any],
    schema_name: str,
    label: str,
) -> list[str]:
    schema = load_json(schemas_root(workspace_root) / schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    rendered: list[str] = []
    for error in errors:
        location = label
        for part in error.path:
            location += f"[{part}]" if isinstance(part, int) else f".{part}"
        rendered.append(f"{location}: {error.message}")
    return rendered


def read_events(workspace_root: Path) -> list[dict[str, Any]]:
    path = events_path(workspace_root)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from None
        if not isinstance(event, dict):
            raise ValueError(f"{path}:{line_number}: event must be an object")
        events.append(event)
    return events


def latest_event_seq(workspace_root: Path) -> int:
    events = read_events(workspace_root)
    seq_values = [event.get("seq") for event in events]
    ints = [value for value in seq_values if isinstance(value, int)]
    return max(ints, default=0)


def append_event(
    workspace_root: Path,
    event: str,
    *,
    run_id: str | None,
    segment: str | None,
    node_id: str | None = None,
    status: str | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    seq = latest_event_seq(workspace_root) + 1
    record = {
        "v": 1,
        "seq": seq,
        "ts": utc_now(),
        "event": event,
        "run_id": run_id,
        "segment": segment,
        "node_id": node_id,
        "status": status,
        "payload": payload or {},
    }
    path = events_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return seq


def parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def seconds_since(value: Any) -> int | None:
    parsed = parse_utc_timestamp(value)
    if parsed is None:
        return None
    delta = datetime.now(timezone.utc) - parsed
    return max(0, int(delta.total_seconds()))


def worker_runtime_paths(
    workspace_root: Path,
    *,
    run_id: str,
    node_id: str,
) -> dict[str, str]:
    base = supervisor_root(workspace_root) / "runs" / run_id / "runtime"
    handoff_base = (
        workspace_root
        / ".agents"
        / "state"
        / "workflow_supervisor_worker_results"
        / run_id
    )
    return {
        "result": (base / f"{node_id}.worker_result.json").relative_to(
            workspace_root
        ).as_posix(),
        "handoff_result": (handoff_base / f"{node_id}.worker_result.json").relative_to(
            workspace_root
        ).as_posix(),
        "prompt": (base / f"{node_id}.prompt.txt").relative_to(
            workspace_root
        ).as_posix(),
        "stdout": (base / f"{node_id}.stdout.log").relative_to(
            workspace_root
        ).as_posix(),
        "stderr": (base / f"{node_id}.stderr.log").relative_to(
            workspace_root
        ).as_posix(),
        "worker_status": (base / f"{node_id}.worker_status.json").relative_to(
            workspace_root
        ).as_posix(),
        "worker_events": (base / f"{node_id}.worker_events.jsonl").relative_to(
            workspace_root
        ).as_posix(),
    }


def worker_telemetry_refs(
    workspace_root: Path,
    *,
    run_id: str,
    node_id: str,
) -> dict[str, str]:
    paths = worker_runtime_paths(workspace_root, run_id=run_id, node_id=node_id)
    return {
        "worker_status_ref": paths["worker_status"],
        "worker_events_ref": paths["worker_events"],
        "stdout_ref": paths["stdout"],
        "stderr_ref": paths["stderr"],
        "result_ref": paths["result"],
        "handoff_result_ref": paths["handoff_result"],
    }


def append_worker_event(
    workspace_root: Path,
    *,
    run_id: str,
    node_id: str,
    phase: str,
    message: str,
    source: str = "worker",
    command: str | None = None,
    result: str | None = None,
    artifacts: list[str] | None = None,
    timeout_seconds: int | None = None,
    pid: int | None = None,
    skill: str | None = None,
) -> dict[str, Any]:
    if phase not in VALID_WORKER_EVENT_PHASES:
        raise ValueError(
            f"phase must be one of {sorted(VALID_WORKER_EVENT_PHASES)}"
        )
    if result is not None and result not in VALID_GATE_RESULTS:
        raise ValueError(f"result must be one of {sorted(VALID_GATE_RESULTS)}")
    paths = worker_runtime_paths(workspace_root, run_id=run_id, node_id=node_id)
    now = utc_now()
    event = {
        "v": 1,
        "ts": now,
        "run_id": run_id,
        "node_id": node_id,
        "phase": phase,
        "message": message,
        "source": source,
        "command": command,
        "result": result,
        "artifacts": artifacts or [],
        "worker_pid": pid,
    }
    event_path = workspace_root / paths["worker_events"]
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    status_path = workspace_root / paths["worker_status"]
    previous = load_json_if_exists(status_path, {})
    if not isinstance(previous, dict):
        previous = {}
    started_at = previous.get("started_at") if previous.get("started_at") else now
    snapshot: dict[str, Any] = {
        **previous,
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "node_id": node_id,
        "skill": skill if skill is not None else previous.get("skill"),
        "worker_pid": pid if pid is not None else previous.get("worker_pid"),
        "started_at": started_at,
        "updated_at": now,
        "last_semantic_event_at": now,
        "phase": phase,
        "last_message": message,
        "current_command": command,
        "reported_result": result,
        "artifacts": artifacts or previous.get("artifacts", []),
        "timeout_seconds": (
            timeout_seconds
            if timeout_seconds is not None
            else previous.get("timeout_seconds")
        ),
        **worker_telemetry_refs(workspace_root, run_id=run_id, node_id=node_id),
    }
    atomic_write_json(status_path, snapshot)
    return snapshot


def load_state(workspace_root: Path) -> dict[str, Any]:
    data = load_json(state_path(workspace_root))
    if not isinstance(data, dict):
        raise ValueError(f"{state_path(workspace_root)} must contain an object")
    return data


def save_state(workspace_root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    state["last_event_seq"] = latest_event_seq(workspace_root)
    errors = validate_state_invariants(state, workspace_root)
    if errors:
        raise ValueError("; ".join(errors))
    atomic_write_json(state_path(workspace_root), state)
    write_stage_summary(workspace_root, state)


def write_stage_summary(workspace_root: Path, state: dict[str, Any]) -> None:
    run_id = state.get("active_run_id")
    if not isinstance(run_id, str) or not run_id:
        return
    run_dir = supervisor_root(workspace_root) / "runs" / run_id
    node_dir = run_dir / "node_runs"
    pending_ref = None
    if pending_request_path(workspace_root).exists():
        pending = load_json(pending_request_path(workspace_root))
        if isinstance(pending, dict):
            pending_ref = pending.get("request_id")

    node_records: list[dict[str, Any]] = []
    if node_dir.exists():
        for path in sorted(node_dir.glob("*.json")):
            record = load_json(path)
            if isinstance(record, dict):
                node_records.append(record)

    lines = [
        "# Workflow Supervisor Run Summary",
        "",
        f"- run_id: {run_id}",
        f"- segment: {state.get('segment')}",
        f"- status: {state.get('status')}",
        f"- segment_status: {state.get('segment_status')}",
        f"- current_node_id: {state.get('current_node_id')}",
        f"- pending_request_id: {state.get('pending_request_id') or pending_ref}",
        "",
        "## Nodes",
        "",
    ]
    if node_records:
        lines.extend(["| Node | Status | Gate Result |", "| --- | --- | --- |"])
        for record in node_records:
            gates = record.get("gate_ledger", [])
            gate_results = []
            if isinstance(gates, list):
                gate_results = [
                    str(gate.get("result"))
                    for gate in gates
                    if isinstance(gate, dict) and gate.get("result")
                ]
            lines.append(
                "| {node} | {status} | {gates} |".format(
                    node=record.get("node_id"),
                    status=record.get("status"),
                    gates=", ".join(gate_results) if gate_results else "not recorded",
                )
            )
    else:
        lines.append("- No node records written yet.")

    lines.extend(["", "## Gate Ledger", ""])
    gate_count = 0
    for record in node_records:
        gates = record.get("gate_ledger", [])
        if not isinstance(gates, list):
            continue
        for gate in gates:
            if not isinstance(gate, dict):
                continue
            gate_count += 1
            artifacts = gate.get("artifacts", [])
            artifact_text = (
                "; ".join(str(item) for item in artifacts)
                if isinstance(artifacts, list)
                else str(artifacts)
            )
            lines.extend(
                [
                    f"- command: {gate.get('command')}",
                    f"  result: {gate.get('result')}",
                    f"  reason: {gate.get('reason')}",
                    f"  artifacts: {artifact_text}",
                ]
            )
    if gate_count == 0:
        lines.append("- command: not run")
        lines.append("  result: NOT_RUN")
        lines.append("  reason: no node gate ledger has been recorded yet")
        lines.append("  artifacts: ")

    lines.extend(
        [
            "",
            "## Next Safe Action",
            "",
            "- Resolve the pending request if one exists; otherwise inspect status "
            "and segment_status before starting another segment.",
            "",
        ]
    )
    atomic_write_text(run_dir / "stage_summary.md", "\n".join(lines))


def _process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _clear_stale_lock(path: Path) -> None:
    if not path.exists():
        return
    lock = load_json(path)
    if not isinstance(lock, dict):
        raise ValueError(f"invalid supervisor lock at {path}: expected object")
    pid = lock.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError(f"supervisor lock already exists with invalid pid: {path}")
    if _process_is_alive(pid):
        raise ValueError(f"supervisor lock already exists: {path}")
    current_lock = load_json_if_exists(path, None)
    if current_lock is None:
        return
    if current_lock != lock:
        raise ValueError(f"supervisor lock changed while checking stale lock: {path}")
    path.unlink()


def acquire_lock(workspace_root: Path, run_id: str) -> None:
    path = lock_path(workspace_root)
    _clear_stale_lock(path)
    if path.exists():
        raise ValueError(f"supervisor lock already exists: {path}")
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "pid": os.getpid(),
            "acquired_at": utc_now(),
        },
    )


def release_lock(workspace_root: Path, run_id: str) -> None:
    path = lock_path(workspace_root)
    if not path.exists():
        return
    lock = load_json_if_exists(path, {})
    if isinstance(lock, dict) and lock.get("run_id") == run_id:
        path.unlink()


def validate_state_invariants(
    state: dict[str, Any],
    workspace_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    status = state.get("status")
    if status not in VALID_RUN_STATUSES:
        errors.append(f"status must be one of {sorted(VALID_RUN_STATUSES)}")
    segment = state.get("segment")
    if segment is not None and segment not in VALID_SEGMENTS:
        errors.append(f"segment must be one of {sorted(VALID_SEGMENTS)}")
    if status == "paused":
        if not state.get("pending_request_id"):
            errors.append("status=paused requires pending_request_id")
        if (
            workspace_root is not None
            and not pending_request_path(workspace_root).exists()
        ):
            errors.append("status=paused requires pending_request.json")
    if status == "running":
        if not state.get("active_run_id"):
            errors.append("status=running requires active_run_id")
        if not state.get("current_node_id"):
            errors.append("status=running requires current_node_id")
        if workspace_root is not None and not lock_path(workspace_root).exists():
            errors.append("status=running requires lock.json")
    if status == "completed" and state.get("pending_request_id"):
        errors.append("status=completed must not have pending_request_id")
    return errors


def run_manifest(
    *,
    workspace_root: Path,
    run_id: str,
    segment: str,
    goal: str,
    entrypoint: str,
    allow_external_downloads: bool = False,
    worker_mode: str = "none",
    worker_command: str | None = None,
    codex_home: str | None = None,
    complete_prepare: bool = False,
    grill_bridge_ref: str | None = None,
) -> dict[str, Any]:
    commit = ""
    dirty = None
    git_dir = workspace_root / ".git"
    if git_dir.exists():
        commit_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        commit = commit_proc.stdout.strip() if commit_proc.returncode == 0 else ""
        dirty_proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        dirty = bool(dirty_proc.stdout.strip()) if dirty_proc.returncode == 0 else None
    expected_llm_calls = 0
    if worker_mode == "codex":
        try:
            registry = load_node_registry(workspace_root)
            expected_llm_calls = len(ordered_segment_nodes(registry, segment))
        except ValueError:
            expected_llm_calls = 1
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "segment": segment,
        "started_at": utc_now(),
        "started_by": "cli",
        "workspace_root": str(workspace_root),
        "base_git_commit": commit,
        "base_git_dirty": dirty,
        "goal": goal,
        "entrypoint": entrypoint,
        "policy": {
            "max_llm_calls": expected_llm_calls,
            "max_node_attempts": 1,
            "pause_on_gate_fail": True,
            "allow_external_downloads": allow_external_downloads,
            "worker_mode": worker_mode,
            "worker_command": worker_command,
            "codex_home": codex_home,
            "complete_prepare": complete_prepare,
            "grill_bridge_ref": grill_bridge_ref,
            "gate_policy_ref": GATE_POLICY_REF,
            "gate_profile": gate_profile_for_run(
                segment,
                complete_prepare=complete_prepare,
            ),
        },
    }


def active_node_definition(
    workspace_root: Path,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    node_id = state.get("current_node_id")
    segment = state.get("segment")
    if not isinstance(node_id, str) or not node_id:
        return None
    if not isinstance(segment, str) or not segment:
        return None
    try:
        registry = load_node_registry(workspace_root)
    except ValueError:
        return None
    for node in registry.get("nodes", []):
        if (
            isinstance(node, dict)
            and node.get("node_id") == node_id
            and node.get("segment") == segment
        ):
            return node
    return None


def durable_dirty_paths(workspace_root: Path) -> list[str]:
    if not (workspace_root / ".git").exists():
        return []
    return [
        path
        for path in git_status_paths(workspace_root)
        if not any(
            path.startswith(pattern)
            for pattern in GIT_WORKTREE_CLEAN_IGNORE_PREFIXES
        )
    ]


def load_worker_status(
    workspace_root: Path,
    *,
    run_id: str,
    node_id: str,
) -> dict[str, Any] | None:
    path = workspace_root / worker_runtime_paths(
        workspace_root,
        run_id=run_id,
        node_id=node_id,
    )["worker_status"]
    if not path.exists():
        return None
    data = load_json(path)
    if not isinstance(data, dict):
        return None
    return data


def result_path_exists(
    workspace_root: Path,
    *,
    run_id: str,
    node_id: str,
) -> bool:
    paths = worker_runtime_paths(workspace_root, run_id=run_id, node_id=node_id)
    return (workspace_root / paths["result"]).exists() or (
        workspace_root / paths["handoff_result"]
    ).exists()


def process_liveness(pid: Any) -> bool | None:
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def classify_worker_state(
    workspace_root: Path,
    *,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    run_id = state.get("active_run_id")
    node_id = state.get("current_node_id")
    if not isinstance(run_id, str) or not run_id:
        return None
    if not isinstance(node_id, str) or not node_id:
        return None
    node = active_node_definition(workspace_root, state)
    status = load_worker_status(workspace_root, run_id=run_id, node_id=node_id)
    status_timeout = status.get("timeout_seconds") if isinstance(status, dict) else None
    if isinstance(node, dict):
        timeout_seconds = int(node.get("timeout_seconds", 900))
    elif isinstance(status_timeout, int):
        timeout_seconds = status_timeout
    else:
        timeout_seconds = None
    refs = worker_telemetry_refs(workspace_root, run_id=run_id, node_id=node_id)
    dirty_paths = durable_dirty_paths(workspace_root)
    has_result = result_path_exists(workspace_root, run_id=run_id, node_id=node_id)
    started_at = status.get("started_at") if isinstance(status, dict) else None
    last_semantic_event_at = (
        status.get("last_semantic_event_at") if isinstance(status, dict) else None
    )
    elapsed_seconds = seconds_since(started_at)
    semantic_age_seconds = seconds_since(last_semantic_event_at)
    phase = status.get("phase") if isinstance(status, dict) else None
    worker_pid = status.get("worker_pid") if isinstance(status, dict) else None
    process_alive = process_liveness(worker_pid)
    telemetry_state = "unknown"
    recommended_action = "inspect_tail"
    if has_result:
        telemetry_state = "result_ready"
        recommended_action = "recover"
    elif process_alive is False and status is not None:
        telemetry_state = "worker_exited_no_result"
        recommended_action = "recover"
    elif dirty_paths and status is not None and phase in {"blocked", "done"}:
        telemetry_state = "dirty_no_result"
        recommended_action = "manual_recovery"
    elif timeout_seconds is not None and elapsed_seconds is not None and (
        elapsed_seconds >= timeout_seconds
    ):
        telemetry_state = "timed_out"
        recommended_action = "stop"
    elif semantic_age_seconds is None:
        telemetry_state = "unknown"
        recommended_action = "inspect_tail"
    elif semantic_age_seconds >= WORKER_TELEMETRY_STALL_AFTER_SECONDS:
        telemetry_state = "stalled"
        recommended_action = "recover"
    elif semantic_age_seconds >= WORKER_TELEMETRY_QUIET_AFTER_SECONDS:
        telemetry_state = "quiet_alive"
        recommended_action = "inspect_tail"
    else:
        telemetry_state = "healthy"
        recommended_action = "wait"
    if state.get("status") != "running" and telemetry_state not in {"result_ready"}:
        recommended_action = "status_only"
    return {
        "run_id": run_id,
        "node_id": node_id,
        "skill": node.get("skill") if isinstance(node, dict) else None,
        "telemetry_state": telemetry_state,
        "recommended_action": recommended_action,
        "elapsed_seconds": elapsed_seconds,
        "timeout_seconds": timeout_seconds,
        "semantic_age_seconds": semantic_age_seconds,
        "last_semantic_event_at": last_semantic_event_at,
        "last_phase": phase,
        "worker_pid": worker_pid,
        "process_alive": process_alive,
        "last_message": status.get("last_message")
        if isinstance(status, dict)
        else None,
        "current_command": status.get("current_command")
        if isinstance(status, dict)
        else None,
        "reported_result": status.get("reported_result")
        if isinstance(status, dict)
        else None,
        "dirty_paths": dirty_paths,
        "dirty_paths_count": len(dirty_paths),
        "result_exists": has_result,
        "status_exists": status is not None,
        **refs,
    }


def gate_profile_for_run(segment: str, *, complete_prepare: bool = False) -> str:
    if segment == "prepare" and complete_prepare:
        return "automation_prepare"
    return SEGMENT_GATE_PROFILES.get(segment, "default")


def new_run_id() -> str:
    return "sup_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def new_request_id() -> str:
    return "req_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def read_goal(args: argparse.Namespace) -> str:
    if args.goal and args.goal_file:
        raise ValueError("use either --goal or --goal-file, not both")
    if args.goal:
        return str(args.goal).strip()
    if args.goal_file:
        path = Path(args.goal_file)
        return path.read_text(encoding="utf-8").strip()
    raise ValueError("start requires --goal or --goal-file")


def base_state(run_id: str, segment: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "active_run_id": run_id,
        "status": "running",
        "segment": segment,
        "segment_status": None,
        "current_node_id": "dry_run_bootstrap",
        "current_attempt": 1,
        "pending_request_id": None,
        "last_event_seq": 0,
        "completed_nodes": [],
        "failed_nodes": [],
        "resolved_inputs_ref": None,
        "last_failure": None,
        "recovery_strategy": DEFAULT_RECOVERY_STRATEGY,
        "updated_at": utc_now(),
    }


def write_run_manifest(workspace_root: Path, manifest: dict[str, Any]) -> Path:
    run_id = str(manifest["run_id"])
    path = supervisor_root(workspace_root) / "runs" / run_id / "run_manifest.json"
    atomic_write_json(path, manifest)
    return path


def update_run_manifest_policy(
    workspace_root: Path,
    *,
    run_id: str,
    updates: dict[str, Any],
) -> None:
    path = supervisor_root(workspace_root) / "runs" / run_id / "run_manifest.json"
    manifest = load_json(path)
    if not isinstance(manifest, dict):
        raise ValueError("run manifest must be an object")
    policy = manifest.setdefault("policy", {})
    if not isinstance(policy, dict):
        raise ValueError("run manifest policy must be an object")
    policy.update(updates)
    atomic_write_json(path, manifest)


def write_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    segment: str,
    status: str,
) -> Path:
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / "dry_run_bootstrap.json"
    )
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": "dry_run_bootstrap",
            "skill": "workflow-supervisor",
            "stage": None,
            "status": status,
            "attempt": 1,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "input_refs": [],
            "output_refs": [],
            "evidence_refs": [],
            "gate_refs": [],
            "worker_result_ref": None,
            "observed_writes": [],
            "postcondition_result": {
                "ok": True,
                "classification": "dry_run_only",
                "failed_checks": [],
            },
            "contract_violations": [],
            "next_node": None,
            "segment": segment,
        },
    )
    return path


def run_dynamic_context_gate(
    workspace_root: Path,
    *,
    stage: str,
    build_id: str,
    write_review_packet: bool,
) -> dict[str, Any]:
    script = evidence_script_path(workspace_root, "check_dynamic_context.py")
    command = [
        sys.executable,
        str(script),
        "--workspace-root",
        str(workspace_root),
        "--stage",
        stage,
        "--json",
    ]
    if write_review_packet:
        command.extend(["--review-packet", "--build-id", build_id])
    proc = subprocess.run(
        command,
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "dynamic-context gate did not return JSON: "
            f"exit={proc.returncode} stderr={proc.stderr.strip()}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("dynamic-context gate JSON must contain an object")
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "stdout": payload,
        "stderr": proc.stderr,
    }


def run_protocol_compiler(
    workspace_root: Path,
    *,
    build_id: str,
) -> dict[str, Any]:
    script = evidence_script_path(workspace_root, "compile_protocol.py")
    command = [
        sys.executable,
        str(script),
        "--workspace-root",
        str(workspace_root),
        "--build-id",
        build_id,
        "--json",
    ]
    proc = subprocess.run(
        command,
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    payload: dict[str, Any] | None = None
    if proc.stdout.strip():
        try:
            decoded = json.loads(proc.stdout)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            payload = decoded
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "stdout": payload,
        "stdout_text": proc.stdout,
        "stderr": proc.stderr,
    }


def run_auto_iterate_command(
    workspace_root: Path,
    subcommand: str,
    args: list[str] | None = None,
) -> dict[str, Any]:
    script = auto_iterate_ctl_path(workspace_root)
    command = [
        sys.executable,
        str(script),
        "--workspace-root",
        str(workspace_root),
        subcommand,
    ]
    command.extend(args or [])
    proc = subprocess.run(
        command,
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "stdout_text": proc.stdout,
        "stderr_text": proc.stderr,
    }


def run_contract_approval(
    workspace_root: Path,
    *,
    contract: str,
    approved_by: str,
    approval_source: str,
) -> dict[str, Any]:
    script = evidence_script_path(workspace_root, "approve_contract.py")
    command = [
        sys.executable,
        str(script),
        "--workspace-root",
        str(workspace_root),
        "--contract",
        contract,
        "--approved-by",
        approved_by,
        "--approval-source",
        approval_source,
        "--json",
    ]
    proc = subprocess.run(
        command,
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout: dict[str, Any] | None = None
    if proc.stdout.strip():
        try:
            decoded = json.loads(proc.stdout)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            stdout = decoded
    status = "PASS" if proc.returncode == 0 else "FAIL"
    artifacts: list[str] = []
    if stdout:
        for key in ("contract_path", "project_state_path"):
            value = stdout.get(key)
            if isinstance(value, str):
                artifacts.append(value)
    return {
        "status": status,
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stdout_text": proc.stdout,
        "stderr_text": proc.stderr,
        "artifacts": artifacts,
    }


def approval_execution_for_decision(
    workspace_root: Path,
    *,
    request: dict[str, Any],
    decision: str,
    approved_by: str,
    approval_source: str,
) -> dict[str, Any]:
    if decision != "approve":
        return {
            "status": "NOT_RUN",
            "reason": "decision did not approve the exact action",
        }
    exact_action = request.get("exact_action")
    if not isinstance(exact_action, dict):
        raise ValueError("approve decision requires exact_action")
    contract = exact_action.get("contract")
    if not isinstance(contract, str) or not contract:
        return {
            "status": "NOT_RUN",
            "reason": (
                "exact action is not a contract approval; supervisor records "
                "the scoped approval payload only"
            ),
        }
    result = run_contract_approval(
        workspace_root,
        contract=contract,
        approved_by=approved_by,
        approval_source=approval_source,
    )
    if result["status"] != "PASS":
        message = str(result.get("stderr_text") or result.get("stdout_text") or "")
        raise ValueError(
            "approval action failed: "
            f"{contract} exit={result['exit_code']} {message.strip()}"
        )
    return result


def auto_iterate_status(workspace_root: Path) -> dict[str, Any]:
    result = run_auto_iterate_command(workspace_root, "status", ["--json"])
    try:
        payload = json.loads(result["stdout_text"])
    except json.JSONDecodeError as exc:
        raise ValueError(
            "auto-iterate status did not return JSON: "
            f"exit={result['exit_code']} stderr={result['stderr_text'].strip()}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("auto-iterate status JSON must contain an object")
    result["stdout"] = payload
    return result


def write_text_artifact(workspace_root: Path, relative_path: str, text: str) -> str:
    path = workspace_root / relative_path
    atomic_write_text(path, text)
    return relative_path


def write_json_artifact(workspace_root: Path, relative_path: str, data: Any) -> str:
    path = workspace_root / relative_path
    atomic_write_json(path, data)
    return relative_path


def path_stats(path: Path, *, max_entries: int = 2000) -> dict[str, int | bool]:
    if not path.exists():
        return {"files": 0, "bytes": 0, "truncated": False}
    if path.is_file():
        return {"files": 1, "bytes": path.stat().st_size, "truncated": False}
    files = 0
    bytes_total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        for child in current.iterdir():
            if child.is_dir():
                stack.append(child)
                continue
            if child.is_file():
                files += 1
                bytes_total += child.stat().st_size
                if files >= max_entries:
                    return {
                        "files": files,
                        "bytes": bytes_total,
                        "truncated": True,
                    }
    return {"files": files, "bytes": bytes_total, "truncated": False}


def nonempty_path(path: Path) -> bool:
    if path.is_file():
        return True
    if path.is_dir():
        return any(path.iterdir())
    return False


def source_basename(source: str) -> str:
    parsed = urllib.parse.urlparse(source)
    name = Path(parsed.path.rstrip("/")).name if parsed.path else ""
    if name.endswith(".git"):
        name = name[:-4]
    return name or "downloaded_dataset"


def source_is_remote(source: str) -> bool:
    parsed = urllib.parse.urlparse(source)
    return parsed.scheme in {"http", "https", "git", "ssh"} or source.startswith(
        "git@"
    )


def source_is_git(source: str) -> bool:
    if source.endswith(".git") or source.startswith("git@"):
        return True
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    if not any(name in host for name in ("github.com", "gitlab.com", "bitbucket.org")):
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 2


def resolve_operator_path(workspace_root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return workspace_root / path


def normalize_execution_readiness(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for key, value in STRUCTURED_READINESS_DEFAULTS.items():
        if key not in normalized:
            normalized[key] = value.copy() if isinstance(value, (dict, list)) else value
    return normalized


def readiness_value(workspace_root: Path, key: str) -> str | None:
    path = supervisor_root(workspace_root) / "readiness.json"
    if not path.exists():
        return None
    data = load_json_if_exists(path, {})
    if not isinstance(data, dict):
        return None
    data = normalize_execution_readiness(data)
    if key == "external_download_policy":
        value = data.get("external_download_policy")
        if isinstance(value, str) and usable_grill_value(value):
            return value.strip()
    if key == "operator_approved_at":
        value = data.get("operator_approved_at")
        if isinstance(value, str) and value.strip():
            return value.strip()
    target_paths = data.get("target_paths")
    if isinstance(target_paths, dict):
        value = target_paths.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if key in {"dataset_source", "dataset_remote"}:
        for item in data.get("approved_datasets", []):
            if not isinstance(item, dict):
                continue
            value = item.get("source")
            status = str(item.get("access_status", "approved"))
            if status in {"candidate", "approved"} and isinstance(value, str):
                return value.strip()
    if key in {"dataset_root", "dataset_path", "dataset_target"}:
        for item in data.get("approved_datasets", []):
            if not isinstance(item, dict):
                continue
            value = item.get("target_path") or item.get("target")
            status = str(item.get("access_status", "approved"))
            if status in {"candidate", "approved"} and isinstance(value, str):
                return value.strip()
    if key in {"baseline_repo", "baseline_source"}:
        for item in data.get("approved_baselines", []):
            if not isinstance(item, dict):
                continue
            value = item.get("source") or item.get("repo")
            status = str(item.get("access_status", "approved"))
            if status in {"candidate", "approved"} and isinstance(value, str):
                return value.strip()
    if key in {"baseline_cache", "baseline_target"}:
        for item in data.get("approved_baselines", []):
            if not isinstance(item, dict):
                continue
            value = item.get("target_path") or item.get("target")
            status = str(item.get("access_status", "approved"))
            if status in {"candidate", "approved"} and isinstance(value, str):
                return value.strip()
    for item in data.get("inputs", []):
        if not isinstance(item, dict):
            continue
        if item.get("key") == key and item.get("verification_status") in {
            "candidate",
            "verified",
        }:
            value = item.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def normalize_grill_key(key: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    return GRILL_KEY_ALIASES.get(normalized)


def usable_grill_value(value: Any) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip().strip("`'\"")
    if not rendered:
        return None
    if rendered.lower() in GRILL_REDACTED_VALUES:
        return None
    if rendered.startswith("<") and rendered.endswith(">"):
        return None
    return rendered


def normalized_marker_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def contains_normalized_label(normalized_text: str, labels: set[str]) -> bool:
    padded = f"_{normalized_text}_"
    return any(f"_{label}_" in padded for label in labels)


def contains_marker(normalized_text: str, markers: set[str]) -> bool:
    return any(marker in normalized_text for marker in markers)


def dataset_access_decision(text: str) -> str:
    normalized = normalized_marker_text(text)
    if contains_marker(normalized, DATASET_REJECT_MARKERS):
        return "rejected"
    if contains_marker(normalized, DATASET_REQUIRES_APPROVAL_MARKERS):
        return "requires_approval"
    if contains_marker(normalized, DATASET_DEFER_MARKERS):
        return "deferred"
    if contains_marker(normalized, DATASET_CANDIDATE_MARKERS):
        return "candidate"
    return "candidate"


def truthy_policy_value(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized in {
        "1",
        "true",
        "yes",
        "y",
        "allow",
        "allowed",
        "approve",
        "approved",
        "enabled",
    }


def hf_policy_allows_download(value: str | None) -> bool:
    if value is None:
        return False
    normalized = normalized_marker_text(value)
    if any(marker in normalized for marker in {"do_not_download", "no_download"}):
        return False
    has_hf = any(
        marker in normalized
        for marker in {"hf", "hugging_face", "huggingface"}
    )
    has_allowance = any(
        marker in normalized
        for marker in {"auth", "account", "allow", "accepted", "download", "use"}
    )
    return has_hf and has_allowance


def baseline_clone_markers_from_text(text: str) -> list[str]:
    markers: list[str] = []
    for line in text.splitlines():
        normalized = normalized_marker_text(line)
        if "clone" not in normalized or "baseline" not in normalized:
            continue
        if "free_surgs" in normalized:
            markers.append("free_surgs")
        if "feature_3dgs" in normalized:
            markers.append("feature_3dgs")
    return list(dict.fromkeys(markers))


def allowed_baseline_repo_urls_from_text(
    text: str,
    *,
    allowed_markers: list[str],
) -> list[str]:
    if not allowed_markers:
        return []
    repos: list[str] = []
    url_re = re.compile(r"(https?://[^\s`'\"<>]+|git@[^\s`'\"<>]+)")
    for line in text.splitlines():
        normalized_line = normalized_marker_text(line)
        if "baseline" not in normalized_line and "code" not in normalized_line:
            continue
        for match in url_re.finditer(line):
            value = match.group(1).rstrip(".,;)")
            if not source_is_git(value):
                continue
            source_name = normalized_marker_text(source_basename(value))
            if any(marker in source_name for marker in allowed_markers):
                repos.append(value)
    return list(dict.fromkeys(repos))


def remote_source_allowed_by_policy(policy: dict[str, Any], source: str) -> bool:
    if not source_is_remote(source):
        return True
    if policy.get("allow_external_downloads"):
        return True
    allowed_sources = policy.get("allowed_remote_sources")
    if isinstance(allowed_sources, list) and source in {
        str(item) for item in allowed_sources
    }:
        return True
    parsed = urllib.parse.urlparse(source)
    host = parsed.netloc.lower()
    allowed_hosts = policy.get("allowed_remote_hosts")
    if isinstance(allowed_hosts, list):
        for item in allowed_hosts:
            allowed = str(item).lower()
            if host == allowed or host.endswith(f".{allowed}"):
                return True
    allowed_markers = policy.get("allowed_baseline_repo_markers")
    if source_is_git(source) and isinstance(allowed_markers, list):
        source_name = normalized_marker_text(source_basename(source))
        if any(str(marker) in source_name for marker in allowed_markers):
            return True
    return False


def external_source_allowed(args: argparse.Namespace, source: str | None) -> bool:
    if not source or not source_is_remote(source):
        return True
    if getattr(args, "allow_external_downloads", False):
        return True
    bridge = getattr(args, "_grill_bridge", None)
    if isinstance(bridge, dict):
        policy = bridge.get("policy")
        if isinstance(policy, dict):
            return remote_source_allowed_by_policy(policy, source)
    return False


def bridge_candidate(
    value: str,
    *,
    source_ref: str,
    confidence: str,
    notes: str,
) -> dict[str, str]:
    return {
        "value": value,
        "source_ref": source_ref,
        "confidence": confidence,
        "notes": notes,
    }


def add_bridge_candidate(
    values: dict[str, dict[str, str]],
    *,
    key: str,
    value: Any,
    source_ref: str,
    confidence: str,
    notes: str,
) -> None:
    normalized = normalize_grill_key(key)
    rendered = usable_grill_value(value)
    if normalized is None or rendered is None:
        return
    values.setdefault(
        normalized,
        bridge_candidate(
            rendered,
            source_ref=source_ref,
            confidence=confidence,
            notes=notes,
        ),
    )


def structured_status_decision(status: Any) -> str:
    rendered = str(status or "approved").strip().lower()
    if rendered in {"candidate", "approved"}:
        return "candidate"
    if rendered in {"rejected", "requires_approval", "deferred"}:
        return rendered
    return "candidate"


def markdown_table_header(cells: list[str]) -> list[str] | None:
    normalized = [normalized_marker_text(cell) for cell in cells]
    if all(set(cell) <= {"_"} or not cell for cell in normalized):
        return None
    if not any("dataset" in cell for cell in normalized):
        return None
    if not any(cell in DATASET_TABLE_SOURCE_HEADERS for cell in normalized) and not any(
        cell in {"access_verdict", "local_status", "first_use", "action"}
        for cell in normalized
    ):
        return None
    return normalized


def baseline_table_header(cells: list[str]) -> list[str] | None:
    normalized = [normalized_marker_text(cell) for cell in cells]
    if all(set(cell) <= {"_"} or not cell for cell in normalized):
        return None
    if not any("baseline" in cell for cell in normalized):
        return None
    if not any(cell in BASELINE_TABLE_SOURCE_HEADERS for cell in normalized):
        return None
    return normalized


def table_cell(
    headers: list[str],
    cells: list[str],
    names: set[str],
) -> str | None:
    for index, header in enumerate(headers):
        if header in names and index < len(cells):
            value = cells[index].strip()
            if value:
                return value
    return None


def merge_dataset_candidate(
    candidates: dict[str, dict[str, str]],
    *,
    key: str,
    update: dict[str, str],
) -> None:
    existing = candidates.setdefault(key, {})
    for field, value in update.items():
        if value and not existing.get(field):
            existing[field] = value
    update_decision = update.get("decision", "candidate")
    existing_decision = existing.get("decision", "candidate")
    update_priority = DATASET_DECISION_PRIORITY.get(update_decision, 0)
    existing_priority = DATASET_DECISION_PRIORITY.get(existing_decision, 0)
    if update_priority >= existing_priority:
        existing["decision"] = update_decision
    if update.get("reason"):
        reason = update["reason"]
        existing_reason = existing.get("reason")
        if existing_reason and reason not in existing_reason:
            existing["reason"] = f"{existing_reason}; {reason}"
        elif not existing_reason:
            existing["reason"] = reason


def extract_dataset_candidates_from_packet(
    text: str,
    *,
    source_ref: str,
) -> list[dict[str, str]]:
    candidates: dict[str, dict[str, str]] = {}
    headers: list[str] | None = None
    for line in text.splitlines():
        cells = parse_markdown_table_row(line)
        if not cells:
            stripped = line.strip()
            if not stripped.startswith("|") or not stripped.endswith("|"):
                headers = None
            continue
        header = markdown_table_header(cells)
        if header is not None:
            headers = header
            continue
        if headers is None:
            continue

        dataset_id = table_cell(headers, cells, {"dataset_id", "id"})
        dataset_name = table_cell(headers, cells, {"dataset", "name"})
        source = table_cell(headers, cells, DATASET_TABLE_SOURCE_HEADERS)
        source = usable_grill_value(source)
        row_text = " ".join(cells)
        normalized_row = normalized_marker_text(row_text)
        decision = dataset_access_decision(row_text)
        key = dataset_id or dataset_name or source
        if not key:
            continue
        update = {
            "dataset_id": dataset_id or key,
            "name": dataset_name or dataset_id or key,
            "decision": decision,
            "reason": row_text,
            "source_ref": source_ref,
        }
        local_candidate = contains_marker(normalized_row, DATASET_LOCAL_SOURCE_MARKERS)
        if source and source_is_remote(source) and local_candidate:
            update["official_source"] = source
            update["local_status"] = "local_existing"
        elif source and source_is_remote(source):
            update["source"] = source
        elif source and Path(source).is_absolute():
            update["source"] = source
        merge_dataset_candidate(candidates, key=key, update=update)

    return [
        candidate
        for candidate in candidates.values()
        if (
            candidate.get("source")
            or candidate.get("local_status") == "local_existing"
            or candidate.get("decision") == "rejected"
        )
    ]


def extract_baseline_candidates_from_packet(
    text: str,
    *,
    source_ref: str,
) -> list[dict[str, str]]:
    candidates: dict[str, dict[str, str]] = {}
    headers: list[str] | None = None
    for line in text.splitlines():
        cells = parse_markdown_table_row(line)
        if not cells:
            stripped = line.strip()
            if not stripped.startswith("|") or not stripped.endswith("|"):
                headers = None
            continue
        header = baseline_table_header(cells)
        if header is not None:
            headers = header
            continue
        if headers is None:
            continue

        baseline_id = table_cell(headers, cells, BASELINE_TABLE_ID_HEADERS)
        role = table_cell(headers, cells, {"role", "purpose"})
        source = table_cell(headers, cells, BASELINE_TABLE_SOURCE_HEADERS)
        source = usable_grill_value(source)
        row_text = " ".join(cells)
        decision = dataset_access_decision(row_text)
        key = baseline_id or role or source
        if not key:
            continue
        update = {
            "baseline_id": baseline_id or key,
            "role": role or baseline_id or key,
            "decision": decision,
            "reason": row_text,
            "source_ref": source_ref,
        }
        if decision == "candidate" and source:
            if source_is_git(source) or Path(source).is_absolute():
                update["source"] = source
            else:
                update["decision"] = "rejected"
                update["reason"] = f"{row_text}; source is not cloneable"
        elif source and (source_is_remote(source) or Path(source).is_absolute()):
            update["source"] = source
        merge_dataset_candidate(candidates, key=key, update=update)

    return [
        candidate
        for candidate in candidates.values()
        if candidate.get("source") or candidate.get("decision") == "rejected"
    ]


def add_readiness_json_bridge_values(
    workspace_root: Path,
    values: dict[str, dict[str, str]],
    input_refs: list[str],
    dataset_candidates: list[dict[str, str]],
    baseline_candidates: list[dict[str, str]],
) -> None:
    path = supervisor_root(workspace_root) / "readiness.json"
    if not path.exists():
        return
    input_refs.append(path.relative_to(workspace_root).as_posix())
    data = load_json_if_exists(path, {})
    if not isinstance(data, dict):
        return
    data = normalize_execution_readiness(data)
    source_ref = path.relative_to(workspace_root).as_posix()
    add_bridge_candidate(
        values,
        key="external_download_policy",
        value=data.get("external_download_policy"),
        source_ref=source_ref,
        confidence="structured_readiness_json",
        notes="top-level readiness external download policy",
    )
    add_bridge_candidate(
        values,
        key="operator_approved_at",
        value=data.get("operator_approved_at"),
        source_ref=source_ref,
        confidence="structured_readiness_json",
        notes="operator approval timestamp recorded in readiness",
    )
    target_paths = data.get("target_paths")
    if isinstance(target_paths, dict):
        for key, value in target_paths.items():
            add_bridge_candidate(
                values,
                key=str(key),
                value=value,
                source_ref=source_ref,
                confidence="structured_readiness_json",
                notes="top-level readiness target path",
            )
    for item in data.get("approved_datasets", []):
        if not isinstance(item, dict):
            continue
        source = usable_grill_value(item.get("source"))
        dataset_id = usable_grill_value(item.get("id")) or "dataset"
        if not source:
            continue
        candidate = {
            "dataset_id": dataset_id,
            "name": dataset_id,
            "source": source,
            "decision": structured_status_decision(item.get("access_status")),
            "reason": str(item.get("notes", "structured readiness dataset")),
            "source_ref": source_ref,
        }
        target_path = usable_grill_value(item.get("target_path") or item.get("target"))
        if target_path:
            candidate["target_path"] = target_path
        dataset_candidates.append(candidate)
    for item in data.get("approved_baselines", []):
        if not isinstance(item, dict):
            continue
        source = usable_grill_value(item.get("source") or item.get("repo"))
        baseline_id = usable_grill_value(item.get("id")) or "baseline"
        if not source:
            continue
        candidate = {
            "baseline_id": baseline_id,
            "role": str(item.get("role") or baseline_id),
            "source": source,
            "decision": structured_status_decision(item.get("access_status")),
            "reason": str(item.get("notes", "structured readiness baseline")),
            "source_ref": source_ref,
        }
        target_path = usable_grill_value(item.get("target_path") or item.get("target"))
        if target_path:
            candidate["target_path"] = target_path
        baseline_candidates.append(candidate)
    for item in data.get("inputs", []):
        if not isinstance(item, dict):
            continue
        if item.get("verification_status") not in {"candidate", "verified"}:
            continue
        add_bridge_candidate(
            values,
            key=str(item.get("key", "")),
            value=item.get("value"),
            source_ref=path.relative_to(workspace_root).as_posix(),
            confidence="structured_readiness_json",
            notes=str(item.get("notes", "readiness candidate")),
        )


def parse_markdown_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if not cells or all(set(cell) <= {"-", ":"} for cell in cells):
        return None
    return cells


def add_packet_table_bridge_values(
    text: str,
    *,
    source_ref: str,
    values: dict[str, dict[str, str]],
) -> None:
    for line in text.splitlines():
        cells = parse_markdown_table_row(line)
        if not cells or len(cells) < 2:
            continue
        if cells[0].lower() in {"input", "key", "field"}:
            continue
        add_bridge_candidate(
            values,
            key=cells[0],
            value=cells[1],
            source_ref=source_ref,
            confidence="readiness_packet_table",
            notes="parsed from Execution Readiness Packet table",
        )


def add_explicit_line_bridge_values(
    text: str,
    *,
    source_ref: str,
    values: dict[str, dict[str, str]],
) -> None:
    for line in text.splitlines():
        pattern = (
            r"^\s*(?:[-*]\s*)?(?:`)?"
            r"([A-Za-z][A-Za-z0-9 _./-]{2,64})(?:`)?\s*[:=]\s*(.+?)\s*$"
        )
        match = re.match(
            pattern,
            line,
        )
        if not match:
            continue
        add_bridge_candidate(
            values,
            key=match.group(1),
            value=match.group(2),
            source_ref=source_ref,
            confidence="explicit_grill_line",
            notes="parsed from explicit key/value line",
        )


def add_contextual_url_bridge_values(
    text: str,
    *,
    source_ref: str,
    values: dict[str, dict[str, str]],
) -> None:
    url_re = re.compile(r"(https?://[^\s`'\"<>]+|git@[^\s`'\"<>]+)")
    for line in text.splitlines():
        if parse_markdown_table_row(line):
            continue
        normalized_line = re.sub(r"[^a-z0-9]+", "_", line.lower()).strip("_")
        has_dataset_label = contains_normalized_label(
            normalized_line,
            CONTEXTUAL_DATASET_URL_LABELS,
        )
        has_baseline_label = contains_normalized_label(
            normalized_line,
            CONTEXTUAL_BASELINE_URL_LABELS,
        )
        for match in url_re.finditer(line):
            value = match.group(1).rstrip(".,;)")
            if has_dataset_label:
                add_bridge_candidate(
                    values,
                    key="dataset_source",
                    value=value,
                    source_ref=source_ref,
                    confidence="contextual_dataset_url",
                    notes="line labels dataset source and contains a URL",
                )
            if has_baseline_label:
                add_bridge_candidate(
                    values,
                    key="baseline_repo",
                    value=value,
                    source_ref=source_ref,
                    confidence="contextual_baseline_url",
                    notes="line labels baseline source and contains a URL",
                )


def build_grill_bridge(
    workspace_root: Path,
    *,
    run_id: str,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], str]:
    values: dict[str, dict[str, str]] = {}
    dataset_candidates: list[dict[str, str]] = []
    baseline_candidates: list[dict[str, str]] = []
    allowed_baseline_repo_markers: list[str] = []
    artifact_texts: list[tuple[str, str]] = []
    input_refs: list[str] = []
    add_readiness_json_bridge_values(
        workspace_root,
        values,
        input_refs,
        dataset_candidates,
        baseline_candidates,
    )
    for source_ref in GRILL_ARTIFACT_REFS:
        path = workspace_root / source_ref
        if not path.exists():
            continue
        input_refs.append(source_ref)
        text = path.read_text(encoding="utf-8")
        artifact_texts.append((source_ref, text))
        if source_ref.endswith("Execution_Readiness_Packet.md"):
            add_packet_table_bridge_values(
                text,
                source_ref=source_ref,
                values=values,
            )
            dataset_candidates.extend(
                extract_dataset_candidates_from_packet(text, source_ref=source_ref)
            )
            baseline_candidates.extend(
                extract_baseline_candidates_from_packet(text, source_ref=source_ref)
            )
        add_explicit_line_bridge_values(text, source_ref=source_ref, values=values)
        add_contextual_url_bridge_values(text, source_ref=source_ref, values=values)
        clone_markers = baseline_clone_markers_from_text(text)
        if clone_markers:
            allowed_baseline_repo_markers.extend(clone_markers)
            values.setdefault(
                "baseline_clone_policy",
                bridge_candidate(
                    ", ".join(clone_markers),
                    source_ref=source_ref,
                    confidence="explicit_grill_clone_policy",
                    notes=(
                        "parsed from a Grill line that permits cloning the first "
                        "baseline set"
                    ),
                ),
            )

    if args.dataset_source:
        values["dataset_source"] = bridge_candidate(
            args.dataset_source,
            source_ref="cli:--dataset-source",
            confidence="cli",
            notes="explicit CLI override",
        )
    if args.dataset_target:
        values["dataset_root"] = bridge_candidate(
            args.dataset_target,
            source_ref="cli:--dataset-target",
            confidence="cli",
            notes="explicit CLI override",
        )
    if args.baseline_repo:
        values["baseline_repo"] = bridge_candidate(
            args.baseline_repo[0],
            source_ref="cli:--baseline-repo",
            confidence="cli",
            notes="explicit CLI override",
        )
    if args.baseline_target:
        values["baseline_cache"] = bridge_candidate(
            args.baseline_target,
            source_ref="cli:--baseline-target",
            confidence="cli",
            notes="explicit CLI override",
        )

    dataset_source = values.get("dataset_source", {}).get("value")
    dataset_target = values.get("dataset_root", {}).get("value")
    if dataset_source and not dataset_target:
        resolved_source = resolve_operator_path(workspace_root, dataset_source)
        if resolved_source is not None and resolved_source.exists():
            values["dataset_root"] = bridge_candidate(
                relpath_or_abs(resolved_source, workspace_root),
                source_ref=values["dataset_source"]["source_ref"],
                confidence="adopt_existing_dataset_source",
                notes="dataset source is an existing local path; adopting it as root",
            )
        else:
            values["dataset_root"] = bridge_candidate(
                f"data/{source_basename(dataset_source)}",
                source_ref=values["dataset_source"]["source_ref"],
                confidence="default_dataset_download_target",
                notes="dataset source exists but no target was provided",
            )

    allow_policy = values.get("external_download_policy", {}).get("value")
    allow_external = bool(args.allow_external_downloads) or truthy_policy_value(
        allow_policy
    )
    operator_approved_at = values.get("operator_approved_at", {}).get("value")
    allowed_remote_hosts: list[str] = []
    hf_policy = values.get("hf_access_policy", {}).get("value")
    if hf_policy_allows_download(hf_policy):
        allowed_remote_hosts.append("huggingface.co")
    allowed_baseline_repo_markers = list(
        dict.fromkeys(allowed_baseline_repo_markers)
    )
    if not values.get("baseline_repo"):
        executable_baselines = [
            candidate
            for candidate in baseline_candidates
            if candidate.get("decision") == "candidate" and candidate.get("source")
        ]
        if executable_baselines:
            values["baseline_repo"] = bridge_candidate(
                executable_baselines[0]["source"],
                source_ref=executable_baselines[0].get(
                    "source_ref", "docs/05_intake/Execution_Readiness_Packet.md"
                ),
                confidence="baseline_source_ledger",
                notes="parsed from executable Baseline Source Ledger row",
            )
        for source_ref, text in artifact_texts:
            if values.get("baseline_repo"):
                break
            allowed_repos = allowed_baseline_repo_urls_from_text(
                text,
                allowed_markers=allowed_baseline_repo_markers,
            )
            if allowed_repos:
                values["baseline_repo"] = bridge_candidate(
                    allowed_repos[0],
                    source_ref=source_ref,
                    confidence="explicit_grill_clone_scope_url",
                    notes=(
                        "parsed from a Git repository URL matching the allowed "
                        "first baseline clone scope"
                    ),
                )
                break
    executable_dataset_sources = [
        candidate.get("source", "")
        for candidate in dataset_candidates
        if candidate.get("decision") == "candidate" and candidate.get("source")
    ]
    executable_baseline_sources = [
        candidate.get("source", "")
        for candidate in baseline_candidates
        if candidate.get("decision") == "candidate" and candidate.get("source")
    ]
    allowed_remote_sources = [
        source
        for source in (*executable_dataset_sources, *executable_baseline_sources)
        if source_is_remote(source)
        and any(
            marker in source_ref
            for source_ref in (
                candidate.get("source_ref", "")
                for candidate in (*dataset_candidates, *baseline_candidates)
                if candidate.get("source") == source
            )
            for marker in (".workflow_supervisor/readiness.json", "readiness.json")
        )
        and operator_approved_at
    ]
    remote_sources = [
        item
        for item in (
            values.get("dataset_source", {}).get("value"),
            values.get("baseline_repo", {}).get("value"),
            *executable_dataset_sources,
            *executable_baseline_sources,
        )
        if item and source_is_remote(item)
    ]
    policy = {
        "allow_external_downloads": allow_external,
        "allow_external_downloads_source": (
            "cli:--allow-external-downloads"
            if args.allow_external_downloads
            else values.get("external_download_policy", {}).get("source_ref")
        ),
        "allowed_remote_hosts": allowed_remote_hosts,
        "allowed_remote_sources": list(dict.fromkeys(allowed_remote_sources)),
        "allowed_baseline_repo_markers": allowed_baseline_repo_markers,
        "remote_sources": remote_sources,
    }
    blocked_remote_sources = [
        source
        for source in remote_sources
        if not remote_source_allowed_by_policy(policy, source)
    ]
    unresolved: list[str] = []
    if blocked_remote_sources:
        unresolved.append(
            "remote dataset or baseline source found, but external download "
            "policy is not approved"
        )
    if not values.get("dataset_source") and not values.get("dataset_root"):
        unresolved.append(
            "dataset source or dataset root is not explicit in Grill outputs"
        )
    if not values.get("baseline_repo") and not values.get("baseline_cache"):
        unresolved.append(
            "baseline repo or existing baseline cache is not explicit in Grill outputs"
        )

    bridge = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": utc_now(),
        "source": "grill_to_prepare_bridge",
        "input_refs": list(dict.fromkeys(input_refs)),
        "values": values,
        "dataset_candidates": dataset_candidates,
        "baseline_candidates": baseline_candidates,
        "policy": policy,
        "unresolved": unresolved,
    }
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "runtime"
        / "grill_bridge.json"
    )
    atomic_write_json(path, bridge)
    return bridge, path.relative_to(workspace_root).as_posix()


def grill_bridge_value(args: argparse.Namespace, *keys: str) -> str | None:
    bridge = getattr(args, "_grill_bridge", None)
    if not isinstance(bridge, dict):
        return None
    values = bridge.get("values")
    if not isinstance(values, dict):
        return None
    for key in keys:
        item = values.get(key)
        if isinstance(item, dict):
            value = item.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def effective_allow_external_downloads(args: argparse.Namespace) -> bool:
    if getattr(args, "allow_external_downloads", False):
        return True
    bridge = getattr(args, "_grill_bridge", None)
    if isinstance(bridge, dict):
        policy = bridge.get("policy")
        if isinstance(policy, dict):
            return bool(policy.get("allow_external_downloads"))
    return False


def attach_grill_bridge_to_args(
    workspace_root: Path,
    *,
    run_id: str,
    args: argparse.Namespace,
) -> str:
    bridge, bridge_ref = build_grill_bridge(workspace_root, run_id=run_id, args=args)
    setattr(args, "_grill_bridge", bridge)
    setattr(args, "_grill_bridge_ref", bridge_ref)
    if effective_allow_external_downloads(args):
        args.allow_external_downloads = True
    return bridge_ref


def project_state_path(workspace_root: Path) -> Path:
    return workspace_root / "PROJECT_STATE.json"


def load_project_state(workspace_root: Path) -> dict[str, Any]:
    path = project_state_path(workspace_root)
    if not path.exists():
        return {"schema_version": 1}
    data = load_json_if_exists(path, {})
    return data if isinstance(data, dict) else {"schema_version": 1}


def update_project_state(workspace_root: Path, updates: dict[str, Any]) -> str:
    state = load_project_state(workspace_root)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(state.get(key), dict):
            merged = dict(state[key])
            merged.update(value)
            state[key] = merged
        else:
            state[key] = value
    state["updated_at"] = utc_now()
    atomic_write_json(project_state_path(workspace_root), state)
    return "PROJECT_STATE.json"


def write_markdown_table(path: Path, heading: str, rows: list[list[str]]) -> str:
    lines = [f"# {heading}", "", "| Field | Value |", "| --- | --- |"]
    for key, value in rows:
        lines.append(f"| {key} | {value} |")
    lines.append("")
    atomic_write_text(path, "\n".join(lines))
    return path.as_posix()


def copy_local_source(source_path: Path, target_path: Path) -> None:
    if source_path.is_dir():
        if target_path.exists() and target_path.is_file():
            raise OSError(f"target exists and is not a directory: {target_path}")
        shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.is_dir():
        shutil.copy2(source_path, target_path / source_path.name)
    else:
        shutil.copy2(source_path, target_path)


def download_http_source(source: str, target_path: Path) -> Path:
    if target_path.suffix:
        output_path = target_path
    else:
        output_path = target_path / source_basename(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(source, timeout=60) as response:
        with output_path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    return output_path


def clone_git_source(source: str, target_path: Path, *, timeout: int) -> dict[str, Any]:
    if target_path.exists() and nonempty_path(target_path):
        return {
            "command": f"git clone {source} {target_path}",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "skipped": True,
        }
    target_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["git", "clone", source, str(target_path)]
    try:
        proc = subprocess.run(
            command,
            cwd=target_path.parent,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "command": " ".join(command),
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "skipped": False,
        }
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "skipped": False,
    }


def acquire_source(
    workspace_root: Path,
    *,
    source: str | None,
    target: Path,
    allow_external_downloads: bool,
    timeout: int,
) -> dict[str, Any]:
    if target.exists() and nonempty_path(target):
        return {
            "ok": True,
            "command": "existing_path",
            "artifacts": [relpath_or_abs(target, workspace_root)],
            "reason": "target already exists",
        }
    if not source:
        return {
            "ok": False,
            "reason": "source is missing and target does not exist",
            "command": "not run",
            "artifacts": [relpath_or_abs(target, workspace_root)],
        }
    if source_is_remote(source) and not allow_external_downloads:
        return {
            "ok": False,
            "reason": "external download requires --allow-external-downloads",
            "command": "not run",
            "artifacts": [relpath_or_abs(target, workspace_root)],
        }
    local_source = resolve_operator_path(workspace_root, source)
    if local_source is not None and local_source.exists():
        try:
            copy_local_source(local_source, target)
            return {
                "ok": True,
                "command": f"copy {local_source} {target}",
                "artifacts": [relpath_or_abs(target, workspace_root)],
                "reason": "copied local source",
            }
        except OSError as exc:
            return {
                "ok": False,
                "reason": str(exc),
                "command": f"copy {local_source} {target}",
                "artifacts": [relpath_or_abs(target, workspace_root)],
            }
    if source_is_git(source):
        result = clone_git_source(source, target, timeout=timeout)
        return {
            "ok": result["exit_code"] == 0,
            "command": result["command"],
            "artifacts": [relpath_or_abs(target, workspace_root)],
            "reason": (
                "git clone completed"
                if result["exit_code"] == 0
                else result["stderr"].strip()
            ),
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        }
    if urllib.parse.urlparse(source).scheme in {"http", "https"}:
        try:
            output = download_http_source(source, target)
            return {
                "ok": True,
                "command": f"download {source} {output}",
                "artifacts": [relpath_or_abs(output, workspace_root)],
                "reason": "download completed",
            }
        except Exception as exc:
            return {
                "ok": False,
                "reason": str(exc),
                "command": f"download {source} {target}",
                "artifacts": [relpath_or_abs(target, workspace_root)],
            }
    return {
        "ok": False,
        "reason": f"source not found or unsupported: {source}",
        "command": "not run",
        "artifacts": [relpath_or_abs(target, workspace_root)],
    }


def worker_result_payload(
    *,
    run_id: str,
    node: dict[str, Any],
    status: str,
    exit_code: int | None,
    summary: str,
    artifact_refs: list[str],
    gate_ledger: list[dict[str, Any]],
    observed_writes: list[str],
    stdout_ref: str | None = None,
    stderr_ref: str | None = None,
    interrupt_request: dict[str, Any] | None = None,
    contract_violations: list[str] | None = None,
    worker_warnings: list[str] | None = None,
) -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "node_id": str(node["node_id"]),
        "skill": str(node["skill"]),
        "attempt": 1,
        "status": status,
        "exit_code": exit_code,
        "started_at": now,
        "finished_at": now,
        "summary": summary,
        "artifact_refs": artifact_refs,
        "gate_ledger": gate_ledger,
        "postcondition_claims": [],
        "interrupt_request": interrupt_request,
        "observed_writes": observed_writes,
        "stdout_ref": stdout_ref,
        "stderr_ref": stderr_ref,
        "contract_violations": contract_violations or [],
        "worker_warnings": worker_warnings or [],
    }


def write_worker_result(
    workspace_root: Path,
    *,
    run_id: str,
    node_id: str,
    result: dict[str, Any],
) -> str:
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "runtime"
        / f"{node_id}.worker_result.json"
    )
    atomic_write_json(path, result)
    return path.relative_to(workspace_root).as_posix()


def archive_node_attempt_artifacts(
    workspace_root: Path,
    *,
    run_id: str,
    node_id: str,
    reason: str,
    gate_status_refs: list[str],
) -> list[str]:
    base = supervisor_root(workspace_root) / "runs" / run_id / "attempts" / node_id
    attempt = 1
    while (base / f"attempt_{attempt}").exists():
        attempt += 1
    archive_dir = base / f"attempt_{attempt}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    sources = [
        (
            supervisor_root(workspace_root)
            / "runs"
            / run_id
            / "runtime"
            / f"{node_id}.worker_result.json",
            "worker_result.json",
        ),
        (
            supervisor_root(workspace_root)
            / "runs"
            / run_id
            / "node_runs"
            / f"{node_id}.json",
            "node_record.json",
        ),
        (
            supervisor_root(workspace_root)
            / "runs"
            / run_id
            / "gate_results"
            / f"{node_id}.postconditions.json",
            "postconditions.json",
        ),
    ]
    source_refs: list[str] = []
    artifact_refs: list[str] = []
    for source, target_name in sources:
        if not source.exists():
            continue
        target = archive_dir / target_name
        shutil.copy2(source, target)
        source_refs.append(relpath_or_abs(source, workspace_root))
        artifact_refs.append(relpath_or_abs(target, workspace_root))

    manifest_path = archive_dir / "archive_manifest.json"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "node_id": node_id,
        "attempt": attempt,
        "archived_at": utc_now(),
        "reason": reason,
        "source_refs": source_refs,
        "artifact_refs": artifact_refs,
        "gate_status_refs": gate_status_refs,
    }
    atomic_write_json(manifest_path, manifest)
    return [relpath_or_abs(manifest_path, workspace_root), *artifact_refs]


def dataset_source_from_args(
    workspace_root: Path,
    args: argparse.Namespace,
) -> str | None:
    return (
        args.dataset_source
        or readiness_value(workspace_root, "dataset_source")
        or readiness_value(workspace_root, "dataset_remote")
        or grill_bridge_value(args, "dataset_source")
    )


def dataset_target_from_args(
    workspace_root: Path,
    args: argparse.Namespace,
) -> Path | None:
    value = (
        args.dataset_target
        or readiness_value(workspace_root, "dataset_root")
        or readiness_value(workspace_root, "dataset_root_wsl")
        or readiness_value(workspace_root, "dataset_path")
        or grill_bridge_value(args, "dataset_root")
    )
    return resolve_operator_path(workspace_root, value)


def grill_dataset_candidates(args: argparse.Namespace) -> list[dict[str, str]]:
    bridge = getattr(args, "_grill_bridge", None)
    if not isinstance(bridge, dict):
        return []
    candidates = bridge.get("dataset_candidates")
    if not isinstance(candidates, list):
        return []
    valid: list[dict[str, str]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        normalized: dict[str, str] = {}
        for key, value in candidate.items():
            if isinstance(key, str) and isinstance(value, str):
                normalized[key] = value
        valid.append(normalized)
    return valid


def grill_baseline_candidates(args: argparse.Namespace) -> list[dict[str, str]]:
    bridge = getattr(args, "_grill_bridge", None)
    if not isinstance(bridge, dict):
        return []
    candidates = bridge.get("baseline_candidates")
    if not isinstance(candidates, list):
        return []
    valid: list[dict[str, str]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        normalized: dict[str, str] = {}
        for key, value in candidate.items():
            if isinstance(key, str) and isinstance(value, str):
                normalized[key] = value
        valid.append(normalized)
    return valid


def dataset_candidate_target(
    workspace_root: Path,
    args: argparse.Namespace,
    *,
    source: str | None,
) -> Path | None:
    base = dataset_target_from_args(workspace_root, args)
    if source and base is not None:
        return base / source_basename(source)
    if source:
        return workspace_root / "data" / source_basename(source)
    return base


def dataset_acquisition_entries(
    workspace_root: Path,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    source = dataset_source_from_args(workspace_root, args)
    target = dataset_target_from_args(workspace_root, args)
    bridge_candidates = (
        []
        if (source or target is not None)
        and getattr(args, "_answer_overrides_dataset_source", False)
        else grill_dataset_candidates(args)
    )

    if source or (target is not None and not bridge_candidates):
        entries.append(
            {
                "source": source,
                "target": target,
                "label": "explicit_dataset",
                "source_ref": "cli/readiness/grill_bridge",
            }
        )

    for candidate in bridge_candidates:
        decision = candidate.get("decision", "candidate")
        candidate_source = candidate.get("source")
        label = candidate.get("dataset_id") or candidate.get("name") or "dataset"
        if decision != "candidate":
            skipped.append(
                {
                    "label": label,
                    "source": candidate_source,
                    "source_ref": candidate.get("source_ref", "grill_bridge"),
                    "reason": candidate.get(
                        "reason",
                        "dataset candidate is not executable under current policy",
                    ),
                }
            )
            continue
        candidate_target = resolve_operator_path(
            workspace_root,
            candidate.get("target_path"),
        ) or dataset_candidate_target(
            workspace_root,
            args,
            source=candidate_source,
        )
        entries.append(
            {
                "source": candidate_source,
                "target": candidate_target,
                "label": label,
                "source_ref": candidate.get("source_ref", "grill_bridge"),
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        entry_source = str(entry.get("source") or "")
        entry_target = entry.get("target")
        target_key = str(entry_target) if isinstance(entry_target, Path) else ""
        key = (entry_source, target_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped, skipped


def baseline_repos_from_args(
    workspace_root: Path,
    args: argparse.Namespace,
) -> list[str]:
    repos = list(args.baseline_repo or [])
    if repos and getattr(args, "_answer_overrides_baseline_repo", False):
        return list(dict.fromkeys(repos))
    for key in ("baseline_repo", "baseline_source"):
        value = readiness_value(workspace_root, key)
        if value:
            repos.append(value)
    bridge_value = grill_bridge_value(args, "baseline_repo")
    if bridge_value:
        repos.append(bridge_value)
    for candidate in grill_baseline_candidates(args):
        if candidate.get("decision") != "candidate":
            continue
        source = candidate.get("source")
        if source:
            repos.append(source)
    return list(dict.fromkeys(repos))


def baseline_target_from_args(workspace_root: Path, args: argparse.Namespace) -> Path:
    value = (
        args.baseline_target
        or readiness_value(workspace_root, "baseline_cache")
        or grill_bridge_value(args, "baseline_cache")
    )
    return resolve_operator_path(workspace_root, value or "baselines") or (
        workspace_root / "baselines"
    )


def acquisition_plan_path(workspace_root: Path, run_id: str) -> Path:
    return (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "runtime"
        / "acquisition_plan.json"
    )


def source_kind(workspace_root: Path, source: str | None) -> str:
    if not source:
        return "missing"
    if source_is_git(source):
        return "git"
    scheme = urllib.parse.urlparse(source).scheme
    if scheme in {"http", "https"}:
        return "http"
    if source_is_remote(source):
        return "remote"
    local_source = resolve_operator_path(workspace_root, source)
    if local_source is not None:
        return "local_path"
    return "unknown"


def planned_source_entry(
    workspace_root: Path,
    *,
    label: str,
    source: str | None,
    target: Path | None,
    source_ref: str,
    allowed: bool,
) -> dict[str, Any]:
    remote = bool(source and source_is_remote(source))
    target_ref = relpath_or_abs(target, workspace_root) if target is not None else None
    if target is not None and target.exists() and nonempty_path(target):
        status = "existing_target"
        reason = "target already exists and is non-empty"
    elif target is None:
        status = "missing_target"
        reason = "target path is not explicit"
    elif remote and not allowed:
        status = "blocked"
        reason = "remote source is not approved by the run policy"
    else:
        status = "planned"
        reason = "source can be attempted by the acquisition node"
    return {
        "label": label,
        "source": source,
        "target": target_ref,
        "source_ref": source_ref,
        "source_kind": source_kind(workspace_root, source),
        "remote": remote,
        "allowed": allowed,
        "status": status,
        "reason": reason,
    }


def baseline_source_ref(args: argparse.Namespace, repo: str) -> str:
    for candidate in grill_baseline_candidates(args):
        if candidate.get("source") == repo:
            return candidate.get("source_ref", "grill_bridge")
    if repo in (args.baseline_repo or []):
        return "cli:--baseline-repo"
    return "readiness/grill_bridge"


def bridge_policy(args: argparse.Namespace) -> dict[str, Any]:
    bridge = getattr(args, "_grill_bridge", None)
    if not isinstance(bridge, dict):
        return {}
    policy = bridge.get("policy")
    return policy if isinstance(policy, dict) else {}


def policy_string_list(policy: dict[str, Any], key: str) -> list[str]:
    value = policy.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def prepare_acquisition_plan_source_refs(
    *,
    readiness_ref: str,
    args: argparse.Namespace,
) -> list[str]:
    refs = [readiness_ref]
    bridge_ref = getattr(args, "_grill_bridge_ref", None)
    if isinstance(bridge_ref, str) and bridge_ref:
        refs.append(bridge_ref)
    bridge = getattr(args, "_grill_bridge", None)
    if isinstance(bridge, dict):
        input_refs = bridge.get("input_refs")
        if isinstance(input_refs, list):
            refs.extend(str(item) for item in input_refs if item)
    return list(dict.fromkeys(refs))


def build_prepare_acquisition_plan(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    readiness_ref: str,
) -> dict[str, Any]:
    dataset_entries, skipped_datasets = dataset_acquisition_entries(
        workspace_root,
        args,
    )
    dataset_plan = [
        planned_source_entry(
            workspace_root,
            label=str(entry.get("label") or "dataset"),
            source=(
                entry.get("source") if isinstance(entry.get("source"), str) else None
            ),
            target=(
                entry.get("target") if isinstance(entry.get("target"), Path) else None
            ),
            source_ref=str(entry.get("source_ref") or "readiness/grill_bridge"),
            allowed=external_source_allowed(
                args,
                entry.get("source") if isinstance(entry.get("source"), str) else None,
            ),
        )
        for entry in dataset_entries
    ]
    skipped_plan = [
        {
            "label": str(item.get("label") or "dataset"),
            "source": (
                item.get("source") if isinstance(item.get("source"), str) else None
            ),
            "source_ref": str(item.get("source_ref") or "grill_bridge"),
            "reason": str(item.get("reason") or "candidate is not executable"),
        }
        for item in skipped_datasets
    ]
    baseline_target = baseline_target_from_args(workspace_root, args)
    baseline_plan = []
    for repo in baseline_repos_from_args(workspace_root, args):
        target = baseline_target / source_basename(repo)
        baseline_plan.append(
            planned_source_entry(
                workspace_root,
                label=source_basename(repo),
                source=repo,
                target=target,
                source_ref=baseline_source_ref(args, repo),
                allowed=external_source_allowed(args, repo),
            )
        )
    remote_sources = [
        str(entry["source"])
        for entry in [*dataset_plan, *baseline_plan]
        if entry.get("remote") and entry.get("source")
    ]
    blocked_remote_sources = [
        str(entry["source"])
        for entry in [*dataset_plan, *baseline_plan]
        if entry.get("status") == "blocked" and entry.get("source")
    ]
    policy = bridge_policy(args)
    allow_source = getattr(args, "_allow_external_downloads_source", None)
    if not allow_source and getattr(args, "allow_external_downloads", False):
        allow_source = "cli:--allow-external-downloads"
    if not allow_source:
        allow_source = policy.get("allow_external_downloads_source")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "prepare_acquisition_plan",
        "generated_at": utc_now(),
        "run_id": run_id,
        "source_refs": prepare_acquisition_plan_source_refs(
            readiness_ref=readiness_ref,
            args=args,
        ),
        "policy": {
            "gate_policy_ref": GATE_POLICY_REF,
            "gate_profile": "automation_prepare",
            "allow_external_downloads": effective_allow_external_downloads(args),
            "allow_external_downloads_source": (
                str(allow_source) if allow_source else None
            ),
            "allowed_remote_hosts": policy_string_list(
                policy,
                "allowed_remote_hosts",
            ),
            "allowed_remote_sources": policy_string_list(
                policy,
                "allowed_remote_sources",
            ),
            "allowed_baseline_repo_markers": policy_string_list(
                policy,
                "allowed_baseline_repo_markers",
            ),
            "remote_sources": list(dict.fromkeys(remote_sources)),
            "blocked_remote_sources": list(dict.fromkeys(blocked_remote_sources)),
        },
        "dataset": {
            "entries": dataset_plan,
            "skipped_candidates": skipped_plan,
        },
        "baselines": {
            "target_root": relpath_or_abs(baseline_target, workspace_root),
            "existing_target_nonempty": nonempty_path(baseline_target),
            "repos": baseline_plan,
        },
        "blockers": [
            f"remote source requires approval: {source}"
            for source in list(dict.fromkeys(blocked_remote_sources))
        ],
        "next_nodes": ["prepare_data_prep", "prepare_baseline_repro"],
    }


def write_prepare_acquisition_plan(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    readiness_ref: str,
) -> tuple[dict[str, Any], str, list[str]]:
    plan = build_prepare_acquisition_plan(
        workspace_root,
        args=args,
        run_id=run_id,
        readiness_ref=readiness_ref,
    )
    path = acquisition_plan_path(workspace_root, run_id)
    atomic_write_json(path, plan)
    plan_ref = path.relative_to(workspace_root).as_posix()
    errors = validate_schema(
        workspace_root,
        plan,
        "acquisition_plan.schema.json",
        plan_ref,
    )
    if effective_allow_external_downloads(args):
        update_run_manifest_policy(
            workspace_root,
            run_id=run_id,
            updates={
                "allow_external_downloads": True,
                "allow_external_downloads_source": plan["policy"].get(
                    "allow_external_downloads_source"
                ),
            },
        )
    return plan, plan_ref, errors


def write_prepare_acquisition_plan_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    readiness_ref: str,
    plan_ref: str,
    plan: dict[str, Any],
    schema_errors: list[str],
) -> Path:
    blockers = [str(item) for item in plan.get("blockers", [])]
    passed = not schema_errors and not blockers
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / "prepare_acquisition_plan.json"
    )
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": "prepare_acquisition_plan",
            "skill": "workflow-supervisor",
            "stage": "WF4/WF5",
            "status": "success" if passed else "failed",
            "attempt": 1,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "input_refs": list(
                dict.fromkeys([readiness_ref, *plan.get("source_refs", [])])
            ),
            "output_refs": [plan_ref],
            "evidence_refs": [plan_ref],
            "gate_refs": [],
            "worker_result_ref": None,
            "observed_writes": [plan_ref],
            "postcondition_result": {
                "ok": passed,
                "classification": "prepare_acquisition_plan",
                "failed_checks": [*schema_errors, *blockers],
            },
            "contract_violations": [],
            "gate_ledger": [
                {
                    "command": "validate acquisition_plan.schema.json",
                    "result": "PASS" if not schema_errors else "FAIL",
                    "reason": (
                        "schema validation passed"
                        if not schema_errors
                        else "; ".join(schema_errors)
                    ),
                    "artifacts": [plan_ref, "schemas/acquisition_plan.schema.json"],
                },
                {
                    "command": "check acquisition plan remote policy",
                    "result": "PASS" if not blockers else "FAIL",
                    "reason": (
                        "planned remote sources are allowed"
                        if not blockers
                        else "; ".join(blockers)
                    ),
                    "artifacts": plan.get("policy", {}).get(
                        "blocked_remote_sources",
                        [],
                    ),
                },
            ],
            "next_node": "prepare_data_prep" if passed else None,
            "segment": "prepare",
        },
    )
    return path


def create_prepare_acquisition_plan_request(
    workspace_root: Path,
    *,
    run_id: str,
    node_record_path: Path,
    plan_ref: str,
    blockers: list[str],
) -> dict[str, Any]:
    request = create_node_pending_request(
        workspace_root,
        run_id=run_id,
        segment="prepare",
        node_id="prepare_acquisition_plan",
        request_type="ASK_INPUT",
        reason="acquisition_policy_approval_required",
        question=(
            "The acquisition plan contains remote dataset or baseline sources "
            "that are not approved by the current readiness policy."
        ),
        allowed_responses=["approve_download", "provide_local_path", "reject"],
        evidence_refs=[plan_ref],
        gate_status_refs=[node_record_path.relative_to(workspace_root).as_posix()],
        risk_summary=[
            "No dataset download or baseline clone has started.",
            "Approve only if these remote sources match the readiness packet.",
            *blockers,
        ],
        resume_strategy="resume_with_answer",
    )
    return request


def run_prepare_acquisition_plan_gate(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    readiness_ref: str,
) -> int | None:
    state["current_node_id"] = "prepare_acquisition_plan"
    save_state(workspace_root, state)
    plan, plan_ref, schema_errors = write_prepare_acquisition_plan(
        workspace_root,
        args=args,
        run_id=run_id,
        readiness_ref=readiness_ref,
    )
    blockers = [str(item) for item in plan.get("blockers", [])]
    node_record_path = write_prepare_acquisition_plan_node_record(
        workspace_root,
        run_id=run_id,
        readiness_ref=readiness_ref,
        plan_ref=plan_ref,
        plan=plan,
        schema_errors=schema_errors,
    )
    passed = not schema_errors and not blockers
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_acquisition_plan",
        status="success" if passed else "failed",
        payload={
            "postcondition": "PASS" if passed else "FAIL",
            "mode": "prepare_complete_acquisition_plan",
            "node_record": node_record_path.relative_to(workspace_root).as_posix(),
            "acquisition_plan": plan_ref,
        },
    )
    state["acquisition_plan_ref"] = plan_ref
    if passed:
        state["completed_nodes"] = list(
            dict.fromkeys(
                [*state.get("completed_nodes", []), "prepare_acquisition_plan"]
            )
        )
        state["failed_nodes"] = [
            failed
            for failed in state.get("failed_nodes", [])
            if failed != "prepare_acquisition_plan"
        ]
        save_state(workspace_root, state)
        return None

    request = create_prepare_acquisition_plan_request(
        workspace_root,
        run_id=run_id,
        node_record_path=node_record_path,
        plan_ref=plan_ref,
        blockers=[*schema_errors, *blockers],
    )
    state["status"] = "paused"
    state["segment_status"] = "acquisition_policy_approval_required"
    state["pending_request_id"] = request["request_id"]
    state["failed_nodes"] = list(
        dict.fromkeys([*state.get("failed_nodes", []), "prepare_acquisition_plan"])
    )
    state["last_failure"] = {
        "kind": "prepare_acquisition_plan_failed",
        "node_record": node_record_path.relative_to(workspace_root).as_posix(),
        "acquisition_plan_ref": plan_ref,
        "errors": [*schema_errors, *blockers],
    }
    save_state(workspace_root, state)
    return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)


def write_dataset_acquisition_manifest(
    workspace_root: Path,
    *,
    run_id: str,
    dataset_ref: str,
    source: str | None,
    acquisition: dict[str, Any],
    stats: dict[str, Any],
) -> str:
    manifest_ref = "data/dataset_manifest.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "dataset_acquisition",
        "generated_at": utc_now(),
        "run_id": run_id,
        "dataset_root": dataset_ref,
        "source": source,
        "acquisition": {
            "command": str(acquisition.get("command", "")),
            "reason": str(acquisition.get("reason", "")),
            "artifacts": [
                str(item) for item in acquisition.get("artifacts", []) if item
            ],
        },
        "verification": {
            "command": f"path_stats {dataset_ref}",
            "result": "PASS",
            "files": int(stats["files"]),
            "bytes": int(stats["bytes"]),
            "stats_truncated": bool(stats["truncated"]),
        },
        "artifacts": [dataset_ref, "docs/Dataset_Stats.md"],
    }
    write_json_artifact(workspace_root, manifest_ref, payload)
    return manifest_ref


def run_data_prep_worker(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    node: dict[str, Any],
) -> dict[str, Any]:
    entries, skipped_candidates = dataset_acquisition_entries(workspace_root, args)
    skipped_gates = [
        {
            "command": "dataset acquisition",
            "result": "NOT_RUN",
            "reason": (
                f"{item['label']} not executable under Grill dataset access verdict: "
                f"{item['reason']}"
            ),
            "artifacts": [
                str(value)
                for value in (item.get("source"), item.get("source_ref"))
                if value
            ],
        }
        for item in skipped_candidates
    ]
    if not entries:
        interrupt = {
            "type": "ASK_INPUT",
            "reason": "dataset_input_required",
            "question": (
                "Provide --dataset-target, and optionally --dataset-source if "
                "the target path does not already contain the dataset."
            ),
            "allowed_responses": ["provide_dataset_path", "revise", "reject"],
        }
        return worker_result_payload(
            run_id=run_id,
            node=node,
            status="interrupt_requested",
            exit_code=None,
            summary="dataset target path is missing",
            artifact_refs=[],
            gate_ledger=[
                *skipped_gates,
                {
                    "command": "dataset acquisition",
                    "result": "NOT_RUN",
                    "reason": (
                        "dataset target path and executable candidates are missing"
                    ),
                    "artifacts": [],
                }
            ],
            observed_writes=[],
            interrupt_request=interrupt,
        )

    gate_ledger: list[dict[str, Any]] = [*skipped_gates]
    acquisition: dict[str, Any] | None = None
    target: Path | None = None
    source: str | None = None
    for entry in entries:
        entry_target = entry.get("target")
        entry_source = entry.get("source")
        if not isinstance(entry_target, Path):
            gate_ledger.append(
                {
                    "command": "dataset acquisition",
                    "result": "NOT_RUN",
                    "reason": f"{entry.get('label', 'dataset')} target path is missing",
                    "artifacts": [
                        str(value)
                        for value in (entry_source, entry.get("source_ref"))
                        if value
                    ],
                }
            )
            continue
        result = acquire_source(
            workspace_root,
            source=entry_source if isinstance(entry_source, str) else None,
            target=entry_target,
            allow_external_downloads=external_source_allowed(
                args,
                entry_source if isinstance(entry_source, str) else None,
            ),
            timeout=int(node.get("timeout_seconds", 900)),
        )
        gate_ledger.append(
            {
                "command": str(result["command"]),
                "result": "PASS" if result["ok"] else "FAIL",
                "reason": (
                    f"{entry.get('label', 'dataset')}: {str(result['reason'])}"
                ),
                "artifacts": result.get("artifacts", []),
            }
        )
        if result["ok"]:
            acquisition = result
            target = entry_target
            source = entry_source if isinstance(entry_source, str) else None
            break

    if acquisition is None:
        interrupt = {
            "type": "ASK_INPUT",
            "reason": "dataset_input_required",
            "question": (
                "Dataset acquisition could not proceed. Provide an existing "
                "dataset path, approve a currently blocked download, or revise "
                "the Grill dataset candidate order."
            ),
            "allowed_responses": ["provide_dataset_path", "approve_download", "reject"],
        }
        summary = (
            "dataset acquisition candidates were exhausted"
            if gate_ledger
            else "dataset acquisition could not run"
        )
        return worker_result_payload(
            run_id=run_id,
            node=node,
            status="interrupt_requested",
            exit_code=1,
            summary=summary,
            artifact_refs=[],
            gate_ledger=gate_ledger,
            observed_writes=[],
            interrupt_request=interrupt,
        )

    if target is None:
        raise RuntimeError("dataset acquisition succeeded without a target")
    docs_dir = workspace_root / "docs"
    evidence_dir = docs_dir / "30_evidence"
    stats = path_stats(target)
    dataset_ref = relpath_or_abs(target, workspace_root)
    dataset_stats_path = docs_dir / "Dataset_Stats.md"
    dataset_table_path = evidence_dir / "Dataset_Table.md"
    write_markdown_table(
        dataset_stats_path,
        "Dataset Stats",
        [
            ["dataset_root", dataset_ref],
            ["source", source or "existing local target"],
            ["files", str(stats["files"])],
            ["bytes", str(stats["bytes"])],
            ["stats_truncated", str(stats["truncated"]).lower()],
            ["acquisition", str(acquisition["reason"])],
        ],
    )
    write_markdown_table(
        dataset_table_path,
        "Dataset Evidence Table",
        [
            ["dataset_root", dataset_ref],
            ["acquisition_command", str(acquisition["command"])],
            ["verification", "path_stats"],
        ],
    )
    manifest_ref = write_dataset_acquisition_manifest(
        workspace_root,
        run_id=run_id,
        dataset_ref=dataset_ref,
        source=source,
        acquisition=acquisition,
        stats=stats,
    )
    state_ref = update_project_state(
        workspace_root,
        {
            "dataset_paths": {"primary": dataset_ref},
            "artifacts": {"dataset_stats": "docs/Dataset_Stats.md"},
        },
    )
    artifacts = [
        manifest_ref,
        "docs/Dataset_Stats.md",
        "docs/30_evidence/Dataset_Table.md",
        state_ref,
        *[str(item) for item in acquisition.get("artifacts", [])],
    ]
    observed = [
        manifest_ref,
        "docs/Dataset_Stats.md",
        "docs/30_evidence/Dataset_Table.md",
        state_ref,
    ]
    return worker_result_payload(
        run_id=run_id,
        node=node,
        status="success",
        exit_code=0,
        summary="dataset acquired or verified and stats report written",
        artifact_refs=artifacts,
        gate_ledger=[
            *gate_ledger,
            {
                "command": f"path_stats {dataset_ref}",
                "result": "PASS",
                "reason": "dataset path exists and was summarized",
                "artifacts": ["docs/Dataset_Stats.md", manifest_ref],
            },
        ],
        observed_writes=observed,
    )


def write_minimal_project_map(
    workspace_root: Path,
    *,
    baseline_entries: dict[str, dict[str, Any]],
) -> str:
    path = workspace_root / "project_map.json"
    existing = load_json_if_exists(path, {})
    if not isinstance(existing, dict) or not existing:
        existing = {
            "version": "1.0",
            "detail_policy": {
                "detailed": (
                    "Main research code with public interfaces and dependencies"
                ),
                "medium": "Configs and docs",
                "brief": "Reproduced baselines",
                "minimal": "Logs and generated outputs",
            },
            "structure": {},
        }
    existing["updated_at"] = utc_now()
    structure = existing.setdefault("structure", {})
    if isinstance(structure, dict):
        structure["baselines"] = {
            "type": "directory",
            "detail_level": "brief",
            "description": "Reproduced baseline repositories",
            "children": baseline_entries,
        }
    atomic_write_json(path, existing)
    return "project_map.json"


def write_baseline_acquisition_manifest(
    workspace_root: Path,
    *,
    run_id: str,
    target_root: Path,
    target_ref: str,
    repos: list[str],
    gate_ledger: list[dict[str, Any]],
    baseline_entries: dict[str, dict[str, Any]],
    artifacts: list[str],
) -> str:
    baselines: dict[str, dict[str, str]] = {}
    for name, entry in baseline_entries.items():
        baselines[name] = {
            "path": relpath_or_abs(target_root / name, workspace_root),
            "status": str(entry.get("status") or "untested"),
            "entry_point": str(entry.get("entry_point") or ""),
        }
    manifest_ref = "baselines/baseline_manifest.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "baseline_acquisition",
        "generated_at": utc_now(),
        "run_id": run_id,
        "baseline_root": target_ref,
        "repos": repos,
        "acquisition": [
            {
                "command": str(gate.get("command", "")),
                "result": str(gate.get("result", "NOT_RUN")),
                "reason": str(gate.get("reason", "")),
                "artifacts": [
                    str(item) for item in gate.get("artifacts", []) if item
                ],
            }
            for gate in gate_ledger
        ],
        "baselines": baselines,
        "artifacts": artifacts,
    }
    write_json_artifact(workspace_root, manifest_ref, payload)
    return manifest_ref


def run_baseline_repro_worker(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    node: dict[str, Any],
) -> dict[str, Any]:
    repos = baseline_repos_from_args(workspace_root, args)
    target_root = baseline_target_from_args(workspace_root, args)
    target_root.mkdir(parents=True, exist_ok=True)
    gate_ledger: list[dict[str, Any]] = []
    artifacts: list[str] = []
    baseline_entries: dict[str, dict[str, Any]] = {}

    if not repos and not nonempty_path(target_root):
        interrupt = {
            "type": "ASK_INPUT",
            "reason": "baseline_input_required",
            "question": (
                "Provide --baseline-repo for the required baseline, or place an "
                "existing baseline under --baseline-target."
            ),
            "allowed_responses": ["provide_baseline_repo", "revise", "reject"],
        }
        return worker_result_payload(
            run_id=run_id,
            node=node,
            status="interrupt_requested",
            exit_code=None,
            summary="baseline repository is missing",
            artifact_refs=[],
            gate_ledger=[
                {
                    "command": "baseline acquisition",
                    "result": "NOT_RUN",
                    "reason": "baseline repo and existing baseline target are missing",
                    "artifacts": [],
                }
            ],
            observed_writes=[],
            interrupt_request=interrupt,
        )

    for repo in repos:
        repo_target = target_root / source_basename(repo)
        result = acquire_source(
            workspace_root,
            source=repo,
            target=repo_target,
            allow_external_downloads=external_source_allowed(args, repo),
            timeout=int(node.get("timeout_seconds", 1800)),
        )
        gate_ledger.append(
            {
                "command": str(result["command"]),
                "result": "PASS" if result["ok"] else "FAIL",
                "reason": str(result["reason"]),
                "artifacts": [str(item) for item in result.get("artifacts", [])],
            }
        )
        if not result["ok"]:
            interrupt = {
                "type": "ASK_INPUT",
                "reason": "baseline_acquisition_decision_required",
                "question": (
                    "Baseline acquisition failed. Provide another repo/path or "
                    "approve the external clone/download requirements."
                ),
                "allowed_responses": [
                    "provide_baseline_repo",
                    "approve_clone",
                    "reject",
                ],
            }
            return worker_result_payload(
                run_id=run_id,
                node=node,
                status="interrupt_requested",
                exit_code=1,
                summary=str(result["reason"]),
                artifact_refs=[],
                gate_ledger=gate_ledger,
                observed_writes=[],
                interrupt_request=interrupt,
            )
        artifacts.extend(str(item) for item in result.get("artifacts", []))

    for child in sorted(target_root.iterdir()):
        if child.is_dir():
            baseline_entries[child.name] = {
                "type": "directory",
                "detail_level": "brief",
                "description": "Baseline repository",
                "source": "",
                "status": "untested",
                "entry_point": "",
            }

    docs_dir = workspace_root / "docs"
    evidence_dir = docs_dir / "30_evidence"
    target_ref = relpath_or_abs(target_root, workspace_root)
    baseline_report_path = docs_dir / "Baseline_Report.md"
    baseline_table_path = evidence_dir / "Baseline_Table.md"
    write_markdown_table(
        baseline_report_path,
        "Baseline Report",
        [
            ["baseline_root", target_ref],
            ["repos", ", ".join(repos) if repos else "existing local baselines"],
            ["status", "cloned_or_existing"],
            ["reproduction", "not run by acquisition helper"],
        ],
    )
    write_markdown_table(
        baseline_table_path,
        "Baseline Evidence Table",
        [
            ["baseline_root", target_ref],
            [
                "acquisition",
                " ; ".join(gate["command"] for gate in gate_ledger)
                or "existing_path",
            ],
            ["status", "untested until baseline smoke command runs"],
        ],
    )
    project_map_ref = write_minimal_project_map(
        workspace_root,
        baseline_entries=baseline_entries,
    )
    state_ref = update_project_state(
        workspace_root,
        {
            "artifacts": {"baseline_report": "docs/Baseline_Report.md"},
            "baseline_metrics": {},
        },
    )
    if not gate_ledger:
        gate_ledger.append(
            {
                "command": f"inspect {target_ref}",
                "result": "PASS",
                "reason": "existing baseline target is non-empty",
                "artifacts": [target_ref],
            }
        )
    artifacts.extend(
        [
            "docs/Baseline_Report.md",
            "docs/30_evidence/Baseline_Table.md",
            project_map_ref,
            state_ref,
        ]
    )
    manifest_ref = write_baseline_acquisition_manifest(
        workspace_root,
        run_id=run_id,
        target_root=target_root,
        target_ref=target_ref,
        repos=repos,
        gate_ledger=gate_ledger,
        baseline_entries=baseline_entries,
        artifacts=artifacts,
    )
    artifacts.insert(0, manifest_ref)
    observed = [
        manifest_ref,
        "docs/Baseline_Report.md",
        "docs/30_evidence/Baseline_Table.md",
        project_map_ref,
        state_ref,
        relpath_or_abs(target_root, workspace_root),
    ]
    return worker_result_payload(
        run_id=run_id,
        node=node,
        status="success",
        exit_code=0,
        summary="baseline repositories acquired or verified",
        artifact_refs=artifacts,
        gate_ledger=gate_ledger,
        observed_writes=observed,
    )


def automation_policy_for_node(node: dict[str, Any]) -> dict[str, Any]:
    policy = dict(DEFAULT_AUTOMATION_POLICY)
    segment_policy = SEGMENT_AUTOMATION_POLICIES.get(str(node.get("segment")), {})
    policy.update(segment_policy)
    override = node.get("automation_policy")
    if isinstance(override, dict):
        policy.update(override)
    max_attempts = node.get("max_attempts")
    if isinstance(max_attempts, int) and max_attempts > 0:
        policy["node_retry_limit"] = max_attempts
    else:
        policy["node_retry_limit"] = 1
    return policy


def positive_policy_int(policy: dict[str, Any], key: str) -> int:
    default = DEFAULT_AUTOMATION_POLICY[key]
    value = policy.get(key, default)
    if isinstance(value, int) and value > 0:
        return value
    return int(default)


def truncate_context(value: str, *, max_chars: int, label: str) -> str:
    if len(value) <= max_chars:
        return value
    marker = (
        f"\n[truncated {label}: {len(value) - max_chars} chars omitted; "
        "read the source artifact if the node needs more context]"
    )
    keep = max(0, max_chars - len(marker))
    return value[:keep].rstrip() + marker


def prompt_json(value: Any, *, max_chars: int, label: str) -> str:
    rendered = json.dumps(value, indent=2, sort_keys=True)
    return truncate_context(rendered, max_chars=max_chars, label=label)


def enforce_worker_prompt_budget(
    prompt: str,
    *,
    policy: dict[str, Any],
    goal: str,
    render_with_goal: Any,
) -> str:
    max_chars = positive_policy_int(policy, "worker_prompt_max_chars")
    if len(prompt) <= max_chars:
        return prompt
    overflow = len(prompt) - max_chars
    goal_limit = positive_policy_int(policy, "goal_max_chars")
    reduced_goal_limit = max(160, goal_limit - overflow - 120)
    reduced_goal = truncate_context(
        goal,
        max_chars=reduced_goal_limit,
        label="goal",
    )
    return render_with_goal(reduced_goal)


def render_worker_prompt(
    *,
    workspace_root: Path,
    run_id: str,
    node: dict[str, Any],
    goal: str,
    result_ref: str,
) -> str:
    node_id = str(node["node_id"])
    skill = str(node["skill"])
    purpose = str(node.get("purpose") or "").strip()
    policy = automation_policy_for_node(node)
    json_limit = positive_policy_int(policy, "json_context_max_chars")
    goal_text = truncate_context(
        goal,
        max_chars=positive_policy_int(policy, "goal_max_chars"),
        label="goal",
    )
    policy_text = prompt_json(
        policy,
        max_chars=json_limit,
        label="automation policy",
    )
    postconditions = prompt_json(
        node.get("postconditions", []),
        max_chars=json_limit,
        label="postconditions",
    )
    allowed_writes = prompt_json(
        node.get("allowed_worker_write_patterns", []),
        max_chars=json_limit,
        label="allowed writes",
    )
    evidence_tools = prompt_json(
        node.get("evidence_tools", []),
        max_chars=json_limit,
        label="evidence tools",
    )

    def render_with_goal(current_goal: str) -> str:
        return (
            "You are a Harness workflow supervisor worker.\n"
            "\n"
            f"Workspace: {workspace_root}\n"
            f"Run ID: {run_id}\n"
            f"Node ID: {node_id}\n"
            f"Skill: ${skill}\n"
            f"{'Purpose: ' + purpose + chr(10) if purpose else ''}"
            f"Goal: {current_goal}\n"
            "\n"
            "Execute the local Harness skill for this node in auto mode. Do not ask "
            "the operator directly. If input is missing, write an "
            "interrupt_requested worker result instead.\n"
            "\n"
            "Automation budget:\n"
            f"{policy_text}\n"
            "\n"
            "Quality bar:\n"
            "- Read the relevant local artifacts before editing.\n"
            "- Do not read historical supervisor design docs, workflow_handbook, "
            "docs/_site, or docs/_views unless this node explicitly requires "
            "maintaining those files.\n"
            "- Do not write docs/_site or docs/_views from ordinary worker nodes; "
            "report docs_site_boundary_report unless a docs-site boundary render "
            "is explicitly requested.\n"
            "- Make the smallest code/config/doc changes needed for this node.\n"
            "- Run concrete commands that prove the node postconditions below; "
            "defer validation-heavy unrelated checks to commit checkpoints.\n"
            "- For each `command_passes` postcondition, include a Gate ledger "
            "entry whose `command` exactly matches the postcondition command "
            "string, with result PASS, FAIL, or NOT_RUN. Do not mark PASS unless "
            "that gate was actually satisfied.\n"
            "- For nodes that edit durable non-tool-owned files, create an "
            "automatic commit checkpoint before returning success. Select the "
            "`slice`, `guardrail`, `docs`, `experiment`, or `release` profile "
            "from the touched surface. For roadmap `commit_plan` rows, complete "
            "and commit one row before starting the next independent row. "
            "Report each commit hash, subject, validation profile, and Gate "
            "ledger.\n"
            "- The supervisor verifies sliced commits from the run "
            "`base_git_commit` and verifies that accepted non-tool-owned slice "
            "paths are clean before accepting build nodes.\n"
            "- Run each listed evidence tool exactly when its inputs exist. If a "
            "tool cannot run, include a NOT_RUN Gate ledger entry with the reason.\n"
            "- If a command fails, debug and rerun within the node budget before "
            "declaring failure.\n"
            "- Do not exceed node_retry_limit or gate_cycle_limit; return a compact "
            "failed or interrupt_requested worker result instead.\n"
            "- Report semantic progress through `workflow_ctl.py worker-event`; "
            "do not hand-write `.workflow_supervisor/**`. Call worker-event at "
            "node start, each long phase, before and after important commands, "
            "before handoff, and whenever blocked.\n"
            "- If there is no concrete progress for about 5 minutes, report "
            "`phase=blocked` with the blocker or write an interrupt_requested "
            "worker result.\n"
            "- For build_validate_run, run the project's actual smoke/validation "
            "command when one is discoverable; otherwise return interrupt_requested "
            "with the missing command as the reason.\n"
            "- Do not report success from prose. Success requires artifacts, "
            "observed_writes, and PASS gate_ledger entries.\n"
            "- Keep summaries and Gate ledger context compact. Include full logs as "
            "artifact paths rather than inline text.\n"
            "- Treat hook or sandbox write denials as contract_violations and route "
            "them through the worker result.\n"
            "\n"
            "Allowed worker write patterns:\n"
            f"{allowed_writes}\n"
            "\n"
            "Evidence tools for this node:\n"
            f"{evidence_tools}\n"
            "\n"
            "Supervisor postconditions for this node:\n"
            f"{postconditions}\n"
            "\n"
            "Write exactly one JSON object matching "
            "schemas/workflow_supervisor_worker_result.schema.json to:\n"
            f"{result_ref}\n"
            "If that path is under `.agents/state/`, treat it as a temporary "
            "worker handoff. The supervisor will validate and adopt it into "
            "`.workflow_supervisor/**`; do not write supervisor runtime state "
            "directly.\n"
            "Do not use apply_patch for this handoff file; create or replace "
            "the JSON with a normal file write command so hook policy does not "
            "confuse the temporary handoff with a durable source edit.\n"
            "\n"
            "The result must include gate_ledger entries for every command or gate "
            "that mattered, observed_writes, artifact_refs, and any contract "
            "violations. The supervisor will reject prose-only completion claims.\n"
            "\n"
            "Worker telemetry command template:\n"
            "python tooling/workflow_supervisor/scripts/workflow_ctl.py "
            f"worker-event --run-id {run_id} --node-id {node_id} "
            "--phase <starting|reading|planning|editing|testing|committing|"
            "handoff|blocked|done> --message <compact status> --json\n"
        )

    prompt = render_with_goal(goal_text)
    return enforce_worker_prompt_budget(
        prompt,
        policy=policy,
        goal=goal,
        render_with_goal=render_with_goal,
    )


def run_worker_command(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    node: dict[str, Any],
    goal: str,
) -> dict[str, Any]:
    node_id = str(node["node_id"])
    paths = worker_runtime_paths(workspace_root, run_id=run_id, node_id=node_id)
    result_path = workspace_root / paths["result"]
    prompt_path = workspace_root / paths["prompt"]
    stdout_path = workspace_root / paths["stdout"]
    stderr_path = workspace_root / paths["stderr"]
    prompt = render_worker_prompt(
        workspace_root=workspace_root,
        run_id=run_id,
        node=node,
        goal=goal,
        result_ref=paths["result"],
    )
    atomic_write_text(prompt_path, prompt)
    append_worker_event(
        workspace_root,
        run_id=run_id,
        node_id=node_id,
        phase="starting",
        message="command worker prompt written",
        source="supervisor",
        timeout_seconds=int(node.get("timeout_seconds", 900)),
        skill=str(node.get("skill") or ""),
        artifacts=[paths["prompt"]],
    )

    command_template = args.worker_command
    if not command_template:
        append_worker_event(
            workspace_root,
            run_id=run_id,
            node_id=node_id,
            phase="blocked",
            message="worker command is not configured",
            source="supervisor",
            artifacts=[paths["prompt"]],
        )
        return worker_result_payload(
            run_id=run_id,
            node=node,
            status="interrupt_requested",
            exit_code=None,
            summary="worker command is not configured",
            artifact_refs=[],
            gate_ledger=[
                {
                    "command": "worker command",
                    "result": "NOT_RUN",
                    "reason": "run with --worker-command or --auto",
                    "artifacts": [],
                }
            ],
            observed_writes=[],
            interrupt_request={
                "type": "STEER",
                "reason": "worker_command_required",
                "question": (
                    "Provide --worker-command for this supervisor node, or rerun "
                    "with --auto to delegate the node to Codex."
                ),
                "allowed_responses": ["provide_worker_command", "auto", "reject"],
            },
        )

    rendered = command_template.format(
        workspace_root=str(workspace_root),
        run_id=run_id,
        node_id=node_id,
        skill=str(node["skill"]),
        result_path=str(result_path),
        result_ref=paths["result"],
        prompt_path=str(prompt_path),
        prompt_ref=paths["prompt"],
    )
    command = shlex.split(rendered)
    timeout_seconds = int(node.get("timeout_seconds", 900))
    try:
        proc = subprocess.Popen(
            command,
            cwd=workspace_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        append_worker_event(
            workspace_root,
            run_id=run_id,
            node_id=node_id,
            phase="blocked",
            message=f"worker command failed before subprocess start: {exc}",
            source="supervisor",
            command=rendered,
            result="FAIL",
            artifacts=[paths["prompt"]],
        )
        return worker_result_payload(
            run_id=run_id,
            node=node,
            status="failed",
            exit_code=1,
            summary=f"worker command failed before subprocess start: {exc}",
            artifact_refs=[paths["prompt"]],
            gate_ledger=[
                {
                    "command": rendered,
                    "result": "FAIL",
                    "reason": str(exc),
                    "artifacts": [paths["prompt"]],
                }
            ],
            observed_writes=[],
            stdout_ref=None,
            stderr_ref=None,
        )
    append_worker_event(
        workspace_root,
        run_id=run_id,
        node_id=node_id,
        phase="testing",
        message="command worker subprocess started",
        source="supervisor",
        command=rendered,
        pid=proc.pid,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        stdout, stderr = proc.communicate()
        atomic_write_text(stdout_path, stdout or "")
        atomic_write_text(stderr_path, (stderr or "") + f"\n{exc}\n")
        append_worker_event(
            workspace_root,
            run_id=run_id,
            node_id=node_id,
            phase="blocked",
            message=f"worker command timed out after {timeout_seconds} seconds",
            source="supervisor",
            command=rendered,
            result="FAIL",
            artifacts=[paths["stdout"], paths["stderr"]],
            pid=proc.pid,
        )
        return worker_result_payload(
            run_id=run_id,
            node=node,
            status="failed",
            exit_code=1,
            summary=f"worker command timed out after {timeout_seconds} seconds",
            artifact_refs=[paths["stdout"], paths["stderr"]],
            gate_ledger=[
                {
                    "command": rendered,
                    "result": "FAIL",
                    "reason": str(exc),
                    "artifacts": [paths["stdout"], paths["stderr"]],
                }
            ],
            observed_writes=[],
            stdout_ref=paths["stdout"],
            stderr_ref=paths["stderr"],
        )
    atomic_write_text(stdout_path, stdout)
    atomic_write_text(stderr_path, stderr)
    if not result_path.exists():
        append_worker_event(
            workspace_root,
            run_id=run_id,
            node_id=node_id,
            phase="blocked",
            message="worker command did not write worker result JSON",
            source="supervisor",
            command=rendered,
            result="FAIL",
            artifacts=[paths["stdout"], paths["stderr"]],
        )
        return worker_result_payload(
            run_id=run_id,
            node=node,
            status="failed",
            exit_code=proc.returncode,
            summary="worker command did not write worker result JSON",
            artifact_refs=[paths["stdout"], paths["stderr"]],
            gate_ledger=[
                {
                    "command": rendered,
                    "result": "FAIL",
                    "reason": "missing worker result JSON",
                    "artifacts": [paths["stdout"], paths["stderr"]],
                }
            ],
            observed_writes=[],
            stdout_ref=paths["stdout"],
            stderr_ref=paths["stderr"],
        )
    loaded = load_json(result_path)
    if not isinstance(loaded, dict):
        raise ValueError("worker result must be an object")
    loaded.setdefault("stdout_ref", paths["stdout"])
    loaded.setdefault("stderr_ref", paths["stderr"])
    append_worker_event(
        workspace_root,
        run_id=run_id,
        node_id=node_id,
        phase="done",
        message="worker result JSON loaded",
        source="supervisor",
        result="PASS" if loaded.get("status") == "success" else "FAIL",
        artifacts=[paths["result"], paths["stdout"], paths["stderr"]],
    )
    return loaded


def codex_worker_command(codex: str, workspace_root: Path) -> list[str]:
    return [
        codex,
        "exec",
        *CODEX_WORKER_SANDBOX_ARGS,
        "--cd",
        str(workspace_root),
        "-",
    ]


def synthetic_codex_success_from_postconditions(
    workspace_root: Path,
    *,
    run_id: str,
    node: dict[str, Any],
    command: list[str],
    paths: dict[str, str],
) -> dict[str, Any] | None:
    postconditions = node.get("postconditions", [])
    if not isinstance(postconditions, list) or not any(
        isinstance(condition, dict)
        and condition.get("type") in {"artifact_exists", "artifact_matches_schema"}
        for condition in postconditions
    ):
        return None
    candidate = worker_result_payload(
        run_id=run_id,
        node=node,
        status="success",
        exit_code=0,
        summary=(
            "codex worker exited successfully without handoff JSON; "
            "supervisor synthesized success from passing artifact postconditions"
        ),
        artifact_refs=[paths["prompt"], paths["stdout"], paths["stderr"]],
        gate_ledger=[],
        observed_writes=[],
        stdout_ref=paths["stdout"],
        stderr_ref=paths["stderr"],
        worker_warnings=[
            "codex_worker_missing_handoff_synthesized_from_postconditions"
        ],
    )
    postcondition_result = evaluate_node_postconditions(
        workspace_root,
        node,
        run_id=run_id,
        worker_result=candidate,
    )
    if not postcondition_result["ok"]:
        return None
    postcondition_artifacts = [
        artifact
        for gate in postcondition_result.get("gate_ledger", [])
        if isinstance(gate, dict)
        for artifact in gate.get("artifacts", [])
        if isinstance(artifact, str)
    ]
    candidate["artifact_refs"] = list(
        dict.fromkeys([*candidate["artifact_refs"], *postcondition_artifacts])
    )
    candidate["observed_writes"] = [
        artifact
        for artifact in dict.fromkeys(postcondition_artifacts)
        if not artifact.startswith("schemas/")
    ]
    sanitized_postcondition_gates = [
        {
            "command": str(gate.get("command") or "postcondition"),
            "result": str(gate.get("result") or "FAIL"),
            "reason": str(gate.get("reason") or "postcondition gate result"),
            "artifacts": [
                artifact
                for artifact in gate.get("artifacts", [])
                if isinstance(artifact, str)
            ],
        }
        for gate in postcondition_result.get("gate_ledger", [])
        if isinstance(gate, dict)
    ]
    candidate["gate_ledger"] = [
        {
            "command": " ".join(command),
            "result": "PASS",
            "reason": (
                "codex exited 0 without worker handoff; supervisor artifact "
                "postconditions passed"
            ),
            "artifacts": [paths["prompt"], paths["stdout"], paths["stderr"]],
        },
        *sanitized_postcondition_gates,
    ]
    return candidate


def run_codex_worker(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    node: dict[str, Any],
    goal: str,
) -> dict[str, Any]:
    node_id = str(node["node_id"])
    codex = shutil.which("codex")
    paths = worker_runtime_paths(workspace_root, run_id=run_id, node_id=node_id)
    result_path = workspace_root / paths["handoff_result"]
    prompt_path = workspace_root / paths["prompt"]
    stdout_path = workspace_root / paths["stdout"]
    stderr_path = workspace_root / paths["stderr"]
    result_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = render_worker_prompt(
        workspace_root=workspace_root,
        run_id=run_id,
        node=node,
        goal=goal,
        result_ref=paths["handoff_result"],
    )
    atomic_write_text(prompt_path, prompt)
    append_worker_event(
        workspace_root,
        run_id=run_id,
        node_id=node_id,
        phase="starting",
        message="codex worker prompt written",
        source="supervisor",
        timeout_seconds=int(node.get("timeout_seconds", 900)),
        skill=str(node.get("skill") or ""),
        artifacts=[paths["prompt"]],
    )
    if codex is None:
        append_worker_event(
            workspace_root,
            run_id=run_id,
            node_id=node_id,
            phase="blocked",
            message="codex worker runtime is unavailable",
            source="supervisor",
            command="codex exec",
            result="NOT_RUN",
            artifacts=[paths["prompt"]],
        )
        return worker_result_payload(
            run_id=run_id,
            node=node,
            status="interrupt_requested",
            exit_code=127,
            summary="codex worker runtime is unavailable",
            artifact_refs=[paths["prompt"]],
            gate_ledger=[
                {
                    "command": "codex exec",
                    "result": "NOT_RUN",
                    "reason": "codex binary was not found",
                    "artifacts": [paths["prompt"]],
                }
            ],
            observed_writes=[],
            interrupt_request={
                "type": "STEER",
                "reason": "worker_runtime_unavailable",
                "question": (
                    "Codex worker runtime is unavailable. Install Codex, provide "
                    "--worker-command, or run the node manually and validate the "
                    "worker result."
                ),
                "allowed_responses": [
                    "provide_worker_command",
                    "manual_recover",
                    "reject",
                ],
            },
        )
    command = codex_worker_command(codex, workspace_root)
    env = os.environ.copy()
    if args.codex_home:
        env["CODEX_HOME"] = str(Path(args.codex_home).expanduser())
    timeout_seconds = int(node.get("timeout_seconds", 900))
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open(
        "w", encoding="utf-8"
    ) as err:
        try:
            proc = subprocess.Popen(
                command,
                cwd=workspace_root,
                stdin=subprocess.PIPE,
                text=True,
                stdout=out,
                stderr=err,
                env=env,
            )
            append_worker_event(
                workspace_root,
                run_id=run_id,
                node_id=node_id,
                phase="testing",
                message="codex worker subprocess started",
                source="supervisor",
                command=" ".join(command),
                pid=proc.pid,
            )
            proc.communicate(input=prompt, timeout=timeout_seconds)
            codex_exit_code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            proc.communicate()
            err.write(str(exc))
            append_worker_event(
                workspace_root,
                run_id=run_id,
                node_id=node_id,
                phase="blocked",
                message=f"codex worker timed out after {timeout_seconds} seconds",
                source="supervisor",
                command=" ".join(command),
                result="FAIL",
                artifacts=[paths["prompt"], paths["stdout"], paths["stderr"]],
                pid=proc.pid,
            )
            codex_exit_code = 1
        except OSError as exc:
            err.write(str(exc))
            append_worker_event(
                workspace_root,
                run_id=run_id,
                node_id=node_id,
                phase="blocked",
                message=f"codex worker failed before result collection: {exc}",
                source="supervisor",
                command=" ".join(command),
                result="FAIL",
                artifacts=[paths["prompt"], paths["stdout"], paths["stderr"]],
            )
            codex_exit_code = 1
    if result_path.exists():
        loaded = load_json(result_path)
        if not isinstance(loaded, dict):
            raise ValueError("worker result must be an object")
        loaded.setdefault("stdout_ref", paths["stdout"])
        loaded.setdefault("stderr_ref", paths["stderr"])
        append_worker_event(
            workspace_root,
            run_id=run_id,
            node_id=node_id,
            phase="done",
            message="codex worker handoff JSON loaded",
            source="supervisor",
            result="PASS" if loaded.get("status") == "success" else "FAIL",
            artifacts=[paths["handoff_result"], paths["stdout"], paths["stderr"]],
        )
        return loaded
    if codex_exit_code == 0:
        synthetic = synthetic_codex_success_from_postconditions(
            workspace_root,
            run_id=run_id,
            node=node,
            command=command,
            paths=paths,
        )
        if synthetic is not None:
            append_worker_event(
                workspace_root,
                run_id=run_id,
                node_id=node_id,
                phase="done",
                message="codex worker success synthesized from postconditions",
                source="supervisor",
                result="PASS",
                artifacts=[paths["prompt"], paths["stdout"], paths["stderr"]],
            )
            return synthetic
    append_worker_event(
        workspace_root,
        run_id=run_id,
        node_id=node_id,
        phase="blocked",
        message="codex worker did not write worker result JSON",
        source="supervisor",
        command=" ".join(command),
        result="FAIL",
        artifacts=[paths["prompt"], paths["stdout"], paths["stderr"]],
    )
    return worker_result_payload(
        run_id=run_id,
        node=node,
        status="failed",
        exit_code=codex_exit_code,
        summary="codex worker did not write worker result JSON",
        artifact_refs=[paths["prompt"], paths["stdout"], paths["stderr"]],
        gate_ledger=[
            {
                "command": " ".join(command),
                "result": "FAIL",
                "reason": "missing worker result JSON",
                "artifacts": [paths["prompt"], paths["stdout"], paths["stderr"]],
            }
        ],
        observed_writes=[],
        stdout_ref=paths["stdout"],
        stderr_ref=paths["stderr"],
    )


def worker_mode(args: argparse.Namespace) -> str:
    if args.worker_command:
        return "command"
    if args.auto:
        return "codex"
    return str(args.worker_mode)


def run_external_worker(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    node: dict[str, Any],
    goal: str,
) -> dict[str, Any]:
    mode = worker_mode(args)
    if mode == "codex":
        return run_codex_worker(
            workspace_root,
            args=args,
            run_id=run_id,
            node=node,
            goal=goal,
        )
    return run_worker_command(
        workspace_root,
        args=args,
        run_id=run_id,
        node=node,
        goal=goal,
    )


def contains_change_keyword(text: str, keyword: str) -> bool:
    if keyword.isascii() and re.fullmatch(r"[A-Za-z0-9_-]+", keyword):
        return bool(re.search(rf"\b{re.escape(keyword)}\b", text))
    return keyword in text


def extract_path_hints(text: str) -> list[str]:
    paths: list[str] = []
    for match in PATH_HINT_RE.finditer(text):
        value = match.group(1).strip("`'\".,;:()[]{}")
        if value:
            paths.append(value)
    return list(dict.fromkeys(paths))


def git_changed_paths(workspace_root: Path) -> list[str]:
    if not (workspace_root / ".git").exists():
        return []
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        value = line[3:].strip()
        if " -> " in value:
            value = value.split(" -> ", 1)[1].strip()
        if value:
            paths.append(value)
    return list(dict.fromkeys(paths))


def git_status_paths(workspace_root: Path) -> list[str]:
    if not (workspace_root / ".git").exists():
        return []
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        value = line[3:].strip()
        if " -> " in value:
            value = value.split(" -> ", 1)[1].strip()
        if value:
            paths.append(value)
    return list(dict.fromkeys(paths))


def read_project_stage(workspace_root: Path) -> str | None:
    path = workspace_root / "PROJECT_STATE.json"
    if not path.exists():
        return None
    data = load_json_if_exists(path, {})
    if not isinstance(data, dict):
        return None
    for key in ("current_stage", "stage", "workflow_stage"):
        value = data.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for nested_key in ("id", "stage", "name", "current"):
                nested = value.get(nested_key)
                if isinstance(nested, str):
                    return nested
    return None


def collect_change_context(
    workspace_root: Path,
    *,
    request_text: str,
    previous_state: dict[str, Any] | None,
) -> dict[str, Any]:
    refs = [
        {
            "path": relative_path,
            "exists": (workspace_root / relative_path).exists(),
        }
        for relative_path in CHANGE_CONTEXT_INPUTS
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "request_text_hash": sha256_text(request_text),
        "context_refs": refs,
        "current_stage": read_project_stage(workspace_root),
        "previous_supervisor": {
            "status": previous_state.get("status") if previous_state else None,
            "segment": previous_state.get("segment") if previous_state else None,
            "segment_status": (
                previous_state.get("segment_status") if previous_state else None
            ),
        },
        "path_hints": extract_path_hints(request_text),
        "git_changed_paths": git_changed_paths(workspace_root),
    }


def score_change_request(
    request_text: str,
    affected_paths: list[str],
) -> dict[str, int]:
    text = request_text.lower()
    scores = {change_type: 0 for change_type in CHANGE_KEYWORDS}
    for change_type, keywords in CHANGE_KEYWORDS.items():
        for keyword in keywords:
            if contains_change_keyword(text, keyword.lower()):
                scores[change_type] += 1

    for path in affected_paths:
        normalized = path.lower()
        if normalized.startswith((".agents/", ".claude/")):
            scores["harness_guardrail_delta"] += 2
        if normalized.startswith("tooling/codex_hooks/"):
            scores["harness_guardrail_delta"] += 2
        if normalized.startswith("tooling/workflow_supervisor/"):
            scores["harness_guardrail_delta"] += 2
        if normalized == "schemas/skill_contracts.json":
            scores["harness_guardrail_delta"] += 2
        if normalized.endswith("evaluation_contract.md"):
            scores["evaluation_delta"] += 2
        if normalized.endswith("baseline_contract.md"):
            scores["evaluation_delta"] += 2
        if normalized.endswith("claim_boundary.md"):
            scores["claim_boundary_delta"] += 2
        if normalized == "iteration_log.json":
            scores["experiment_delta"] += 2
        if normalized in {"project_map.json", "docs/20_facts/codebase_map.md"}:
            scores["stable_code_delta"] += 1
    return scores


def infer_affected_contracts(change_type: str, request_text: str) -> list[str]:
    text = request_text.lower()
    contracts: list[str] = []
    if change_type in {
        "stable_code_delta",
        "architecture_delta",
        "new_research_direction",
    }:
        contracts.append("Project_Contract")
    if change_type == "evaluation_delta" or any(
        term in text
        for term in ["metric", "primary metric", "evaluation", "评估", "指标"]
    ):
        contracts.append("Evaluation_Contract")
    if change_type == "evaluation_delta" or any(
        term in text for term in ["baseline", "基线"]
    ):
        contracts.append("Baseline_Contract")
    if change_type == "claim_boundary_delta" or any(
        term in text for term in ["claim", "conclusion", "结论", "声明"]
    ):
        contracts.append("Claim_Boundary")
    if change_type == "harness_guardrail_delta":
        contracts.extend(["Skill_Contracts", "Hook_Policy"])
    return list(dict.fromkeys(contracts))


def route_details(change_type: str, route: str) -> dict[str, list[str]]:
    details = {
        "bugfix": {
            "validation_plan": [
                "reproduce the failing behavior with the narrowest command",
                "apply a focused fix through code-debug",
                "run regression or focused tests before handoff",
            ],
            "human_stop_points": [
                "pause if the root cause changes a public interface or contract"
            ],
            "gate_evidence_plan": [
                "failing command before fix when available",
                "focused test PASS after fix",
                "project_map/Codebase_Map update gate if stable surface changed",
            ],
        },
        "experiment_delta": {
            "validation_plan": [
                "route through iterate plan/code/run/eval",
                "record the hypothesis and decision in iteration_log.json",
                "compare against the current primary metric and baseline",
            ],
            "human_stop_points": [
                "pause if metric, baseline, contract, or claim boundary changes"
            ],
            "gate_evidence_plan": [
                "auto-iterate or iterate status",
                "iteration_log.json update",
                "evaluation command and metric output",
            ],
        },
        "stable_code_delta": {
            "validation_plan": [
                "route as a build delta through code-debug",
                "keep implementation scoped to current architecture",
                "run focused tests and update codebase map when stable files change",
            ],
            "human_stop_points": [
                "pause if public interface, config schema, data flow, or "
                "contracts change"
            ],
            "gate_evidence_plan": [
                "focused test PASS",
                "project_map.json and Codebase_Map docchain gate when touched",
            ],
        },
        "architecture_delta": {
            "validation_plan": [
                "run delta grill before implementation",
                "revise architecture plan through refine-arch/build-plan",
                "define compatibility or rollback before code changes",
            ],
            "human_stop_points": [
                "operator approves architecture tradeoff and contract impact "
                "before build"
            ],
            "gate_evidence_plan": [
                "delta grill answers",
                "Technical_Spec or Implementation_Roadmap update",
                "review packet when contracts or claims may move",
            ],
        },
        "evaluation_delta": {
            "validation_plan": [
                "route to review packet and contract gate",
                "update Evaluation/Baseline Contract only after explicit approval",
                "define validation command and acceptance threshold before experiments",
            ],
            "human_stop_points": [
                "Evaluation or Baseline Contract approval is required before execution"
            ],
            "gate_evidence_plan": [
                "Review Packet",
                "dynamic-context gate",
                "Human Approval record before contract mutation",
            ],
        },
        "claim_boundary_delta": {
            "validation_plan": [
                "route to Claim Boundary review",
                "map each new or stronger claim to evidence",
                "defer release/submission until claim approval is recorded",
            ],
            "human_stop_points": [
                "Claim Boundary approval is required before stronger claims are used"
            ],
            "gate_evidence_plan": [
                "claim-evidence map",
                "Review Packet",
                "Human Approval record for Claim Boundary changes",
            ],
        },
        "new_research_direction": {
            "validation_plan": [
                "route to delta grill or a new Research Intent Draft branch",
                "separate old baseline/claims from the new branch",
                "decide whether this is a new workflow branch before implementation",
            ],
            "human_stop_points": [
                "operator decides whether to create a new research branch"
            ],
            "gate_evidence_plan": [
                "delta grill answers",
                "Research Intent Draft branch artifact when accepted",
                "contract impact review before execution",
            ],
        },
        "harness_guardrail_delta": {
            "validation_plan": [
                "route through harness-maintenance",
                "update hooks/contracts/skills and aligned docs together",
                "run guardrail and contract regression tests",
            ],
            "human_stop_points": [
                "pause before changing permission boundaries or approval semantics"
            ],
            "gate_evidence_plan": [
                "check_contracts.py PASS",
                "hook_status.py inspection",
                "targeted pytest for guardrail behavior",
            ],
        },
        "unknown": {
            "validation_plan": [
                "ask operator to narrow the request or choose a route",
                "do not edit code or contracts until the route is explicit",
            ],
            "human_stop_points": ["operator steering is required"],
            "gate_evidence_plan": [
                "pending STEER request",
                "operator answer record",
            ],
        },
    }
    return details.get(change_type, details["unknown"])


def classify_change_request(
    *,
    request_text: str,
    run_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    path_hints = [
        path
        for path in context.get("path_hints", [])
        if isinstance(path, str)
    ]
    changed_paths = [
        path
        for path in context.get("git_changed_paths", [])
        if isinstance(path, str)
    ]
    affected_paths = list(dict.fromkeys([*path_hints, *changed_paths]))
    scores = score_change_request(request_text, affected_paths)
    candidates = [kind for kind, score in scores.items() if score > 0]
    uncertainty_reasons: list[str] = []
    if len(request_text.strip()) < 8:
        uncertainty_reasons.append("request_too_short")
    if not candidates:
        selected = "unknown"
        uncertainty_reasons.append("no_change_type_signal")
    else:
        selected = next(kind for kind in CHANGE_PRIORITY if scores[kind] > 0)
        competing = [kind for kind in candidates if kind != selected]
        if competing:
            uncertainty_reasons.append(
                "multiple_change_type_signals:" + ",".join(sorted(competing))
            )

    route = CHANGE_ROUTE_BY_TYPE[selected]
    confidence = "high"
    if selected == "unknown":
        confidence = "low"
    elif uncertainty_reasons:
        confidence = "medium"
    if len(candidates) >= 4 and selected not in {
        "evaluation_delta",
        "claim_boundary_delta",
        "harness_guardrail_delta",
    }:
        selected = "unknown"
        route = "steer"
        confidence = "low"
        uncertainty_reasons.append("too_many_competing_route_signals")

    details = route_details(selected, route)
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": "chg_" + run_id.removeprefix("sup_"),
        "change_type": selected,
        "route": route,
        "confidence": confidence,
        "uncertainty_reasons": uncertainty_reasons,
        "affected_contracts": infer_affected_contracts(selected, request_text),
        "affected_paths": affected_paths,
        "validation_plan": details["validation_plan"],
        "human_stop_points": details["human_stop_points"],
        "gate_evidence_plan": details["gate_evidence_plan"],
    }


def write_change_classify_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    change_request: dict[str, Any],
    context_ref: str,
    change_request_ref: str,
    schema_errors: list[str],
) -> Path:
    route = str(change_request.get("route"))
    confidence = str(change_request.get("confidence"))
    passed = not schema_errors
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / "change_classify_request.json"
    )
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": "change_classify_request",
            "skill": "change-intake",
            "stage": None,
            "status": "success" if passed else "failed",
            "attempt": 1,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "input_refs": [context_ref],
            "output_refs": [change_request_ref],
            "evidence_refs": [],
            "gate_refs": [],
            "worker_result_ref": None,
            "observed_writes": [context_ref, change_request_ref],
            "postcondition_result": {
                "ok": passed,
                "classification": "change_request_schema",
                "failed_checks": schema_errors,
            },
            "contract_violations": [],
            "gate_ledger": [
                {
                    "command": (
                        "workflow_ctl start --segment change "
                        "--goal <operator_request>"
                    ),
                    "result": "PASS" if passed else "FAIL",
                    "reason": (
                        f"classified change route={route} confidence={confidence}"
                    ),
                    "artifacts": [change_request_ref, context_ref],
                }
            ],
            "route_postconditions": {
                "validation_plan": change_request.get("validation_plan", []),
                "human_stop_points": change_request.get("human_stop_points", []),
                "gate_evidence_plan": change_request.get("gate_evidence_plan", []),
            },
            "next_node": route if route != "steer" else None,
            "segment": "change",
        },
    )
    return path


def create_change_steer_request(
    workspace_root: Path,
    *,
    run_id: str,
    change_request_ref: str,
    node_record_path: Path,
    change_request: dict[str, Any],
) -> dict[str, Any]:
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "change_classify_request",
        "type": "STEER",
        "reason": "change_route_uncertain",
        "question": (
            "Change intake could not select a deterministic route. Choose one "
            "route or narrow the request before any code, contract, or stage "
            "artifact changes."
        ),
        "allowed_responses": [
            "code-debug",
            "iterate",
            "build_delta",
            "delta_grill",
            "review_packet",
            "claim_boundary_review",
            "harness-maintenance",
            "reject",
        ],
        "exact_action": None,
        "evidence_refs": [
            {"kind": "change_request", "path": change_request_ref},
        ],
        "diff_refs": [],
        "gate_status_refs": [
            node_record_path.relative_to(workspace_root).as_posix(),
        ],
        "risk_summary": [
            "Low-confidence change routing must fail closed.",
            "No Stage Skill has been invoked.",
            "No code, contract, or canonical workflow state was modified.",
        ],
        "rollback_plan": (
            "Reject or provide a narrower route; runtime files are supervisor-owned."
        ),
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": "resume_with_answer",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment="change",
        node_id="change_classify_request",
        status="paused",
        payload={
            "request_id": request_id,
            "type": "STEER",
            "change_type": change_request.get("change_type"),
            "route": change_request.get("route"),
        },
    )
    return request


def route_status(route: str) -> str:
    return "change_routed_" + route.replace("-", "_")


def release_action_from_goal(goal: str) -> str | None:
    text = goal.lower()
    if any(term in text for term in ["submit", "submission", "提交"]):
        return "submit"
    if any(term in text for term in ["package", "packaging", "打包"]):
        return "package"
    if any(term in text for term in ["validate", "validation", "验证"]):
        return "validate"
    if any(term in text for term in ["release", "发布"]):
        return "package"
    return None


def release_gate_blockers(gate_result: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if gate_result.get("exit_code") != 0:
        blockers.append("dynamic_context_gate_failed")
    result = gate_result.get("stdout")
    if not isinstance(result, dict):
        return [*blockers, "missing_gate_payload"]
    if result.get("ok") is not True:
        blockers.append("dynamic_context_result_not_ok")
    gates = result.get("gates")
    context = gates.get("context") if isinstance(gates, dict) else None
    if not isinstance(context, dict):
        return [*blockers, "missing_context_gate_payload"]
    if context.get("dynamic_context") is not True:
        blockers.append("dynamic_context_required_for_release")
    contracts = context.get("contracts")
    if not isinstance(contracts, dict):
        return [*blockers, "missing_contract_gate_payload"]
    required = {
        "project_contract": "Project Contract",
        "evaluation_contract": "Evaluation Contract",
        "claim_boundary": "Claim Boundary",
    }
    for key, label in required.items():
        info = contracts.get(key)
        if not isinstance(info, dict):
            blockers.append(f"{key}_missing")
        elif not info.get("exists"):
            blockers.append(f"{key}_missing")
        elif info.get("approval_confirmed") is not True:
            blockers.append(f"{key}_approval_unconfirmed")
    return list(dict.fromkeys(blockers))


def write_release_claim_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    gate_result: dict[str, Any],
    release_action: str,
    blockers: list[str],
) -> Path:
    result = gate_result["stdout"]
    packet = result.get("review_packet")
    if not isinstance(packet, dict) or not packet.get("markdown_path"):
        raise ValueError("release review packet command did not produce a packet")
    markdown_path = str(packet["markdown_path"])
    json_path = str(packet.get("json_path", ""))
    artifacts = [markdown_path]
    if json_path:
        artifacts.append(json_path)
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / "release_claim_approval.json"
    )
    gate_status = "PASS" if not blockers else "FAIL"
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": "release_claim_approval",
            "skill": "release",
            "stage": "WF12",
            "status": "success" if not blockers else "failed",
            "attempt": 1,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "input_refs": [
                "docs/Final_Experiment_Matrix.md",
                "docs/10_contract/Claim_Boundary.md",
            ],
            "output_refs": artifacts,
            "evidence_refs": artifacts,
            "gate_refs": [],
            "worker_result_ref": None,
            "observed_writes": [str(packet["output_dir"])],
            "postcondition_result": {
                "ok": not blockers,
                "classification": "release_wf12_dynamic_context_gate",
                "failed_checks": blockers,
            },
            "contract_violations": [],
            "gate_ledger": [
                {
                    "command": gate_result["command"],
                    "result": gate_status,
                    "reason": (
                        "WF12 release claims require dynamic-context, "
                        "docchain, workflow-state, and Claim Boundary gates "
                        "before approval"
                        if not blockers
                        else "WF12 release gate blocked: " + ", ".join(blockers)
                    ),
                    "artifacts": artifacts,
                }
            ],
            "release_action": release_action,
            "next_node": None,
            "segment": "release",
        },
    )
    return path


def create_release_action_steer_request(
    workspace_root: Path,
    *,
    run_id: str,
) -> dict[str, Any]:
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "release_claim_approval",
        "type": "STEER",
        "reason": "release_action_unclear",
        "question": (
            "Choose the exact release action before WF12 proceeds. The "
            "supervisor will not validate, package, or submit without an "
            "explicit scoped action."
        ),
        "allowed_responses": RELEASE_ACTION_RESPONSES,
        "exact_action": None,
        "evidence_refs": [],
        "diff_refs": [],
        "gate_status_refs": [],
        "risk_summary": [
            "Release/package/submit requests require explicit operator scope.",
            "No release gate or package command has run.",
        ],
        "rollback_plan": "Reject or restart release with a scoped goal.",
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": "resume_with_answer",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment="release",
        node_id="release_claim_approval",
        status="paused",
        payload={"request_id": request_id, "type": "STEER"},
    )
    return request


def create_release_gate_steer_request(
    workspace_root: Path,
    *,
    run_id: str,
    node_record_path: Path,
    gate_result: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    packet = gate_result["stdout"].get("review_packet", {})
    markdown_path = str(packet.get("markdown_path", ""))
    json_path = str(packet.get("json_path", ""))
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "release_claim_approval",
        "type": "STEER",
        "reason": "release_gate_failed",
        "question": (
            "WF12 release gates failed. Fix the gate evidence or revise the "
            "release claims before requesting approval."
        ),
        "allowed_responses": ["fix_gates", "revise_release_claims", "reject"],
        "exact_action": None,
        "evidence_refs": [
            {"kind": "review_packet", "path": markdown_path},
        ]
        if markdown_path
        else [],
        "diff_refs": [],
        "gate_status_refs": [
            ref
            for ref in [
                json_path,
                node_record_path.relative_to(workspace_root).as_posix(),
            ]
            if ref
        ],
        "risk_summary": [
            "Release claims require passing context/docchain gates.",
            "Claim Boundary approval is required before release claims are used.",
            "No package or submission command has run.",
            "Gate blockers: " + ", ".join(blockers),
        ],
        "rollback_plan": "Revise release claims or reject the release request.",
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": "manual_recover",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment="release",
        node_id="release_claim_approval",
        status="paused",
        payload={"request_id": request_id, "type": "STEER"},
    )
    return request


def create_release_approval_request(
    workspace_root: Path,
    *,
    run_id: str,
    gate_result: dict[str, Any],
    node_record_path: Path,
    release_action: str,
) -> dict[str, Any]:
    packet = gate_result["stdout"]["review_packet"]
    markdown_path = str(packet["markdown_path"])
    json_path = str(packet.get("json_path", ""))
    exact_action = {
        "command": (
            f"harness release {release_action} "
            f"--approval-source \"{markdown_path}\""
        ),
        "release_action": release_action,
        "approval_source": markdown_path,
    }
    exact_action["action_hash"] = exact_action_hash(exact_action)
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "release_claim_approval",
        "type": "APPROVE_ACTION",
        "reason": "release_submission_approval_required",
        "question": (
            "Review the WF12 release packet and approve, revise, or reject "
            f"the exact `{release_action}` action. Supervisor v0 records the "
            "decision and reruns gates; it does not package or submit."
        ),
        "allowed_responses": ["approve", "revise", "reject"],
        "exact_action": exact_action,
        "evidence_refs": [
            {"kind": "review_packet", "path": markdown_path},
        ],
        "diff_refs": [],
        "gate_status_refs": [
            ref
            for ref in [
                json_path,
                node_record_path.relative_to(workspace_root).as_posix(),
            ]
            if ref
        ],
        "risk_summary": [
            "Release claims must stay inside the approved Claim Boundary.",
            "Review Packet is a decision input, not Approval Evidence.",
            "Supervisor v0 does not run package or submit commands.",
        ],
        "rollback_plan": "Reject or revise; no release package is modified by v0.",
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": "adopt_if_postconditions_pass_else_rerun",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment="release",
        node_id="release_claim_approval",
        status="paused",
        payload={"request_id": request_id, "type": "APPROVE_ACTION"},
    )
    return request


def auto_iterate_start_args(args: argparse.Namespace) -> list[str]:
    command_args = [
        "--tool",
        "codex",
        "--goal",
        args.auto_goal,
    ]
    if args.auto_config:
        command_args.extend(["--config", args.auto_config])
    if args.auto_dry_run:
        command_args.append("--dry-run")
    if args.max_rounds is not None:
        command_args.extend(["--max-rounds", str(args.max_rounds)])
    if args.skip_dynamic_preflight:
        command_args.append("--skip-dynamic-preflight")
        command_args.extend(
            [
                "--skip-dynamic-preflight-reason",
                args.skip_dynamic_preflight_reason,
            ]
        )
    if args.allow_draft_contract:
        command_args.append("--allow-draft-contract")
    if args.allow_review_required:
        command_args.append("--allow-review-required")
    return command_args


def write_iterate_delegate_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    start_result: dict[str, Any] | None,
    status_result: dict[str, Any],
) -> Path:
    runtime_dir = supervisor_root(workspace_root) / "runs" / run_id / "runtime"
    artifacts: list[str] = []
    if start_result is not None:
        artifacts.append(
            write_text_artifact(
                workspace_root,
                f"{SUPERVISOR_DIR}/runs/{run_id}/runtime/auto_iterate_start.stdout.log",
                str(start_result.get("stdout_text", "")),
            )
        )
        artifacts.append(
            write_text_artifact(
                workspace_root,
                f"{SUPERVISOR_DIR}/runs/{run_id}/runtime/auto_iterate_start.stderr.log",
                str(start_result.get("stderr_text", "")),
            )
        )
    status_ref = runtime_dir / "auto_iterate_status.json"
    atomic_write_json(status_ref, status_result)
    artifacts.append(status_ref.relative_to(workspace_root).as_posix())
    status_payload = status_result.get("stdout")
    if not isinstance(status_payload, dict):
        status_payload = {}
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / "iterate_delegate_auto_iterate.json"
    )
    start_exit = None if start_result is None else start_result.get("exit_code")
    gate_result = "PASS"
    if start_result is not None and start_exit not in {0, 105, 106, 108}:
        gate_result = "FAIL"
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": "iterate_delegate_auto_iterate",
            "skill": "workflow-supervisor",
            "stage": "WF10",
            "status": "success" if gate_result == "PASS" else "failed",
            "attempt": 1,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "input_refs": ["docs/auto_iterate_goal.md"],
            "output_refs": artifacts,
            "evidence_refs": [],
            "gate_refs": [],
            "worker_result_ref": None,
            "observed_writes": artifacts,
            "postcondition_result": {
                "ok": gate_result == "PASS",
                "classification": "auto_iterate_delegation",
                "failed_checks": [] if gate_result == "PASS" else ["start_exit"],
            },
            "contract_violations": [],
            "gate_ledger": [
                {
                    "command": (
                        str(start_result.get("command"))
                        if start_result is not None
                        else str(status_result.get("command"))
                    ),
                    "result": gate_result,
                    "reason": "delegated WF10 to auto-iterate controller",
                    "artifacts": artifacts,
                }
            ],
            "auto_iterate_status": {
                "status": status_payload.get("status"),
                "halt_reason": status_payload.get("halt_reason"),
                "loop_id": status_payload.get("loop_id"),
            },
            "next_node": None,
            "segment": "iterate",
        },
    )
    return path


def auto_iterate_segment_status(status_payload: dict[str, Any]) -> str:
    status = status_payload.get("status")
    halt_reason = status_payload.get("halt_reason")
    if halt_reason:
        return f"iterate_delegated_{halt_reason}"
    if status:
        return f"iterate_delegated_{status}"
    return "iterate_delegated_unknown"


def create_auto_iterate_pending_request(
    workspace_root: Path,
    *,
    run_id: str,
    status_result: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    status_payload = status_result.get("stdout")
    if not isinstance(status_payload, dict):
        status_payload = {}
    request_id = new_request_id()
    question = (
        "Auto-iterate paused and requires operator steering. Inspect the "
        "auto-iterate status and choose whether to resume, revise the goal, "
        "stop, or recover manually."
    )
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "iterate_delegate_auto_iterate",
        "type": "STEER",
        "reason": reason,
        "question": question,
        "allowed_responses": ["resume", "revise_goal", "stop", "recover"],
        "exact_action": None,
        "evidence_refs": [],
        "diff_refs": [],
        "gate_status_refs": [
            f"{SUPERVISOR_DIR}/runs/{run_id}/runtime/auto_iterate_status.json",
            ".auto_iterate/state.json",
        ],
        "risk_summary": [
            "WF10 remains owned by tooling/auto_iterate/**.",
            "Supervisor must not write .auto_iterate/** directly.",
            "Human steering is required before continuing the loop.",
        ],
        "rollback_plan": (
            "Use auto_iterate_ctl.sh resume, override, stop, or manual recovery."
        ),
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "manual_recover",
        },
        "resume_strategy": "manual_recover",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment="iterate",
        node_id="iterate_delegate_auto_iterate",
        status="paused",
        payload={
            "request_id": request_id,
            "type": "STEER",
            "auto_iterate_status": status_payload.get("status"),
            "halt_reason": status_payload.get("halt_reason"),
        },
    )
    return request


def readiness_preflight_path(workspace_root: Path) -> Path:
    return supervisor_root(workspace_root) / "readiness_preflight.json"


def empty_readiness_preflight() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": utc_now(),
        "source": "prepare_preflight",
        **STRUCTURED_READINESS_DEFAULTS,
        "inputs": [],
    }


def rejected_readiness_preflight(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": utc_now(),
        "source": "prepare_preflight",
        **STRUCTURED_READINESS_DEFAULTS,
        "inputs": [
            {
                "key": "readiness_payload",
                "kind": "open_question",
                "value": None,
                "redacted_value": None,
                "verification_status": "rejected",
                "verified_at": None,
                "verification_command": None,
                "notes": "; ".join(errors),
            }
        ],
    }


def path_verification_command(value: str) -> str:
    return f"test -e {value}"


def verify_readiness_inputs(
    workspace_root: Path,
    readiness: dict[str, Any],
    *,
    allow_creatable_paths: bool = False,
) -> list[str]:
    errors: list[str] = []
    for index, item in enumerate(readiness.get("inputs", [])):
        if not isinstance(item, dict) or item.get("kind") != "path":
            continue
        key = str(item.get("key", ""))
        value = item.get("value")
        if not isinstance(value, str) or not value.strip():
            item["verification_status"] = "rejected"
            item["verified_at"] = utc_now()
            item["verification_command"] = None
            errors.append(f"readiness.inputs[{index}].value missing path value")
            continue
        path = Path(value)
        if not path.is_absolute():
            path = workspace_root / path
        item["verification_command"] = path_verification_command(value)
        item["verified_at"] = utc_now()
        if path.exists():
            item["verification_status"] = "verified"
        elif allow_creatable_paths and key in CREATABLE_READINESS_PATH_KEYS:
            item["verification_status"] = "candidate"
            item["notes"] = (
                (str(item.get("notes", "")).strip() + "; ").lstrip("; ")
                + "path may be created by prepare --complete"
            )
        else:
            item["verification_status"] = "rejected"
            errors.append(
                f"readiness.inputs[{index}].value path does not exist: {value}"
            )
    readiness["updated_at"] = utc_now()
    return errors


def run_prepare_readiness_preflight(
    workspace_root: Path,
    *,
    allow_creatable_paths: bool = False,
) -> tuple[dict[str, Any], list[str], list[str]]:
    input_refs: list[str] = []
    source_path = supervisor_root(workspace_root) / "readiness.json"
    if source_path.exists():
        input_refs.append(source_path.relative_to(workspace_root).as_posix())
        loaded = load_json(source_path)
        if not isinstance(loaded, dict):
            errors = ["readiness.json must contain an object"]
            preflight = rejected_readiness_preflight(errors)
            atomic_write_json(readiness_preflight_path(workspace_root), preflight)
            return preflight, errors, input_refs
        readiness = normalize_execution_readiness(copy.deepcopy(loaded))
    else:
        readiness = empty_readiness_preflight()

    schema_errors = validate_schema(
        workspace_root,
        readiness,
        "execution_readiness.schema.json",
        "readiness_preflight",
    )
    if schema_errors:
        preflight = rejected_readiness_preflight(schema_errors)
        atomic_write_json(readiness_preflight_path(workspace_root), preflight)
        return preflight, schema_errors, input_refs

    errors = verify_readiness_inputs(
        workspace_root,
        readiness,
        allow_creatable_paths=allow_creatable_paths,
    )
    atomic_write_json(readiness_preflight_path(workspace_root), readiness)
    return readiness, errors, input_refs


def write_prepare_readiness_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    input_refs: list[str],
    errors: list[str],
) -> Path:
    output_ref = readiness_preflight_path(workspace_root).relative_to(
        workspace_root
    ).as_posix()
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / "prepare_readiness_preflight.json"
    )
    passed = not errors
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": "prepare_readiness_preflight",
            "skill": "workflow-supervisor",
            "stage": "WF5",
            "status": "success" if passed else "failed",
            "attempt": 1,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "input_refs": input_refs,
            "output_refs": [output_ref],
            "evidence_refs": [],
            "gate_refs": [],
            "worker_result_ref": None,
            "observed_writes": [output_ref],
            "postcondition_result": {
                "ok": passed,
                "classification": "prepare_readiness_preflight",
                "failed_checks": errors,
            },
            "contract_violations": [],
            "gate_ledger": [
                {
                    "command": (
                        "workflow_ctl start --segment prepare readiness preflight"
                    ),
                    "result": "PASS" if passed else "FAIL",
                    "reason": (
                        "execution readiness candidate inputs verified"
                        if passed
                        else "; ".join(errors)
                    ),
                    "artifacts": [*input_refs, output_ref],
                }
            ],
            "next_node": "prepare_protocol_compiler" if passed else None,
            "segment": "prepare",
        },
    )
    return path


def create_prepare_readiness_request(
    workspace_root: Path,
    *,
    run_id: str,
    node_record_path: Path,
    errors: list[str],
) -> dict[str, Any]:
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "prepare_readiness_preflight",
        "type": "ASK_INPUT",
        "reason": "execution_readiness_input_required",
        "question": (
            "Execution readiness candidate inputs are missing, invalid, or stale. "
            "Update the readiness packet/runtime inputs before prepare can build "
            "a review packet."
        ),
        "allowed_responses": ["update_readiness", "continue_without", "reject"],
        "exact_action": None,
        "evidence_refs": [],
        "diff_refs": [],
        "gate_status_refs": [
            node_record_path.relative_to(workspace_root).as_posix(),
            readiness_preflight_path(workspace_root).relative_to(
                workspace_root
            ).as_posix(),
        ],
        "risk_summary": [
            "Readiness answers are candidate inputs, not verified facts.",
            "Prepare cannot consume rejected local paths.",
            "Failures: " + "; ".join(errors),
        ],
        "rollback_plan": (
            "Fix or reject the readiness candidates; no Stage artifact changed."
        ),
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": "resume_with_answer",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_readiness_preflight",
        status="paused",
        payload={"request_id": request_id, "type": "ASK_INPUT"},
    )
    return request


def write_prepare_protocol_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    protocol_result: dict[str, Any],
    readiness_ref: str,
) -> Path:
    payload = protocol_result.get("stdout")
    actions = payload.get("actions", []) if isinstance(payload, dict) else []
    action_paths = [
        action.get("path")
        for action in actions
        if isinstance(action, dict) and isinstance(action.get("path"), str)
    ]
    output_root = (
        payload.get("output_root")
        if isinstance(payload, dict) and isinstance(payload.get("output_root"), str)
        else None
    )
    artifacts = [path for path in [output_root, *action_paths] if path]
    passed = protocol_result.get("exit_code") == 0 and bool(payload)
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / "prepare_protocol_compiler.json"
    )
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": "prepare_protocol_compiler",
            "skill": "protocol-compiler",
            "stage": "WF5",
            "status": "success" if passed else "failed",
            "attempt": 1,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "input_refs": [readiness_ref],
            "output_refs": artifacts,
            "evidence_refs": artifacts,
            "gate_refs": [],
            "worker_result_ref": None,
            "observed_writes": artifacts,
            "postcondition_result": {
                "ok": passed,
                "classification": "prepare_protocol_compiler",
                "failed_checks": [] if passed else ["compile_protocol_failed"],
            },
            "contract_violations": [],
            "gate_ledger": [
                {
                    "command": str(protocol_result.get("command")),
                    "result": "PASS" if passed else "FAIL",
                    "reason": (
                        "compiled draft protocol packet through evidence tooling"
                        if passed
                        else str(
                            protocol_result.get("stderr")
                            or "protocol compile failed"
                        )
                    ),
                    "artifacts": artifacts,
                }
            ],
            "next_node": "prepare_review_packet" if passed else None,
            "segment": "prepare",
        },
    )
    return path


def create_prepare_protocol_request(
    workspace_root: Path,
    *,
    run_id: str,
    node_record_path: Path,
    protocol_result: dict[str, Any],
) -> dict[str, Any]:
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "prepare_protocol_compiler",
        "type": "STEER",
        "reason": "protocol_compiler_failed",
        "question": (
            "Protocol compiler failed before prepare review-packet generation. "
            "Fix evidence table inputs or reject the prepare run."
        ),
        "allowed_responses": ["fix_protocol_inputs", "skip_protocol_draft", "reject"],
        "exact_action": None,
        "evidence_refs": [],
        "diff_refs": [],
        "gate_status_refs": [
            node_record_path.relative_to(workspace_root).as_posix(),
        ],
        "risk_summary": [
            "Protocol drafts are review inputs, not Approved Contracts.",
            f"compile_protocol exit code: {protocol_result.get('exit_code')}",
        ],
        "rollback_plan": (
            "Fix evidence inputs or reject; no canonical protocol was applied."
        ),
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": "manual_recover",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_protocol_compiler",
        status="paused",
        payload={"request_id": request_id, "type": "STEER"},
    )
    return request


def write_prepare_review_packet_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    gate_result: dict[str, Any],
    readiness_ref: str,
    protocol_ref: str,
) -> Path:
    result = gate_result["stdout"]
    packet = result.get("review_packet")
    if not isinstance(packet, dict) or not packet.get("markdown_path"):
        raise ValueError("prepare review packet command did not produce a packet")
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / "prepare_review_packet.json"
    )
    gate_status = "PASS" if gate_result["exit_code"] == 0 else "FAIL"
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": "prepare_review_packet",
            "skill": "review-packet",
            "stage": "WF5",
            "status": "success" if gate_result["exit_code"] == 0 else "failed",
            "attempt": 1,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "input_refs": [
                "docs/05_intake/Execution_Readiness_Packet.md",
                readiness_ref,
                protocol_ref,
            ],
            "output_refs": [
                str(packet["markdown_path"]),
                str(packet.get("json_path", "")),
            ],
            "evidence_refs": [str(packet["markdown_path"])],
            "gate_refs": [],
            "worker_result_ref": None,
            "observed_writes": [str(packet["output_dir"])],
            "postcondition_result": {
                "ok": bool(packet.get("markdown_path")),
                "classification": "prepare_hitl_poc_review_packet",
                "failed_checks": [] if packet.get("markdown_path") else ["missing"],
            },
            "contract_violations": [],
            "gate_ledger": [
                {
                    "command": gate_result["command"],
                    "result": gate_status,
                    "reason": "generated WF5 review packet through evidence tooling",
                    "artifacts": [
                        str(packet["markdown_path"]),
                        str(packet.get("json_path", "")),
                    ],
                }
            ],
            "next_node": None,
            "segment": "prepare",
        },
    )
    return path


def create_prepare_approval_request(
    workspace_root: Path,
    *,
    run_id: str,
    gate_result: dict[str, Any],
    node_record_path: Path,
    reason: str = "evaluation_contract_approval_required",
    unlocks_execution: bool = False,
) -> dict[str, Any]:
    packet = gate_result["stdout"]["review_packet"]
    markdown_path = str(packet["markdown_path"])
    json_path = str(packet.get("json_path", ""))
    exact_action = {
        "command": (
            "python tooling/evidence/approve_contract.py --workspace-root . "
            "--contract evaluation_contract --approved-by <human> "
            f"--approval-source \"{markdown_path}\""
        ),
        "contract": "evaluation_contract",
        "approval_source": markdown_path,
    }
    exact_action["action_hash"] = exact_action_hash(exact_action)
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "prepare_review_packet",
        "type": "APPROVE_ACTION",
        "reason": reason,
        "question": (
            "Review the WF5 dynamic-context packet and choose approve, revise, "
            "or reject. The approve command runs the exact contract approval "
            "action through evidence tooling only after explicit approval."
        ),
        "allowed_responses": ["approve", "revise", "reject"],
        "exact_action": exact_action,
        "evidence_refs": [
            {"kind": "review_packet", "path": markdown_path},
        ],
        "diff_refs": [],
        "gate_status_refs": [
            json_path,
            node_record_path.relative_to(workspace_root).as_posix()
        ],
        "risk_summary": [
            "Review Packet is a decision input, not Approval Evidence.",
            "approve_contract.py runs only for an explicit approve decision.",
            (
                "Approval records prepare_complete and unlocks build."
                if unlocks_execution
                else "prepare_hitl_poc does not unlock build, iterate, or release."
            ),
        ],
        "rollback_plan": "Reject or revise; no canonical contract is modified by v0.",
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": "adopt_if_postconditions_pass_else_rerun",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_review_packet",
        status="paused",
        payload={"request_id": request_id, "type": "APPROVE_ACTION"},
    )
    return request


def write_gate_rerun_record(
    workspace_root: Path,
    *,
    run_id: str,
    request_id: str,
    gate_result: dict[str, Any],
) -> Path:
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "runtime"
        / f"{request_id}.wf5_dynamic_context_after_approval.json"
    )
    atomic_write_json(path, gate_result)
    append_event(
        workspace_root,
        "DYNAMIC_CONTEXT_GATE_RERUN",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_review_packet",
        status="pass" if gate_result["exit_code"] == 0 else "fail",
        payload={
            "request_id": request_id,
            "gate_record": path.relative_to(workspace_root).as_posix(),
            "exit_code": gate_result["exit_code"],
        },
    )
    return path


def write_release_gate_rerun_record(
    workspace_root: Path,
    *,
    run_id: str,
    request_id: str,
    gate_result: dict[str, Any],
) -> Path:
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "runtime"
        / f"{request_id}.wf12_dynamic_context_after_approval.json"
    )
    atomic_write_json(path, gate_result)
    append_event(
        workspace_root,
        "DYNAMIC_CONTEXT_GATE_RERUN",
        run_id=run_id,
        segment="release",
        node_id="release_claim_approval",
        status="pass" if gate_result["exit_code"] == 0 else "fail",
        payload={
            "request_id": request_id,
            "gate_record": path.relative_to(workspace_root).as_posix(),
            "exit_code": gate_result["exit_code"],
        },
    )
    return path


def create_pending_request(
    workspace_root: Path,
    *,
    run_id: str,
    segment: str,
    reason: str,
) -> dict[str, Any]:
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": "dry_run_bootstrap",
        "type": "STEER",
        "reason": reason,
        "question": (
            "Supervisor v0 only records runtime state. Re-run with --dry-run "
            "or continue after a maintainer implements this segment."
        ),
        "allowed_responses": ["acknowledge", "revise", "reject"],
        "exact_action": None,
        "evidence_refs": [],
        "diff_refs": [],
        "gate_status_refs": [],
        "risk_summary": [
            "No Stage Skill was invoked.",
            "No canonical WF stage has been completed.",
        ],
        "rollback_plan": None,
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": "manual_recover",
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment=segment,
        node_id="dry_run_bootstrap",
        status="paused",
        payload={"request_id": request_id, "type": "STEER"},
    )
    return request


def create_node_pending_request(
    workspace_root: Path,
    *,
    run_id: str,
    segment: str,
    node_id: str,
    request_type: str,
    reason: str,
    question: str,
    allowed_responses: list[str] | None = None,
    evidence_refs: list[Any] | None = None,
    gate_status_refs: list[str] | None = None,
    risk_summary: list[str] | None = None,
    resume_strategy: str = "manual_recover",
) -> dict[str, Any]:
    request_id = new_request_id()
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "node_id": node_id,
        "type": request_type,
        "reason": reason,
        "question": question,
        "allowed_responses": allowed_responses or ["acknowledge", "revise", "reject"],
        "exact_action": None,
        "evidence_refs": evidence_refs or [],
        "diff_refs": [],
        "gate_status_refs": gate_status_refs or [],
        "risk_summary": risk_summary
        or [
            "The supervisor paused before accepting this node.",
            "No later node has been accepted for this segment.",
        ],
        "rollback_plan": None,
        "escalation_policy": {
            "expires_at": None,
            "on_expire": "fail_closed",
        },
        "resume_strategy": resume_strategy,
        "created_at": utc_now(),
        "expires_at": None,
    }
    request["request_snapshot_hash"] = request_snapshot_hash(request)
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_CREATED",
        run_id=run_id,
        segment=segment,
        node_id=node_id,
        status="paused",
        payload={"request_id": request_id, "type": request_type, "reason": reason},
    )
    return request


def node_precondition_result(
    workspace_root: Path,
    *,
    run_id: str,
    node: dict[str, Any],
) -> dict[str, Any]:
    worker_result = {"gate_ledger": [], "observed_writes": []}
    gates = [
        evaluate_condition(
            workspace_root,
            condition,
            run_id=run_id,
            worker_result=worker_result,
        )
        for condition in node.get("preconditions", [])
        if isinstance(condition, dict)
    ]
    failed = [gate for gate in gates if gate["result"] == "FAIL"]
    return {"ok": not failed, "gate_ledger": gates, "failed_checks": failed}


def write_supervisor_node_record(
    workspace_root: Path,
    *,
    run_id: str,
    node: dict[str, Any],
    worker_result: dict[str, Any],
    worker_result_ref: str,
    postcondition_result: dict[str, Any],
    status: str,
    next_node: str | None,
) -> str:
    path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / f"{node['node_id']}.json"
    )
    postcondition_path = postcondition_record_path(
        workspace_root,
        run_id=run_id,
        node_id=str(node["node_id"]),
    )
    atomic_write_json(postcondition_path, postcondition_result)
    postcondition_ref = postcondition_path.relative_to(workspace_root).as_posix()
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": node["node_id"],
            "skill": node["skill"],
            "stage": node.get("stage"),
            "status": status,
            "attempt": 1,
            "started_at": worker_result.get("started_at") or utc_now(),
            "finished_at": worker_result.get("finished_at") or utc_now(),
            "input_refs": [
                str(condition.get("path"))
                for condition in node.get("preconditions", [])
                if isinstance(condition, dict) and condition.get("path")
            ],
            "output_refs": worker_result.get("artifact_refs", []),
            "evidence_refs": worker_result.get("artifact_refs", []),
            "gate_refs": [postcondition_ref],
            "worker_result_ref": worker_result_ref,
            "observed_writes": worker_result.get("observed_writes", []),
            "postcondition_result": postcondition_result,
            "contract_violations": worker_result.get("contract_violations", []),
            "gate_ledger": postcondition_result.get("gate_ledger", []),
            "next_node": next_node,
            "segment": node.get("segment"),
        },
    )
    return path.relative_to(workspace_root).as_posix()


def ordered_segment_nodes(
    registry: dict[str, Any],
    segment: str,
    *,
    node_ids: set[str] | None = None,
    run_when: str | None = "always",
) -> list[dict[str, Any]]:
    nodes = [
        node
        for node in registry.get("nodes", [])
        if isinstance(node, dict)
        and node.get("segment") == segment
        and (node_ids is None or str(node.get("node_id")) in node_ids)
        and (
            node_ids is not None
            or run_when is None
            or str(node.get("run_when") or "always") == run_when
        )
    ]
    return sorted(nodes, key=lambda node: int(node.get("order", 0)))


def on_failure_nodes(
    registry: dict[str, Any],
    segment: str,
) -> list[dict[str, Any]]:
    return ordered_segment_nodes(registry, segment, run_when="on_failure")


def run_node_worker(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    node: dict[str, Any],
    goal: str,
) -> dict[str, Any]:
    node_id = str(node["node_id"])
    if node_id == "prepare_data_prep":
        return run_data_prep_worker(
            workspace_root,
            args=args,
            run_id=run_id,
            node=node,
        )
    if node_id == "prepare_baseline_repro":
        return run_baseline_repro_worker(
            workspace_root,
            args=args,
            run_id=run_id,
            node=node,
        )
    return run_external_worker(
        workspace_root,
        args=args,
        run_id=run_id,
        node=node,
        goal=goal,
    )


def pause_for_node_request(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    node: dict[str, Any],
    reason: str,
    question: str,
    request_type: str = "STEER",
    allowed_responses: list[str] | None = None,
    gate_status_refs: list[str] | None = None,
) -> int:
    request = create_node_pending_request(
        workspace_root,
        run_id=run_id,
        segment=str(node.get("segment")),
        node_id=str(node["node_id"]),
        request_type=request_type,
        reason=reason,
        question=question,
        allowed_responses=allowed_responses,
        gate_status_refs=gate_status_refs,
        resume_strategy=str(node.get("resume_strategy") or "manual_recover"),
    )
    state["status"] = "paused"
    state["segment_status"] = reason
    state["pending_request_id"] = request["request_id"]
    state["failed_nodes"] = list(
        dict.fromkeys([*state.get("failed_nodes", []), str(node["node_id"])])
    )
    save_state(workspace_root, state)
    return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)


def recovery_goal_context(
    goal: str,
    *,
    failed_node_id: str,
    failure_reason: str,
    gate_status_refs: list[str],
) -> str:
    refs = "\n".join(f"- {ref}" for ref in gate_status_refs) or "- none"
    return (
        f"{goal}\n\n"
        "Failure recovery context:\n"
        f"- failed_node_id: {failed_node_id}\n"
        f"- failure_reason: {failure_reason}\n"
        "- gate_status_refs:\n"
        f"{refs}\n"
        "Fix the smallest issue that can make the failed node pass, then return "
        "a structured worker result. Do not broaden scope."
    )


def run_failure_recovery_node(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    registry: dict[str, Any],
    segment: str,
    goal: str,
    failed_node: dict[str, Any],
    failure_reason: str,
    gate_status_refs: list[str],
    recovery_attempted_for: set[str],
    completed: list[str],
) -> str | int | None:
    failed_node_id = str(failed_node["node_id"])
    if str(failed_node.get("run_when") or "always") == "on_failure":
        return None
    if failed_node_id in recovery_attempted_for:
        return None
    candidates = [
        node
        for node in on_failure_nodes(registry, segment)
        if str(node.get("node_id")) != failed_node_id
    ]
    if not candidates:
        return None
    recovery_node = candidates[0]
    recovery_node_id = str(recovery_node["node_id"])
    recovery_attempted_for.add(failed_node_id)
    state["current_node_id"] = recovery_node_id
    state["current_attempt"] = 1
    save_state(workspace_root, state)
    append_event(
        workspace_root,
        "NODE_STARTED",
        run_id=run_id,
        segment=segment,
        node_id=recovery_node_id,
        status="running",
        payload={
            "skill": recovery_node.get("skill"),
            "run_when": "on_failure",
            "recovery_for": failed_node_id,
        },
    )
    preconditions = node_precondition_result(
        workspace_root,
        run_id=run_id,
        node=recovery_node,
    )
    if not preconditions["ok"]:
        ref = write_json_artifact(
            workspace_root,
            (
                f"{SUPERVISOR_DIR}/runs/{run_id}/gate_results/"
                f"{recovery_node_id}.preconditions.json"
            ),
            preconditions,
        )
        return pause_for_node_request(
            workspace_root,
            args=args,
            run_id=run_id,
            state=state,
            node=recovery_node,
            reason="failure_recovery_precondition_failed",
            question=(
                f"{recovery_node_id} could not run before retrying "
                f"{failed_node_id}."
            ),
            gate_status_refs=[ref, *gate_status_refs],
        )

    recovery_goal = recovery_goal_context(
        goal,
        failed_node_id=failed_node_id,
        failure_reason=failure_reason,
        gate_status_refs=gate_status_refs,
    )
    worker_result = run_node_worker(
        workspace_root,
        args=args,
        run_id=run_id,
        node=recovery_node,
        goal=recovery_goal,
    )
    worker_result_ref = write_worker_result(
        workspace_root,
        run_id=run_id,
        node_id=recovery_node_id,
        result=worker_result,
    )
    worker_errors = validate_worker_result(workspace_root, worker_result)
    if worker_errors:
        postcondition_result = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "node_id": recovery_node_id,
            "ok": False,
            "gate_ledger": [
                {
                    "command": "validate_worker_result",
                    "result": "FAIL",
                    "reason": "; ".join(worker_errors),
                    "artifacts": [worker_result_ref],
                }
            ],
            "failed_checks": worker_errors,
        }
        record_ref = write_supervisor_node_record(
            workspace_root,
            run_id=run_id,
            node=recovery_node,
            worker_result=worker_result,
            worker_result_ref=worker_result_ref,
            postcondition_result=postcondition_result,
            status="failed",
            next_node=failed_node_id,
        )
        return pause_for_node_request(
            workspace_root,
            args=args,
            run_id=run_id,
            state=state,
            node=recovery_node,
            reason="failure_recovery_worker_contract_violation",
            question=f"{recovery_node_id} returned an invalid worker result.",
            gate_status_refs=[worker_result_ref, record_ref, *gate_status_refs],
        )
    if worker_result.get("status") == "interrupt_requested":
        interrupt = worker_result.get("interrupt_request")
        reason = (
            str(interrupt.get("reason"))
            if isinstance(interrupt, dict) and interrupt.get("reason")
            else "failure_recovery_interrupt_requested"
        )
        question = (
            str(interrupt.get("question"))
            if isinstance(interrupt, dict) and interrupt.get("question")
            else f"{recovery_node_id} requested interruption."
        )
        request_type = (
            str(interrupt.get("type"))
            if isinstance(interrupt, dict) and interrupt.get("type")
            else "STEER"
        )
        allowed = (
            interrupt.get("allowed_responses")
            if isinstance(interrupt, dict)
            and isinstance(interrupt.get("allowed_responses"), list)
            else None
        )
        return pause_for_node_request(
            workspace_root,
            args=args,
            run_id=run_id,
            state=state,
            node=recovery_node,
            reason=reason,
            question=question,
            request_type=request_type,
            allowed_responses=[str(item) for item in allowed] if allowed else None,
            gate_status_refs=[worker_result_ref, *gate_status_refs],
        )

    postcondition_result = evaluate_node_postconditions(
        workspace_root,
        recovery_node,
        run_id=run_id,
        worker_result=worker_result,
    )
    node_status = (
        "success"
        if worker_result.get("status") == "success"
        and postcondition_result["ok"]
        else "failed"
    )
    record_ref = write_supervisor_node_record(
        workspace_root,
        run_id=run_id,
        node=recovery_node,
        worker_result=worker_result,
        worker_result_ref=worker_result_ref,
        postcondition_result=postcondition_result,
        status=node_status,
        next_node=failed_node_id,
    )
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment=segment,
        node_id=recovery_node_id,
        status=node_status,
        payload={
            "postcondition": "PASS" if postcondition_result["ok"] else "FAIL",
            "node_record": record_ref,
            "worker_result": worker_result_ref,
            "run_when": "on_failure",
            "recovery_for": failed_node_id,
        },
    )
    if node_status != "success":
        return pause_for_node_request(
            workspace_root,
            args=args,
            run_id=run_id,
            state=state,
            node=recovery_node,
            reason="failure_recovery_failed",
            question=(
                f"{recovery_node_id} ran but did not recover {failed_node_id}."
            ),
            gate_status_refs=[worker_result_ref, record_ref, *gate_status_refs],
        )
    archive_refs = archive_node_attempt_artifacts(
        workspace_root,
        run_id=run_id,
        node_id=failed_node_id,
        reason=failure_reason,
        gate_status_refs=gate_status_refs,
    )
    append_event(
        workspace_root,
        "NODE_ATTEMPT_ARCHIVED",
        run_id=run_id,
        segment=segment,
        node_id=failed_node_id,
        status="archived",
        payload={
            "reason": failure_reason,
            "artifacts": archive_refs,
            "recovery_node_id": recovery_node_id,
        },
    )
    completed.append(recovery_node_id)
    state["completed_nodes"] = list(dict.fromkeys(completed))
    state["failed_nodes"] = [
        failed
        for failed in state.get("failed_nodes", [])
        if failed != recovery_node_id
    ]
    save_state(workspace_root, state)
    return "retry"


def adopt_previous_missing_handoff_success(
    workspace_root: Path,
    *,
    run_id: str,
    state: dict[str, Any],
    segment: str,
    node: dict[str, Any],
    completed: list[str],
) -> bool:
    node_id = str(node["node_id"])
    record_path = (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "node_runs"
        / f"{node_id}.json"
    )
    if not record_path.exists():
        return False
    record = load_json(record_path)
    if not isinstance(record, dict) or record.get("status") != "failed":
        return False
    postcondition_result = record.get("postcondition_result")
    if not isinstance(postcondition_result, dict) or not postcondition_result.get("ok"):
        return False
    worker_ref = record.get("worker_result_ref")
    if not isinstance(worker_ref, str) or not worker_ref:
        return False
    worker_result = load_json(workspace_root / worker_ref)
    if not isinstance(worker_result, dict):
        return False
    if worker_result.get("summary") != "codex worker did not write worker result JSON":
        return False
    record["status"] = "success"
    record["adoption_reason"] = "codex_missing_handoff_but_postconditions_passed"
    record["adoption_worker_exit_code"] = worker_result.get("exit_code")
    record["adopted_at"] = utc_now()
    atomic_write_json(record_path, record)
    append_event(
        workspace_root,
        "NODE_ADOPTED_FROM_POSTCONDITIONS",
        run_id=run_id,
        segment=segment,
        node_id=node_id,
        status="success",
        payload={
            "node_record": record_path.relative_to(workspace_root).as_posix(),
            "worker_result": worker_ref,
            "reason": "codex_missing_handoff_but_postconditions_passed",
        },
    )
    completed.append(node_id)
    state["completed_nodes"] = list(dict.fromkeys(completed))
    state["failed_nodes"] = [
        failed for failed in state.get("failed_nodes", []) if failed != node_id
    ]
    save_state(workspace_root, state)
    return True


def run_supervised_nodes(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    segment: str,
    goal: str,
    node_ids: set[str] | None = None,
) -> int | None:
    registry = load_node_registry(workspace_root)
    nodes = ordered_segment_nodes(registry, segment, node_ids=node_ids)
    completed = list(state.get("completed_nodes", []))
    recovery_attempted_for: set[str] = set()
    index = 0
    while index < len(nodes):
        node = nodes[index]
        node_id = str(node["node_id"])
        if node_id in completed:
            index += 1
            continue
        if adopt_previous_missing_handoff_success(
            workspace_root,
            run_id=run_id,
            state=state,
            segment=segment,
            node=node,
            completed=completed,
        ):
            index += 1
            continue
        state["current_node_id"] = node_id
        state["current_attempt"] = 1
        save_state(workspace_root, state)
        append_event(
            workspace_root,
            "NODE_STARTED",
            run_id=run_id,
            segment=segment,
            node_id=node_id,
            status="running",
            payload={"skill": node.get("skill")},
        )
        preconditions = node_precondition_result(
            workspace_root,
            run_id=run_id,
            node=node,
        )
        if not preconditions["ok"]:
            ref = write_json_artifact(
                workspace_root,
                f"{SUPERVISOR_DIR}/runs/{run_id}/gate_results/{node_id}.preconditions.json",
                preconditions,
            )
            return pause_for_node_request(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                node=node,
                reason="node_precondition_failed",
                question=f"Preconditions failed before running {node_id}.",
                gate_status_refs=[ref],
            )

        worker_result = run_node_worker(
            workspace_root,
            args=args,
            run_id=run_id,
            node=node,
            goal=goal,
        )
        worker_result_ref = write_worker_result(
            workspace_root,
            run_id=run_id,
            node_id=node_id,
            result=worker_result,
        )
        worker_errors = validate_worker_result(workspace_root, worker_result)
        if worker_errors:
            postcondition_result = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "node_id": node_id,
                "ok": False,
                "gate_ledger": [
                    {
                        "command": "validate_worker_result",
                        "result": "FAIL",
                        "reason": "; ".join(worker_errors),
                        "artifacts": [worker_result_ref],
                    }
                ],
                "failed_checks": worker_errors,
            }
            record_ref = write_supervisor_node_record(
                workspace_root,
                run_id=run_id,
                node=node,
                worker_result=worker_result,
                worker_result_ref=worker_result_ref,
                postcondition_result=postcondition_result,
                status="failed",
                next_node=None,
            )
            recovery = run_failure_recovery_node(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                registry=registry,
                segment=segment,
                goal=goal,
                failed_node=node,
                failure_reason="worker_contract_violation",
                gate_status_refs=[worker_result_ref, record_ref],
                recovery_attempted_for=recovery_attempted_for,
                completed=completed,
            )
            if isinstance(recovery, int):
                return recovery
            if recovery == "retry":
                continue
            return pause_for_node_request(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                node=node,
                reason="worker_contract_violation",
                question=f"Worker result for {node_id} failed validation.",
                gate_status_refs=[worker_result_ref, record_ref],
            )

        if worker_result.get("status") == "interrupt_requested":
            interrupt = worker_result.get("interrupt_request")
            reason = (
                str(interrupt.get("reason"))
                if isinstance(interrupt, dict) and interrupt.get("reason")
                else "worker_interrupt_requested"
            )
            question = (
                str(interrupt.get("question"))
                if isinstance(interrupt, dict) and interrupt.get("question")
                else f"Worker requested interruption for {node_id}."
            )
            request_type = (
                str(interrupt.get("type"))
                if isinstance(interrupt, dict) and interrupt.get("type")
                else "STEER"
            )
            allowed = (
                interrupt.get("allowed_responses")
                if isinstance(interrupt, dict)
                and isinstance(interrupt.get("allowed_responses"), list)
                else None
            )
            return pause_for_node_request(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                node=node,
                reason=reason,
                question=question,
                request_type=request_type,
                allowed_responses=[str(item) for item in allowed] if allowed else None,
                gate_status_refs=[worker_result_ref],
            )

        postcondition_result = evaluate_node_postconditions(
            workspace_root,
            node,
            run_id=run_id,
            worker_result=worker_result,
        )
        node_status = (
            "success"
            if worker_result.get("status") == "success"
            and postcondition_result["ok"]
            else "failed"
        )
        next_node = (
            str(nodes[index + 1]["node_id"]) if index + 1 < len(nodes) else None
        )
        record_ref = write_supervisor_node_record(
            workspace_root,
            run_id=run_id,
            node=node,
            worker_result=worker_result,
            worker_result_ref=worker_result_ref,
            postcondition_result=postcondition_result,
            status=node_status,
            next_node=next_node,
        )
        append_event(
            workspace_root,
            "NODE_COMPLETED",
            run_id=run_id,
            segment=segment,
            node_id=node_id,
            status=node_status,
            payload={
                "postcondition": (
                    "PASS" if postcondition_result["ok"] else "FAIL"
                ),
                "node_record": record_ref,
                "worker_result": worker_result_ref,
            },
        )
        if node_status != "success":
            recovery = run_failure_recovery_node(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                registry=registry,
                segment=segment,
                goal=goal,
                failed_node=node,
                failure_reason="node_postcondition_failed",
                gate_status_refs=[worker_result_ref, record_ref],
                recovery_attempted_for=recovery_attempted_for,
                completed=completed,
            )
            if isinstance(recovery, int):
                return recovery
            if recovery == "retry":
                continue
            return pause_for_node_request(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                node=node,
                reason="node_postcondition_failed",
                question=(
                    f"{node_id} ran but did not satisfy supervisor "
                    "postconditions."
                ),
                gate_status_refs=[worker_result_ref, record_ref],
            )
        completed.append(node_id)
        state["completed_nodes"] = list(dict.fromkeys(completed))
        state["failed_nodes"] = [
            failed
            for failed in state.get("failed_nodes", [])
            if failed != node_id
        ]
        save_state(workspace_root, state)
        index += 1
    return None


def guard_segment_start(workspace_root: Path, segment: str) -> None:
    if not state_path(workspace_root).exists():
        if pending_request_path(workspace_root).exists():
            raise ValueError(
                "pending supervisor request exists without state; run "
                "`workflow_ctl status --json` or `workflow_ctl recover --json` "
                "before starting a new segment"
            )
        return
    state = load_state(workspace_root)
    if state.get("status") in {"running", "paused", "recovering"}:
        raise ValueError(
            "active supervisor run exists; run `workflow_ctl status --json`, "
            "`workflow_ctl recover --repair-stale-running --auto-resume-answered "
            "--json`, or resume/stop the pending request before starting a new run"
        )
    if pending_request_path(workspace_root).exists():
        raise ValueError(
            "pending supervisor request exists; resolve or recover it before "
            "starting a new segment"
        )
    if segment not in {"build", "iterate", "release"}:
        return
    if (
        state.get("segment") == "prepare"
        and state.get("segment_status") in PREPARE_NON_UNLOCKING_STATUSES
    ):
        raise ValueError(
            "prepare_hitl_poc cannot unlock build, iterate, or release; "
            "prepare_complete or an explicit legacy/manual compatibility "
            "decision is required"
        )


def start_prepare_hitl_poc(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
) -> int:
    state["current_node_id"] = "prepare_readiness_preflight"
    save_state(workspace_root, state)
    _preflight, readiness_errors, readiness_input_refs = (
        run_prepare_readiness_preflight(workspace_root)
    )
    readiness_record_path = write_prepare_readiness_node_record(
        workspace_root,
        run_id=run_id,
        input_refs=readiness_input_refs,
        errors=readiness_errors,
    )
    readiness_ref = readiness_preflight_path(workspace_root).relative_to(
        workspace_root
    ).as_posix()
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_readiness_preflight",
        status="success" if not readiness_errors else "failed",
        payload={
            "postcondition": "PASS" if not readiness_errors else "FAIL",
            "mode": "prepare_readiness_preflight",
            "node_record": readiness_record_path.relative_to(
                workspace_root
            ).as_posix(),
        },
    )
    if readiness_errors:
        request = create_prepare_readiness_request(
            workspace_root,
            run_id=run_id,
            node_record_path=readiness_record_path,
            errors=readiness_errors,
        )
        state["status"] = "paused"
        state["segment_status"] = "prepare_readiness_input_required"
        state["pending_request_id"] = request["request_id"]
        state["failed_nodes"] = ["prepare_readiness_preflight"]
        state["last_failure"] = {
            "kind": "prepare_readiness_preflight_failed",
            "node_record": readiness_record_path.relative_to(
                workspace_root
            ).as_posix(),
            "errors": readiness_errors,
        }
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)

    state["current_node_id"] = "prepare_protocol_compiler"
    state["completed_nodes"] = ["prepare_readiness_preflight"]
    save_state(workspace_root, state)
    protocol_result = run_protocol_compiler(workspace_root, build_id=run_id)
    protocol_record_path = write_prepare_protocol_node_record(
        workspace_root,
        run_id=run_id,
        protocol_result=protocol_result,
        readiness_ref=readiness_ref,
    )
    protocol_ref = protocol_record_path.relative_to(workspace_root).as_posix()
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_protocol_compiler",
        status="success" if protocol_result["exit_code"] == 0 else "failed",
        payload={
            "postcondition": (
                "PASS" if protocol_result["exit_code"] == 0 else "FAIL"
            ),
            "mode": "prepare_protocol_compiler",
            "node_record": protocol_ref,
        },
    )
    if protocol_result["exit_code"] != 0:
        request = create_prepare_protocol_request(
            workspace_root,
            run_id=run_id,
            node_record_path=protocol_record_path,
            protocol_result=protocol_result,
        )
        state["status"] = "paused"
        state["segment_status"] = "prepare_protocol_compiler_failed"
        state["pending_request_id"] = request["request_id"]
        state["failed_nodes"] = ["prepare_protocol_compiler"]
        state["last_failure"] = {
            "kind": "prepare_protocol_compiler_failed",
            "node_record": protocol_ref,
            "exit_code": protocol_result["exit_code"],
        }
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)

    state["current_node_id"] = "prepare_review_packet"
    state["completed_nodes"] = [
        "prepare_readiness_preflight",
        "prepare_protocol_compiler",
    ]
    save_state(workspace_root, state)
    gate_result = run_dynamic_context_gate(
        workspace_root,
        stage="wf5",
        build_id=run_id,
        write_review_packet=True,
    )
    node_record_path = write_prepare_review_packet_node_record(
        workspace_root,
        run_id=run_id,
        gate_result=gate_result,
        readiness_ref=readiness_ref,
        protocol_ref=protocol_ref,
    )
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_review_packet",
        status="success" if gate_result["exit_code"] == 0 else "failed",
        payload={
            "postcondition": "PASS" if gate_result["exit_code"] == 0 else "FAIL",
            "mode": "prepare_hitl_poc",
            "node_record": node_record_path.relative_to(workspace_root).as_posix(),
        },
    )
    request = create_prepare_approval_request(
        workspace_root,
        run_id=run_id,
        gate_result=gate_result,
        node_record_path=node_record_path,
    )
    state["status"] = "paused"
    state["segment_status"] = "prepare_waiting_for_approval"
    state["pending_request_id"] = request["request_id"]
    state["completed_nodes"] = [
        "prepare_readiness_preflight",
        "prepare_protocol_compiler",
        "prepare_review_packet",
    ]
    save_state(workspace_root, state)
    return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)


def continue_prepare_complete_after_supervised_nodes(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    readiness_ref: str,
) -> int:
    state["current_node_id"] = "prepare_protocol_compiler"
    save_state(workspace_root, state)
    protocol_result = run_protocol_compiler(workspace_root, build_id=run_id)
    protocol_record_path = write_prepare_protocol_node_record(
        workspace_root,
        run_id=run_id,
        protocol_result=protocol_result,
        readiness_ref=readiness_ref,
    )
    protocol_ref = protocol_record_path.relative_to(workspace_root).as_posix()
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_protocol_compiler",
        status="success" if protocol_result["exit_code"] == 0 else "failed",
        payload={
            "postcondition": (
                "PASS" if protocol_result["exit_code"] == 0 else "FAIL"
            ),
            "mode": "prepare_complete_protocol_compiler",
            "node_record": protocol_ref,
        },
    )
    if protocol_result["exit_code"] != 0:
        request = create_prepare_protocol_request(
            workspace_root,
            run_id=run_id,
            node_record_path=protocol_record_path,
            protocol_result=protocol_result,
        )
        state["status"] = "paused"
        state["segment_status"] = "prepare_protocol_compiler_failed"
        state["pending_request_id"] = request["request_id"]
        state["failed_nodes"] = ["prepare_protocol_compiler"]
        state["last_failure"] = {
            "kind": "prepare_protocol_compiler_failed",
            "node_record": protocol_ref,
            "exit_code": protocol_result["exit_code"],
        }
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)

    state["completed_nodes"] = list(
        dict.fromkeys([*state.get("completed_nodes", []), "prepare_protocol_compiler"])
    )
    state["current_node_id"] = "prepare_review_packet"
    save_state(workspace_root, state)
    gate_result = run_dynamic_context_gate(
        workspace_root,
        stage="wf5",
        build_id=run_id,
        write_review_packet=True,
    )
    node_record_path = write_prepare_review_packet_node_record(
        workspace_root,
        run_id=run_id,
        gate_result=gate_result,
        readiness_ref=readiness_ref,
        protocol_ref=protocol_ref,
    )
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_review_packet",
        status="success" if gate_result["exit_code"] == 0 else "failed",
        payload={
            "postcondition": "PASS" if gate_result["exit_code"] == 0 else "FAIL",
            "mode": "prepare_complete_review_packet",
            "node_record": node_record_path.relative_to(workspace_root).as_posix(),
        },
    )
    if gate_result["exit_code"] != 0:
        return pause_for_node_request(
            workspace_root,
            args=args,
            run_id=run_id,
            state=state,
            node={"node_id": "prepare_review_packet", "segment": "prepare"},
            reason="prepare_wf5_gate_failed",
            question="WF5 dynamic-context gate failed after data and baseline prep.",
            gate_status_refs=[node_record_path.relative_to(workspace_root).as_posix()],
        )

    state["status"] = "completed"
    state["segment_status"] = "prepare_complete"
    state["current_node_id"] = None
    state["current_attempt"] = 0
    state["pending_request_id"] = None
    state["completed_nodes"] = list(
        dict.fromkeys([*state.get("completed_nodes", []), "prepare_review_packet"])
    )
    save_state(workspace_root, state)
    pending = load_json_if_exists(pending_request_path(workspace_root), {})
    if isinstance(pending, dict) and pending.get("run_id") == run_id:
        pending_request_path(workspace_root).unlink(missing_ok=True)
    append_event(
        workspace_root,
        "RUN_COMPLETED",
        run_id=run_id,
        segment="prepare",
        status="completed",
        payload={"mode": "prepare_complete"},
    )
    return emit_status(workspace_root, args.json)


def start_prepare_complete(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    goal: str,
) -> int:
    state["current_node_id"] = "prepare_readiness_preflight"
    save_state(workspace_root, state)
    _preflight, readiness_errors, readiness_input_refs = (
        run_prepare_readiness_preflight(
            workspace_root,
            allow_creatable_paths=True,
        )
    )
    bridge_ref = getattr(args, "_grill_bridge_ref", None)
    if isinstance(bridge_ref, str):
        readiness_input_refs.append(bridge_ref)
    readiness_record_path = write_prepare_readiness_node_record(
        workspace_root,
        run_id=run_id,
        input_refs=readiness_input_refs,
        errors=readiness_errors,
    )
    readiness_ref = readiness_preflight_path(workspace_root).relative_to(
        workspace_root
    ).as_posix()
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_readiness_preflight",
        status="success" if not readiness_errors else "failed",
        payload={
            "postcondition": "PASS" if not readiness_errors else "FAIL",
            "mode": "prepare_complete_readiness_preflight",
            "node_record": readiness_record_path.relative_to(
                workspace_root
            ).as_posix(),
        },
    )
    if readiness_errors:
        request = create_prepare_readiness_request(
            workspace_root,
            run_id=run_id,
            node_record_path=readiness_record_path,
            errors=readiness_errors,
        )
        state["status"] = "paused"
        state["segment_status"] = "prepare_readiness_input_required"
        state["pending_request_id"] = request["request_id"]
        state["failed_nodes"] = ["prepare_readiness_preflight"]
        state["last_failure"] = {
            "kind": "prepare_readiness_preflight_failed",
            "node_record": readiness_record_path.relative_to(
                workspace_root
            ).as_posix(),
            "errors": readiness_errors,
        }
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)

    state["completed_nodes"] = ["prepare_readiness_preflight"]
    save_state(workspace_root, state)
    acquisition_exit = run_prepare_acquisition_plan_gate(
        workspace_root,
        args=args,
        run_id=run_id,
        state=state,
        readiness_ref=readiness_ref,
    )
    if acquisition_exit is not None:
        return acquisition_exit

    save_state(workspace_root, state)
    exit_code = run_supervised_nodes(
        workspace_root,
        args=args,
        run_id=run_id,
        state=state,
        segment="prepare",
        goal=goal,
        node_ids={"prepare_data_prep", "prepare_baseline_repro"},
    )
    if exit_code is not None:
        return exit_code

    return continue_prepare_complete_after_supervised_nodes(
        workspace_root,
        args=args,
        run_id=run_id,
        state=state,
        readiness_ref=readiness_ref,
    )


def start_build_segment(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    goal: str,
) -> int:
    exit_code = run_supervised_nodes(
        workspace_root,
        args=args,
        run_id=run_id,
        state=state,
        segment="build",
        goal=goal,
    )
    if exit_code is not None:
        return exit_code
    state["status"] = "completed"
    state["segment_status"] = "build_ready_for_iterate"
    state["current_node_id"] = None
    state["current_attempt"] = 0
    state["pending_request_id"] = None
    save_state(workspace_root, state)
    append_event(
        workspace_root,
        "RUN_COMPLETED",
        run_id=run_id,
        segment="build",
        status="completed",
        payload={"mode": "build_ready_for_iterate"},
    )
    return emit_status(workspace_root, args.json)


def start_prepare_dry_run(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
) -> int:
    state["current_node_id"] = "prepare_readiness_preflight"
    save_state(workspace_root, state)
    _preflight, readiness_errors, readiness_input_refs = (
        run_prepare_readiness_preflight(workspace_root)
    )
    readiness_record_path = write_prepare_readiness_node_record(
        workspace_root,
        run_id=run_id,
        input_refs=readiness_input_refs,
        errors=readiness_errors,
    )
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="prepare",
        node_id="prepare_readiness_preflight",
        status="success" if not readiness_errors else "failed",
        payload={
            "postcondition": "PASS" if not readiness_errors else "FAIL",
            "mode": "prepare_dry_run_readiness_preflight",
            "node_record": readiness_record_path.relative_to(
                workspace_root
            ).as_posix(),
        },
    )
    state["status"] = "completed"
    state["segment_status"] = (
        "dry_run_readiness_passed"
        if not readiness_errors
        else "dry_run_readiness_failed"
    )
    state["current_node_id"] = None
    state["current_attempt"] = 0
    state["pending_request_id"] = None
    state["completed_nodes"] = ["prepare_readiness_preflight"]
    if readiness_errors:
        state["failed_nodes"] = ["prepare_readiness_preflight"]
        state["last_failure"] = {
            "kind": "prepare_dry_run_readiness_failed",
            "node_record": readiness_record_path.relative_to(
                workspace_root
            ).as_posix(),
            "errors": readiness_errors,
        }
    save_state(workspace_root, state)
    append_event(
        workspace_root,
        "RUN_COMPLETED",
        run_id=run_id,
        segment="prepare",
        status="completed",
        payload={"mode": state["segment_status"]},
    )
    return emit_status(workspace_root, args.json)


def sync_auto_iterate_status(
    workspace_root: Path,
    *,
    run_id: str,
    state: dict[str, Any],
    start_result: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    status_result = auto_iterate_status(workspace_root)
    node_record_path = write_iterate_delegate_node_record(
        workspace_root,
        run_id=run_id,
        start_result=start_result,
        status_result=status_result,
    )
    status_payload = status_result.get("stdout")
    if not isinstance(status_payload, dict):
        raise ValueError("auto-iterate status payload must be an object")
    halt_reason = status_payload.get("halt_reason")
    status = status_payload.get("status")
    if isinstance(halt_reason, str) and halt_reason in AUTO_ITERATE_MANUAL_HALT_REASONS:
        request = create_auto_iterate_pending_request(
            workspace_root,
            run_id=run_id,
            status_result=status_result,
            reason=AUTO_ITERATE_MANUAL_HALT_REASONS[halt_reason],
        )
        state["status"] = "paused"
        state["segment_status"] = AUTO_ITERATE_MANUAL_HALT_REASONS[halt_reason]
        state["pending_request_id"] = request["request_id"]
        state["current_node_id"] = "iterate_delegate_auto_iterate"
        state["completed_nodes"] = ["iterate_delegate_auto_iterate"]
        save_state(workspace_root, state)
        return EXIT_MANUAL_ACTION, status_result
    if status == "failed" or halt_reason == "fatal_controller_error":
        state["status"] = "failed"
        state["segment_status"] = auto_iterate_segment_status(status_payload)
        state["last_failure"] = {
            "kind": "auto_iterate_delegation_failed",
            "halt_reason": halt_reason,
            "status": status,
            "node_record": node_record_path.relative_to(workspace_root).as_posix(),
        }
        save_state(workspace_root, state)
        return EXIT_FATAL, status_result
    state["status"] = "completed"
    state["segment_status"] = auto_iterate_segment_status(status_payload)
    state["pending_request_id"] = None
    state["current_node_id"] = None
    state["completed_nodes"] = ["iterate_delegate_auto_iterate"]
    state["resolved_inputs_ref"] = (
        f"{SUPERVISOR_DIR}/runs/{run_id}/runtime/auto_iterate_status.json"
    )
    save_state(workspace_root, state)
    append_event(
        workspace_root,
        "RUN_COMPLETED",
        run_id=run_id,
        segment="iterate",
        status="completed",
        payload={
            "mode": state["segment_status"],
            "auto_iterate_status": status,
            "halt_reason": halt_reason,
        },
    )
    return EXIT_OK, status_result


def start_iterate_delegation(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
) -> int:
    if args.skip_dynamic_preflight and not args.skip_dynamic_preflight_reason:
        raise ValueError(
            "--skip-dynamic-preflight requires --skip-dynamic-preflight-reason"
        )
    state["current_node_id"] = "iterate_delegate_auto_iterate"
    save_state(workspace_root, state)
    start_result = run_auto_iterate_command(
        workspace_root,
        "start",
        auto_iterate_start_args(args),
    )
    append_event(
        workspace_root,
        "AUTO_ITERATE_DELEGATED",
        run_id=run_id,
        segment="iterate",
        node_id="iterate_delegate_auto_iterate",
        status="started",
        payload={
            "exit_code": start_result["exit_code"],
            "command": start_result["command"],
        },
    )
    exit_code, _status_result = sync_auto_iterate_status(
        workspace_root,
        run_id=run_id,
        state=state,
        start_result=start_result,
    )
    return emit_status(workspace_root, args.json, exit_code=exit_code)


def start_change_intake(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    goal: str,
    previous_state: dict[str, Any] | None,
) -> int:
    state["current_node_id"] = "change_classify_request"
    save_state(workspace_root, state)
    context = collect_change_context(
        workspace_root,
        request_text=goal,
        previous_state=previous_state,
    )
    context_ref = write_json_artifact(
        workspace_root,
        f"{SUPERVISOR_DIR}/runs/{run_id}/runtime/change_context.json",
        context,
    )
    change_request = classify_change_request(
        request_text=goal,
        run_id=run_id,
        context=context,
    )
    change_request_ref = write_json_artifact(
        workspace_root,
        f"{SUPERVISOR_DIR}/runs/{run_id}/runtime/change_request.json",
        change_request,
    )
    schema_errors = validate_schema(
        workspace_root,
        change_request,
        "change_request.schema.json",
        change_request_ref,
    )
    node_record_path = write_change_classify_node_record(
        workspace_root,
        run_id=run_id,
        change_request=change_request,
        context_ref=context_ref,
        change_request_ref=change_request_ref,
        schema_errors=schema_errors,
    )
    append_event(
        workspace_root,
        "CHANGE_CLASSIFIED",
        run_id=run_id,
        segment="change",
        node_id="change_classify_request",
        status="success" if not schema_errors else "failed",
        payload={
            "change_type": change_request.get("change_type"),
            "route": change_request.get("route"),
            "confidence": change_request.get("confidence"),
            "node_record": node_record_path.relative_to(workspace_root).as_posix(),
        },
    )
    if schema_errors:
        state["status"] = "failed"
        state["segment_status"] = "change_request_schema_failed"
        state["failed_nodes"] = ["change_classify_request"]
        state["last_failure"] = {
            "kind": "change_request_schema_failed",
            "errors": schema_errors,
            "node_record": node_record_path.relative_to(workspace_root).as_posix(),
        }
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_INVALID_INPUT)

    if (
        change_request.get("confidence") == "low"
        or change_request.get("route") == "steer"
    ):
        request = create_change_steer_request(
            workspace_root,
            run_id=run_id,
            change_request_ref=change_request_ref,
            node_record_path=node_record_path,
            change_request=change_request,
        )
        state["status"] = "paused"
        state["segment_status"] = "change_route_uncertain"
        state["pending_request_id"] = request["request_id"]
        state["completed_nodes"] = ["change_classify_request"]
        state["resolved_inputs_ref"] = change_request_ref
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)

    route = str(change_request["route"])
    state["status"] = "completed"
    state["segment_status"] = route_status(route)
    state["current_node_id"] = None
    state["current_attempt"] = 0
    state["completed_nodes"] = ["change_classify_request"]
    state["resolved_inputs_ref"] = change_request_ref
    save_state(workspace_root, state)
    append_event(
        workspace_root,
        "RUN_COMPLETED",
        run_id=run_id,
        segment="change",
        status="completed",
        payload={
            "mode": state["segment_status"],
            "change_request": change_request_ref,
        },
    )
    return emit_status(workspace_root, args.json)


def start_release_segment(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    goal: str,
) -> int:
    release_action = release_action_from_goal(goal)
    if release_action is None:
        state["current_node_id"] = "release_claim_approval"
        save_state(workspace_root, state)
        request = create_release_action_steer_request(
            workspace_root,
            run_id=run_id,
        )
        state["status"] = "paused"
        state["segment_status"] = "release_action_unclear"
        state["pending_request_id"] = request["request_id"]
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)

    exit_code = run_supervised_nodes(
        workspace_root,
        args=args,
        run_id=run_id,
        state=state,
        segment="release",
        goal=goal,
        node_ids={"release_final_exp_matrix"},
    )
    if exit_code is not None:
        return exit_code

    return continue_release_after_final_exp(
        workspace_root,
        args=args,
        run_id=run_id,
        state=state,
        release_action=release_action,
    )


def continue_release_after_final_exp(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    run_id: str,
    state: dict[str, Any],
    release_action: str,
) -> int:
    state["current_node_id"] = "release_claim_approval"
    save_state(workspace_root, state)

    gate_result = run_dynamic_context_gate(
        workspace_root,
        stage="wf12",
        build_id=run_id,
        write_review_packet=True,
    )
    blockers = release_gate_blockers(gate_result)
    node_record_path = write_release_claim_node_record(
        workspace_root,
        run_id=run_id,
        gate_result=gate_result,
        release_action=release_action,
        blockers=blockers,
    )
    append_event(
        workspace_root,
        "NODE_COMPLETED",
        run_id=run_id,
        segment="release",
        node_id="release_claim_approval",
        status="success" if not blockers else "failed",
        payload={
            "postcondition": "PASS" if not blockers else "FAIL",
            "mode": "release_approval_gate",
            "node_record": node_record_path.relative_to(workspace_root).as_posix(),
        },
    )
    if blockers:
        request = create_release_gate_steer_request(
            workspace_root,
            run_id=run_id,
            node_record_path=node_record_path,
            gate_result=gate_result,
            blockers=blockers,
        )
        state["status"] = "paused"
        state["segment_status"] = "release_gate_failed"
        state["pending_request_id"] = request["request_id"]
        state["failed_nodes"] = ["release_claim_approval"]
        state["last_failure"] = {
            "kind": "release_gate_failed",
            "node_record": node_record_path.relative_to(workspace_root).as_posix(),
            "blockers": blockers,
        }
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)

    request = create_release_approval_request(
        workspace_root,
        run_id=run_id,
        gate_result=gate_result,
        node_record_path=node_record_path,
        release_action=release_action,
    )
    state["status"] = "paused"
    state["segment_status"] = "release_ready_for_approval"
    state["pending_request_id"] = request["request_id"]
    state["completed_nodes"] = list(
        dict.fromkeys([*state.get("completed_nodes", []), "release_claim_approval"])
    )
    save_state(workspace_root, state)
    return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)


def command_start(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    goal = read_goal(args)
    segment = args.segment
    guard_segment_start(workspace_root, segment)
    previous_state = None
    if state_path(workspace_root).exists():
        loaded_state = load_json_if_exists(state_path(workspace_root), {})
        if isinstance(loaded_state, dict):
            previous_state = loaded_state
    run_id = new_run_id()
    supervisor_root(workspace_root).mkdir(parents=True, exist_ok=True)
    acquire_lock(workspace_root, run_id)
    try:
        grill_bridge_ref = None
        if segment == "prepare" and args.complete:
            grill_bridge_ref = attach_grill_bridge_to_args(
                workspace_root,
                run_id=run_id,
                args=args,
            )
        manifest = run_manifest(
            workspace_root=workspace_root,
            run_id=run_id,
            segment=segment,
            goal=goal,
            entrypoint=f"harness {segment}",
            allow_external_downloads=effective_allow_external_downloads(args),
            worker_mode=worker_mode(args),
            worker_command=args.worker_command,
            codex_home=args.codex_home,
            complete_prepare=bool(args.complete),
            grill_bridge_ref=grill_bridge_ref,
        )
        manifest_path = write_run_manifest(workspace_root, manifest)
        append_event(
            workspace_root,
            "RUN_STARTED",
            run_id=run_id,
            segment=segment,
            status="running",
            payload={
                "dry_run": bool(args.dry_run),
                "manifest": str(manifest_path),
                "grill_bridge": grill_bridge_ref,
            },
        )
        state = base_state(run_id, segment)
        save_state(workspace_root, state)

        if args.dry_run and segment == "prepare":
            return start_prepare_dry_run(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
            )

        if args.dry_run:
            write_node_record(
                workspace_root,
                run_id=run_id,
                segment=segment,
                status="success",
            )
            append_event(
                workspace_root,
                "NODE_COMPLETED",
                run_id=run_id,
                segment=segment,
                node_id="dry_run_bootstrap",
                status="success",
                payload={"postcondition": "PASS", "mode": "dry_run"},
            )
            state["status"] = "completed"
            state["segment_status"] = "dry_run_completed"
            state["current_node_id"] = None
            state["current_attempt"] = 0
            state["completed_nodes"] = ["dry_run_bootstrap"]
            save_state(workspace_root, state)
            append_event(
                workspace_root,
                "RUN_COMPLETED",
                run_id=run_id,
                segment=segment,
                status="completed",
                payload={"mode": "dry_run"},
            )
            save_state(workspace_root, state)
            return emit_status(workspace_root, args.json)

        if segment == "prepare" and args.complete:
            return start_prepare_complete(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                goal=goal,
            )

        if segment == "prepare":
            return start_prepare_hitl_poc(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
            )

        if segment == "build":
            return start_build_segment(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                goal=goal,
            )

        if segment == "iterate":
            return start_iterate_delegation(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
            )

        if segment == "change":
            return start_change_intake(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                goal=goal,
                previous_state=previous_state,
            )

        if segment == "release":
            return start_release_segment(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
                goal=goal,
            )

        request = create_pending_request(
            workspace_root,
            run_id=run_id,
            segment=segment,
            reason="segment_not_implemented_v0",
        )
        state["status"] = "paused"
        state["segment_status"] = "v0_interrupt"
        state["pending_request_id"] = request["request_id"]
        save_state(workspace_root, state)
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)
    finally:
        release_lock(workspace_root, run_id)


def supervisor_command(*parts: str) -> str:
    base = "tooling/workflow_supervisor/scripts/workflow_ctl.sh"
    rendered = [
        part if part.startswith("<") and part.endswith(">") else shlex.quote(part)
        for part in parts
    ]
    return " ".join([base, *rendered])


def pending_recovery_commands(pending_ref: dict[str, Any]) -> dict[str, Any]:
    request_id = pending_ref.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        return {}
    resume = supervisor_command(
        "resume",
        "--request-id",
        request_id,
        "--json",
    )
    answer = supervisor_command(
        "answer",
        "--request-id",
        request_id,
        "--json",
        "<answer.json>",
    )
    approve = supervisor_command(
        "approve",
        "--request-id",
        request_id,
        "--decision",
        "approve",
        "--approved-by",
        "<human>",
        "--json",
    )
    recover = supervisor_command(
        "recover",
        "--repair-stale-running",
        "--auto-resume-answered",
        "--json",
    )
    answered = bool(pending_ref.get("answered"))
    pending_type = pending_ref.get("type")
    if answered:
        next_command = resume
    elif pending_type == "APPROVE_ACTION":
        next_command = approve
    else:
        next_command = answer
    commands: dict[str, Any] = {
        "blocked_by": pending_ref.get("reason") or pending_type,
        "resume_command": next_command,
        "after_answer_command": resume,
        "recover_command": recover,
    }
    if pending_type == "APPROVE_ACTION":
        commands["approve_command"] = approve
    else:
        commands["answer_command"] = answer
    return commands


def status_payload(workspace_root: Path) -> dict[str, Any]:
    state = load_state(workspace_root)
    pending_ref = None
    if pending_request_path(workspace_root).exists():
        pending = load_json(pending_request_path(workspace_root))
        if isinstance(pending, dict):
            pending_ref = {
                "request_id": pending.get("request_id"),
                "path": f"{SUPERVISOR_DIR}/pending_request.json",
                "answered": bool(pending.get("answer_record")),
                "type": pending.get("type"),
                "node_id": pending.get("node_id"),
                "reason": pending.get("reason"),
                "question": pending.get("question"),
                "allowed_responses": pending.get("allowed_responses"),
                "gate_status_refs": pending.get("gate_status_refs"),
                "request_snapshot_hash": pending.get("request_snapshot_hash"),
            }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "state": state,
        "pending_request_ref": pending_ref,
        "last_event_seq": latest_event_seq(workspace_root),
    }
    active_worker = classify_worker_state(workspace_root, state=state)
    if active_worker is not None:
        payload["active_worker"] = active_worker
    acquisition_plan_ref = state.get("acquisition_plan_ref")
    if isinstance(acquisition_plan_ref, str) and acquisition_plan_ref:
        payload["acquisition_plan_ref"] = acquisition_plan_ref
    if pending_ref is not None:
        recovery = pending_recovery_commands(pending_ref)
        if recovery:
            payload["blocked_by"] = recovery["blocked_by"]
            payload["resume_command"] = recovery["resume_command"]
            payload["recovery"] = recovery
    return payload


def emit_status(
    workspace_root: Path,
    as_json: bool,
    *,
    exit_code: int = EXIT_OK,
) -> int:
    payload = status_payload(workspace_root)
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        state = payload["state"]
        print(
            f"{state.get('status')} "
            f"run={state.get('active_run_id')} "
            f"segment={state.get('segment')}"
        )
    return exit_code


def command_status(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    if not state_path(workspace_root).exists():
        if args.json:
            print(
                json.dumps(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "status": "missing",
                        "state_path": f"{SUPERVISOR_DIR}/state.json",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print("No workflow supervisor state found.")
        return EXIT_NO_STATE
    return emit_status(workspace_root, args.json)


def mutate_state_status(args: argparse.Namespace, status: str) -> int:
    workspace_root = repo_root(args.workspace_root)
    if not state_path(workspace_root).exists():
        return EXIT_NO_ACTIVE_RUN
    state = load_state(workspace_root)
    run_id = state.get("active_run_id")
    if not run_id or state.get("status") in {"completed", "stopped"}:
        return EXIT_NO_ACTIVE_RUN
    state["status"] = status
    if status == "paused" and not state.get("pending_request_id"):
        state["last_failure"] = {"reason": args.reason, "kind": "operator_pause"}
    if status == "stopped":
        state["pending_request_id"] = None
    append_event(
        workspace_root,
        "RUN_STOPPED" if status == "stopped" else "RUN_PAUSED",
        run_id=str(run_id),
        segment=state.get("segment"),
        status=status,
        payload={"reason": args.reason},
    )
    save_state(workspace_root, state)
    return emit_status(workspace_root, args.json)


def load_pending_request(workspace_root: Path) -> dict[str, Any]:
    pending = load_json(pending_request_path(workspace_root))
    if not isinstance(pending, dict):
        raise ValueError("pending request must be an object")
    errors = validate_pending_request(workspace_root, pending)
    if errors:
        raise ValueError("; ".join(errors))
    return pending


def validate_pending_request(
    workspace_root: Path,
    request: dict[str, Any],
) -> list[str]:
    errors = validate_schema(
        workspace_root,
        request,
        "human_interrupt.schema.json",
        "pending_request",
    )
    if request.get("type") not in VALID_PENDING_TYPES:
        errors.append(f"type must be one of {sorted(VALID_PENDING_TYPES)}")
    expected_hash = request_snapshot_hash(request)
    if request.get("request_snapshot_hash") != expected_hash:
        errors.append("request_snapshot_hash does not match pending request")
    exact_action = request.get("exact_action")
    if isinstance(exact_action, dict) and exact_action.get("action_hash"):
        if exact_action.get("action_hash") != exact_action_hash(exact_action):
            errors.append("exact_action.action_hash does not match exact_action")
    return errors


def answer_record_path(workspace_root: Path, request: dict[str, Any]) -> Path:
    run_id = str(request["run_id"])
    request_id = str(request["request_id"])
    return (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "runtime"
        / f"{request_id}.answer.json"
    )


def idempotency_record_path(workspace_root: Path, idempotency_key: str) -> Path:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return supervisor_root(workspace_root) / "answers" / f"{digest}.json"


def record_answer(
    workspace_root: Path,
    request: dict[str, Any],
    answer: dict[str, Any],
) -> None:
    key = answer.get("idempotency_key")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("answer requires non-empty idempotency_key")
    existing_path = idempotency_record_path(workspace_root, key)
    answer_hash = sha256_json(answer)
    if existing_path.exists():
        existing = load_json(existing_path)
        if isinstance(existing, dict) and existing.get("answer_hash") == answer_hash:
            return
        raise ValueError("idempotency_key reused with a different answer body")
    record = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request["request_id"],
        "run_id": request["run_id"],
        "idempotency_key": key,
        "answer_hash": answer_hash,
        "recorded_at": utc_now(),
        "answer": answer,
    }
    atomic_write_json(answer_record_path(workspace_root, request), record)
    atomic_write_json(existing_path, record)
    request["answer_record"] = {
        "path": str(
            answer_record_path(workspace_root, request).relative_to(workspace_root)
        ),
        "answer_hash": answer_hash,
        "recorded_at": record["recorded_at"],
    }
    atomic_write_json(pending_request_path(workspace_root), request)
    append_event(
        workspace_root,
        "INTERRUPT_RESOLVED",
        run_id=str(request["run_id"]),
        segment=load_state(workspace_root).get("segment"),
        node_id=request.get("node_id"),
        status="answered",
        payload={
            "request_id": request["request_id"],
            "answer_hash": answer_hash,
        },
    )


def load_answer_record(
    workspace_root: Path,
    request: dict[str, Any],
) -> dict[str, Any]:
    ref = request.get("answer_record")
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        raise ValueError("pending request has no answer_record path")
    record = load_json(workspace_root / ref["path"])
    if not isinstance(record, dict):
        raise ValueError("answer record must be an object")
    return record


def answer_decision(answer_record: dict[str, Any]) -> str | None:
    answer = answer_record.get("answer")
    if not isinstance(answer, dict):
        return None
    answers = answer.get("answers")
    if not isinstance(answers, dict):
        return None
    decision = answers.get("decision")
    return decision if isinstance(decision, str) else None


def validate_answer_payload(
    request: dict[str, Any],
    answer: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if answer.get("request_id") != request.get("request_id"):
        errors.append("answer request_id does not match pending request")
    if answer.get("request_snapshot_hash") != request.get("request_snapshot_hash"):
        errors.append("answer request_snapshot_hash is stale")
    if not isinstance(answer.get("answers"), dict):
        errors.append("answer requires answers object")
    return errors


def command_answer(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    try:
        request = load_pending_request(workspace_root)
        if request.get("request_id") != args.request_id:
            raise ValueError("request-id does not match pending request")
        answer = load_json(Path(args.json_file))
        if not isinstance(answer, dict):
            raise ValueError("answer JSON must contain an object")
        errors = validate_answer_payload(request, answer)
        if errors:
            raise ValueError("; ".join(errors))
        record_answer(workspace_root, request, answer)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INVALID_INPUT
    return emit_status(workspace_root, False)


def review_packet_refs(request: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for value in request.get("evidence_refs", []):
        if isinstance(value, str) and ".evidence/review_packets/" in value:
            refs.append(value)
        elif isinstance(value, dict):
            path = value.get("path")
            kind = value.get("kind")
            if isinstance(path, str) and (
                kind == "review_packet" or ".evidence/review_packets/" in path
            ):
                refs.append(path)
    return refs


def resolve_approval_source(
    request: dict[str, Any],
    explicit_source: str | None,
) -> str:
    if explicit_source:
        return explicit_source
    refs = review_packet_refs(request)
    if len(refs) == 1:
        return refs[0]
    raise ValueError(
        "approval-source is required unless pending_request has exactly one "
        "review packet evidence ref"
    )


def command_approve(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    try:
        request = load_pending_request(workspace_root)
        if request.get("request_id") != args.request_id:
            raise ValueError("request-id does not match pending request")
        if request.get("type") != "APPROVE_ACTION":
            raise ValueError("pending request is not APPROVE_ACTION")
        allowed = request.get("allowed_responses", [])
        if args.decision not in allowed:
            raise ValueError("decision is not in allowed_responses")
        approval_source = resolve_approval_source(request, args.approval_source)
        exact_action = request.get("exact_action")
        if isinstance(exact_action, dict):
            expected_source = exact_action.get("approval_source")
            if (
                isinstance(expected_source, str)
                and "<" not in expected_source
                and expected_source != approval_source
            ):
                raise ValueError("approval_source changed from exact_action")
            action_hash = exact_action.get("action_hash")
            if isinstance(action_hash, str) and action_hash != exact_action_hash(
                exact_action
            ):
                raise ValueError("exact_action.action_hash is stale")
        idempotency_key = (
            args.idempotency_key
            or f"{args.request_id}:{args.approved_by}:{args.decision}"
        )
        existing_idempotency = idempotency_record_path(workspace_root, idempotency_key)
        if existing_idempotency.exists():
            existing = load_json(existing_idempotency)
            if not isinstance(existing, dict):
                raise ValueError("idempotency record must be an object")
            answer = existing.get("answer")
            answers = answer.get("answers") if isinstance(answer, dict) else None
            if (
                isinstance(answer, dict)
                and isinstance(answers, dict)
                and answer.get("request_id") == args.request_id
                and answer.get("answered_by") == args.approved_by
                and answers.get("decision") == args.decision
                and answers.get("approval_source") == approval_source
            ):
                return emit_status(workspace_root, args.json)
            raise ValueError("idempotency_key reused with a different answer body")
        approval_execution = approval_execution_for_decision(
            workspace_root,
            request=request,
            decision=args.decision,
            approved_by=args.approved_by,
            approval_source=approval_source,
        )
        answer = {
            "request_id": args.request_id,
            "request_snapshot_hash": request["request_snapshot_hash"],
            "idempotency_key": idempotency_key,
            "answered_by": args.approved_by,
            "answered_at": utc_now(),
            "answers": {
                "decision": args.decision,
                "approval_source": approval_source,
                "approval_execution": approval_execution,
            },
        }
        record_answer(workspace_root, request, answer)
        if args.decision == "approve":
            state = load_state(workspace_root)
            append_event(
                workspace_root,
                "APPROVAL_RECORDED",
                run_id=str(request["run_id"]),
                segment=state.get("segment"),
                node_id=request.get("node_id"),
                status=str(approval_execution["status"]).lower(),
                payload={
                    "request_id": args.request_id,
                    "approval_source": approval_source,
                    "approval_execution": approval_execution,
                },
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        if "approval-source is required" in str(exc):
            return EXIT_MANUAL_ACTION
        return EXIT_INVALID_INPUT
    return emit_status(workspace_root, args.json)


def run_manifest_path(workspace_root: Path, run_id: str) -> Path:
    return supervisor_root(workspace_root) / "runs" / run_id / "run_manifest.json"


def load_run_manifest(workspace_root: Path, run_id: str) -> dict[str, Any]:
    manifest = load_json(run_manifest_path(workspace_root, run_id))
    if not isinstance(manifest, dict):
        raise ValueError("run manifest must be an object")
    return manifest


def answer_payload_answers(answer_record: dict[str, Any]) -> dict[str, Any]:
    answer = answer_record.get("answer")
    if not isinstance(answer, dict):
        return {}
    answers = answer.get("answers")
    return answers if isinstance(answers, dict) else {}


def answer_string(answers: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = answers.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def answer_bool(answers: dict[str, Any], *keys: str) -> bool | None:
    for key in keys:
        value = answers.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip():
            return truthy_policy_value(value)
    return None


def answer_string_list(answers: dict[str, Any], *keys: str) -> list[str] | None:
    for key in keys:
        value = answers.get(key)
        if isinstance(value, list):
            rendered = [str(item).strip() for item in value if str(item).strip()]
            if rendered:
                return rendered
        if isinstance(value, str) and value.strip():
            return [value.strip()]
    return None


def resume_args_from_answer(
    workspace_root: Path,
    *,
    state: dict[str, Any],
    answer_record: dict[str, Any],
    as_json: bool,
) -> argparse.Namespace:
    run_id = str(state["active_run_id"])
    manifest = load_run_manifest(workspace_root, run_id)
    policy = manifest.get("policy")
    policy = policy if isinstance(policy, dict) else {}
    args = argparse.Namespace(
        json=as_json,
        auto=False,
        worker_mode=str(policy.get("worker_mode") or "none"),
        worker_command=(
            policy.get("worker_command")
            if isinstance(policy.get("worker_command"), str)
            and policy.get("worker_command")
            else None
        ),
        codex_home=(
            policy.get("codex_home")
            if isinstance(policy.get("codex_home"), str) and policy.get("codex_home")
            else None
        ),
        allow_external_downloads=bool(policy.get("allow_external_downloads")),
        dataset_source=None,
        dataset_target=None,
        baseline_repo=[],
        baseline_target=None,
    )
    grill_bridge_ref = policy.get("grill_bridge_ref")
    if isinstance(grill_bridge_ref, str) and grill_bridge_ref:
        bridge_path = workspace_root / grill_bridge_ref
        if bridge_path.exists():
            bridge = load_json(bridge_path)
            if isinstance(bridge, dict):
                setattr(args, "_grill_bridge", bridge)
                setattr(args, "_grill_bridge_ref", grill_bridge_ref)

    answers = answer_payload_answers(answer_record)
    args.dataset_source = answer_string(
        answers,
        "dataset_source",
        "dataset_remote",
        "source",
    )
    args.dataset_target = answer_string(
        answers,
        "dataset_target",
        "dataset_root",
        "dataset_path",
        "path",
    )
    if args.dataset_source or args.dataset_target:
        setattr(args, "_answer_overrides_dataset_source", True)
    baseline_repos = answer_string_list(
        answers,
        "baseline_repo",
        "baseline_source",
        "baseline_repos",
    )
    if baseline_repos is not None:
        args.baseline_repo = baseline_repos
        setattr(args, "_answer_overrides_baseline_repo", True)
    args.baseline_target = answer_string(
        answers,
        "baseline_target",
        "baseline_cache",
        "baseline_path",
    )
    allow_downloads = answer_bool(
        answers,
        "allow_external_downloads",
        "external_download_policy",
    )
    decision = answer_string(answers, "decision")
    if decision in {"approve_clone", "approve_download"}:
        allow_downloads = True
    if allow_downloads is not None:
        args.allow_external_downloads = allow_downloads
    return args


def answer_record_ref(workspace_root: Path, request: dict[str, Any]) -> str:
    return answer_record_path(workspace_root, request).relative_to(
        workspace_root
    ).as_posix()


def mark_answered_resume_failed(
    workspace_root: Path,
    *,
    state: dict[str, Any],
    request: dict[str, Any],
    reason: str,
    detail: str,
) -> None:
    state["status"] = "paused"
    state["segment_status"] = reason
    state["pending_request_id"] = request["request_id"]
    state["last_failure"] = {
        "kind": reason,
        "detail": detail,
        "request_id": request["request_id"],
    }
    append_event(
        workspace_root,
        "RUN_RESUME_FAILED",
        run_id=str(state.get("active_run_id")),
        segment=state.get("segment"),
        node_id=request.get("node_id"),
        status="paused",
        payload={
            "request_id": request["request_id"],
            "reason": reason,
            "detail": detail,
        },
    )
    save_state(workspace_root, state)


def resume_supervised_node_request(
    workspace_root: Path,
    *,
    args: argparse.Namespace,
    state: dict[str, Any],
    request: dict[str, Any],
    answer_record: dict[str, Any],
) -> int | None:
    strategy = request.get("resume_strategy")
    if strategy not in {
        DEFAULT_RECOVERY_STRATEGY,
        "manual_recover",
        "rerun_idempotent",
        "resume_with_answer",
    }:
        return None
    segment = state.get("segment")
    node_id = request.get("node_id")
    run_id = state.get("active_run_id")
    if not isinstance(segment, str) or not isinstance(node_id, str):
        return None
    if not isinstance(run_id, str) or not run_id:
        return None

    manifest = load_run_manifest(workspace_root, run_id)
    goal = str(manifest.get("goal") or "")
    resume_args = resume_args_from_answer(
        workspace_root,
        state=state,
        answer_record=answer_record,
        as_json=args.json,
    )
    if resume_args.allow_external_downloads:
        setattr(
            resume_args,
            "_allow_external_downloads_source",
            answer_record_ref(workspace_root, request),
        )
    acquire_lock(workspace_root, run_id)
    try:
        state["status"] = "running"
        state["pending_request_id"] = request["request_id"]
        state["resolved_inputs_ref"] = answer_record_ref(workspace_root, request)
        state["last_failure"] = None
        append_event(
            workspace_root,
            "RUN_RESUMED",
            run_id=run_id,
            segment=segment,
            node_id=node_id,
            status="running",
            payload={
                "request_id": args.request_id,
                "mode": "rerun_answered_node",
            },
        )
        save_state(workspace_root, state)

        if segment == "prepare" and node_id == "prepare_acquisition_plan":
            acquisition_exit = run_prepare_acquisition_plan_gate(
                workspace_root,
                args=resume_args,
                run_id=run_id,
                state=state,
                readiness_ref=f"{SUPERVISOR_DIR}/readiness_preflight.json",
            )
            if acquisition_exit is not None:
                return acquisition_exit
            exit_code = run_supervised_nodes(
                workspace_root,
                args=resume_args,
                run_id=run_id,
                state=state,
                segment="prepare",
                goal=goal,
                node_ids={"prepare_data_prep", "prepare_baseline_repro"},
            )
            if exit_code is not None:
                return exit_code
            return continue_prepare_complete_after_supervised_nodes(
                workspace_root,
                args=resume_args,
                run_id=run_id,
                state=state,
                readiness_ref=f"{SUPERVISOR_DIR}/readiness_preflight.json",
            )

        if segment == "prepare" and node_id in {
            "prepare_data_prep",
            "prepare_baseline_repro",
        }:
            exit_code = run_supervised_nodes(
                workspace_root,
                args=resume_args,
                run_id=run_id,
                state=state,
                segment="prepare",
                goal=goal,
                node_ids={"prepare_data_prep", "prepare_baseline_repro"},
            )
            if exit_code is not None:
                return exit_code
            return continue_prepare_complete_after_supervised_nodes(
                workspace_root,
                args=resume_args,
                run_id=run_id,
                state=state,
                readiness_ref=f"{SUPERVISOR_DIR}/readiness_preflight.json",
            )

        if segment == "build":
            exit_code = run_supervised_nodes(
                workspace_root,
                args=resume_args,
                run_id=run_id,
                state=state,
                segment="build",
                goal=goal,
            )
            if exit_code is not None:
                return exit_code
            state["status"] = "completed"
            state["segment_status"] = "build_ready_for_iterate"
            state["current_node_id"] = None
            state["current_attempt"] = 0
            state["pending_request_id"] = None
            save_state(workspace_root, state)
            pending = load_json_if_exists(pending_request_path(workspace_root), {})
            if isinstance(pending, dict) and pending.get("request_id") == request.get(
                "request_id"
            ):
                pending_request_path(workspace_root).unlink(missing_ok=True)
            append_event(
                workspace_root,
                "RUN_COMPLETED",
                run_id=run_id,
                segment="build",
                status="completed",
                payload={"mode": "build_ready_for_iterate"},
            )
            return emit_status(workspace_root, args.json)

        if segment == "iterate" and node_id == "iterate_delegate_auto_iterate":
            decision = answer_decision(answer_record)
            if decision in {"resume", "recover"}:
                resume_result = run_auto_iterate_command(
                    workspace_root,
                    "resume",
                    [],
                )
                append_event(
                    workspace_root,
                    "AUTO_ITERATE_DELEGATED",
                    run_id=run_id,
                    segment="iterate",
                    node_id="iterate_delegate_auto_iterate",
                    status="resumed",
                    payload={
                        "exit_code": resume_result["exit_code"],
                        "command": resume_result["command"],
                        "decision": decision,
                    },
                )
                exit_code, _status_result = sync_auto_iterate_status(
                    workspace_root,
                    run_id=run_id,
                    state=state,
                    start_result=resume_result,
                )
                pending = load_json_if_exists(pending_request_path(workspace_root), {})
                if (
                    exit_code == EXIT_OK
                    and isinstance(pending, dict)
                    and pending.get("request_id") == request.get("request_id")
                ):
                    pending_request_path(workspace_root).unlink(missing_ok=True)
                return emit_status(workspace_root, args.json, exit_code=exit_code)
            if decision == "stop":
                stop_result = run_auto_iterate_command(workspace_root, "stop", [])
                append_event(
                    workspace_root,
                    "AUTO_ITERATE_DELEGATED",
                    run_id=run_id,
                    segment="iterate",
                    node_id="iterate_delegate_auto_iterate",
                    status="stop_requested",
                    payload={
                        "exit_code": stop_result["exit_code"],
                        "command": stop_result["command"],
                    },
                )
                exit_code, _status_result = sync_auto_iterate_status(
                    workspace_root,
                    run_id=run_id,
                    state=state,
                    start_result=stop_result,
                )
                pending = load_json_if_exists(pending_request_path(workspace_root), {})
                if (
                    exit_code == EXIT_OK
                    and isinstance(pending, dict)
                    and pending.get("request_id") == request.get("request_id")
                ):
                    pending_request_path(workspace_root).unlink(missing_ok=True)
                return emit_status(workspace_root, args.json, exit_code=exit_code)
            if decision == "revise_goal":
                print(
                    "revise_goal requires auto_iterate_ctl override before resume",
                    file=sys.stderr,
                )
                return EXIT_MANUAL_ACTION
            print(
                "answer decision must be resume, recover, stop, or revise_goal",
                file=sys.stderr,
            )
            return EXIT_INVALID_INPUT

        if segment == "release" and node_id == "release_final_exp_matrix":
            release_action = release_action_from_goal(goal)
            if release_action is None:
                request = create_release_action_steer_request(
                    workspace_root,
                    run_id=run_id,
                )
                state["status"] = "paused"
                state["segment_status"] = "release_action_unclear"
                state["pending_request_id"] = request["request_id"]
                save_state(workspace_root, state)
                return emit_status(
                    workspace_root,
                    args.json,
                    exit_code=EXIT_MANUAL_ACTION,
                )
            exit_code = run_supervised_nodes(
                workspace_root,
                args=resume_args,
                run_id=run_id,
                state=state,
                segment="release",
                goal=goal,
                node_ids={"release_final_exp_matrix"},
            )
            if exit_code is not None:
                return exit_code
            return continue_release_after_final_exp(
                workspace_root,
                args=resume_args,
                run_id=run_id,
                state=state,
                release_action=release_action,
            )
    except KeyboardInterrupt:
        mark_answered_resume_failed(
            workspace_root,
            state=state,
            request=request,
            reason="answered_resume_interrupted",
            detail="operator interrupted answered request resume",
        )
        raise
    except Exception as exc:
        mark_answered_resume_failed(
            workspace_root,
            state=state,
            request=request,
            reason="answered_resume_failed",
            detail=str(exc),
        )
        raise
    finally:
        release_lock(workspace_root, run_id)
    return None


def command_resume(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    try:
        state = load_state(workspace_root)
        request = load_pending_request(workspace_root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_NO_ACTIVE_RUN
    if state.get("status") != "paused":
        return EXIT_NO_ACTIVE_RUN
    if request.get("request_id") != args.request_id:
        print("request-id does not match pending request", file=sys.stderr)
        return EXIT_INVALID_INPUT
    if not request.get("answer_record"):
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)
    answer_record = load_answer_record(workspace_root, request)
    supervised_exit = resume_supervised_node_request(
        workspace_root,
        args=args,
        state=state,
        request=request,
        answer_record=answer_record,
    )
    if supervised_exit is not None:
        return supervised_exit
    decision = answer_decision(answer_record)
    segment_status = "v0_resume_recorded"
    resume_status = "completed"
    resume_exit_code = EXIT_OK
    if (
        state.get("segment") == "prepare"
        and request.get("reason")
        in {
            "evaluation_contract_approval_required",
            "prepare_complete_approval_required",
        }
    ):
        if decision == "approve":
            gate_result = run_dynamic_context_gate(
                workspace_root,
                stage="wf5",
                build_id=str(state["active_run_id"]),
                write_review_packet=False,
            )
            gate_record_path = write_gate_rerun_record(
                workspace_root,
                run_id=str(state["active_run_id"]),
                request_id=args.request_id,
                gate_result=gate_result,
            )
            state["resolved_inputs_ref"] = gate_record_path.relative_to(
                workspace_root
            ).as_posix()
            if request.get("reason") == "prepare_complete_approval_required":
                segment_status = "prepare_complete"
            else:
                segment_status = "prepare_hitl_poc"
        elif decision == "revise":
            segment_status = "prepare_revision_requested"
        elif decision == "reject":
            segment_status = "prepare_rejected"
        else:
            print("answer decision must be approve, revise, or reject", file=sys.stderr)
            return EXIT_INVALID_INPUT
    elif (
        state.get("segment") == "change"
        and request.get("reason") == "change_route_uncertain"
    ):
        allowed = request.get("allowed_responses", [])
        if decision not in allowed:
            print(
                "answer decision must select an allowed change route",
                file=sys.stderr,
            )
            return EXIT_INVALID_INPUT
        if decision == "reject":
            segment_status = "change_rejected"
        elif isinstance(decision, str):
            segment_status = route_status(decision)
        state["resolved_inputs_ref"] = str(
            answer_record_path(workspace_root, request).relative_to(workspace_root)
        )
    elif (
        state.get("segment") == "release"
        and request.get("reason") == "release_submission_approval_required"
    ):
        if decision == "approve":
            gate_result = run_dynamic_context_gate(
                workspace_root,
                stage="wf12",
                build_id=str(state["active_run_id"]),
                write_review_packet=False,
            )
            gate_record_path = write_release_gate_rerun_record(
                workspace_root,
                run_id=str(state["active_run_id"]),
                request_id=args.request_id,
                gate_result=gate_result,
            )
            blockers = release_gate_blockers(gate_result)
            state["resolved_inputs_ref"] = gate_record_path.relative_to(
                workspace_root
            ).as_posix()
            if not blockers:
                segment_status = "release_approval_recorded"
            else:
                segment_status = "release_gate_failed_after_approval"
                resume_status = "failed"
                resume_exit_code = EXIT_INVALID_INPUT
                state["last_failure"] = {
                    "kind": "release_gate_failed_after_approval",
                    "gate_record": state["resolved_inputs_ref"],
                    "exit_code": gate_result["exit_code"],
                    "blockers": blockers,
                }
        elif decision == "revise":
            segment_status = "release_revision_requested"
        elif decision == "reject":
            segment_status = "release_rejected"
        else:
            print("answer decision must be approve, revise, or reject", file=sys.stderr)
            return EXIT_INVALID_INPUT
    append_event(
        workspace_root,
        "RUN_RESUMED",
        run_id=state.get("active_run_id"),
        segment=state.get("segment"),
        status=resume_status,
        payload={"request_id": args.request_id, "mode": segment_status},
    )
    state["status"] = resume_status
    state["segment_status"] = segment_status
    state["pending_request_id"] = None
    state["current_node_id"] = None
    save_state(workspace_root, state)
    pending_request_path(workspace_root).unlink(missing_ok=True)
    return emit_status(workspace_root, args.json, exit_code=resume_exit_code)


def repair_stale_running_answered_request(
    workspace_root: Path,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    if state.get("status") != "running" or lock_path(workspace_root).exists():
        return None
    answer_ref = state.get("resolved_inputs_ref")
    node_id = state.get("current_node_id")
    run_id = state.get("active_run_id")
    segment = state.get("segment")
    if not all(isinstance(value, str) and value for value in [answer_ref, node_id]):
        return None
    if not isinstance(run_id, str) or not isinstance(segment, str):
        return None
    answer_path = workspace_root / str(answer_ref)
    if not answer_path.exists():
        return None
    answer_record = load_json(answer_path)
    if not isinstance(answer_record, dict) or not isinstance(
        answer_record.get("answer"),
        dict,
    ):
        return None
    reason = str(state.get("segment_status") or "answered_resume_interrupted")
    request = create_node_pending_request(
        workspace_root,
        run_id=run_id,
        segment=segment,
        node_id=str(node_id),
        request_type="ASK_INPUT",
        reason=reason,
        question=(
            "Resume was interrupted after an answer was recorded. Reuse the "
            "recorded answer, revise it, or reject this recovery."
        ),
        allowed_responses=["reuse_answer", "revise", "reject"],
        gate_status_refs=[str(answer_ref)],
        resume_strategy=DEFAULT_RECOVERY_STRATEGY,
    )
    answer_hash = answer_record.get("answer_hash")
    if not isinstance(answer_hash, str):
        answer_hash = sha256_json(answer_record["answer"])
    request["answer_record"] = {
        "path": str(answer_ref),
        "answer_hash": answer_hash,
        "recorded_at": answer_record.get("recorded_at") or utc_now(),
    }
    atomic_write_json(pending_request_path(workspace_root), request)
    state["status"] = "paused"
    state["pending_request_id"] = request["request_id"]
    state["last_failure"] = {
        "kind": "stale_running_answered_request_repaired",
        "answer_ref": str(answer_ref),
        "request_id": request["request_id"],
    }
    append_event(
        workspace_root,
        "RECOVERY_REPAIRED_STATE",
        run_id=run_id,
        segment=segment,
        node_id=str(node_id),
        status="paused",
        payload={
            "request_id": request["request_id"],
            "answer_ref": str(answer_ref),
        },
    )
    save_state(workspace_root, state)
    return request


def command_recover(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    if not state_path(workspace_root).exists():
        return EXIT_NO_ACTIVE_RUN
    state = load_state(workspace_root)
    if args.repair_stale_running:
        repair_stale_running_answered_request(workspace_root, state)
        state = load_state(workspace_root)
    errors = validate_state_invariants(state, workspace_root)
    event_seq = latest_event_seq(workspace_root)
    pending_request_id = None
    pending_answered = False
    pending_errors: list[str] = []
    if pending_request_path(workspace_root).exists():
        try:
            request = load_pending_request(workspace_root)
            pending_request_id = request.get("request_id")
            pending_answered = bool(request.get("answer_record"))
        except ValueError as exc:
            pending_errors.append(str(exc))
    recommended_action = "status_only"
    active_worker = classify_worker_state(workspace_root, state=state)
    if errors or pending_errors:
        recommended_action = "manual_recover"
    elif state.get("status") == "paused" and pending_request_id:
        recommended_action = (
            "resume_answered_pending_request"
            if pending_answered
            else "answer_pending_request"
        )
    elif (
        state.get("status") == "running"
        and active_worker is not None
        and active_worker.get("recommended_action") != "wait"
    ):
        recommended_action = str(active_worker.get("recommended_action"))
    if (
        args.auto_resume_answered
        and recommended_action == "resume_answered_pending_request"
    ):
        return command_resume(
            argparse.Namespace(
                workspace_root=str(workspace_root),
                request_id=pending_request_id,
                json=args.json,
            )
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id or state.get("active_run_id"),
        "state_valid": not errors,
        "errors": [*errors, *pending_errors],
        "latest_event_seq": event_seq,
        "state_last_event_seq": state.get("last_event_seq"),
        "pending_request_id": pending_request_id,
        "pending_answered": pending_answered,
        "recommended_action": recommended_action,
    }
    if active_worker is not None:
        payload["active_worker"] = active_worker
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload["recommended_action"])
    return EXIT_MANUAL_ACTION if errors or pending_errors else EXIT_OK


def command_tail(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    if not events_path(workspace_root).exists():
        return EXIT_NO_STATE
    lines = events_path(workspace_root).read_text(encoding="utf-8").splitlines()
    selected = lines[-args.lines :]
    if args.jsonl:
        for line in selected:
            print(line)
    else:
        for line in selected:
            event = json.loads(line)
            print(
                f"{event.get('seq')} {event.get('event')} "
                f"{event.get('status')} {event.get('run_id')}"
            )
    return EXIT_OK


def command_worker_event(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    snapshot = append_worker_event(
        workspace_root,
        run_id=args.run_id,
        node_id=args.node_id,
        phase=args.phase,
        message=args.message,
        source="worker",
        command=args.command_text,
        result=args.result,
        artifacts=args.artifact or [],
    )
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print(f"{snapshot['phase']} {snapshot['node_id']}: {snapshot['last_message']}")
    return EXIT_OK


def command_worker_status(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    if args.run_id and args.node_id:
        state = {
            "active_run_id": args.run_id,
            "current_node_id": args.node_id,
            "status": "running",
            "segment": None,
        }
    else:
        if not state_path(workspace_root).exists():
            return EXIT_NO_ACTIVE_RUN
        state = load_state(workspace_root)
    payload = classify_worker_state(workspace_root, state=state)
    if payload is None:
        return EXIT_NO_ACTIVE_RUN
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"{payload.get('telemetry_state')} "
            f"node={payload.get('node_id')} "
            f"action={payload.get('recommended_action')}"
        )
    return EXIT_OK


def validate_worker_result(
    workspace_root: Path,
    result: dict[str, Any],
) -> list[str]:
    errors = validate_schema(
        workspace_root,
        result,
        "workflow_supervisor_worker_result.schema.json",
        "worker_result",
    )
    status = result.get("status")
    if status not in VALID_WORKER_STATUSES:
        errors.append(f"status must be one of {sorted(VALID_WORKER_STATUSES)}")
    gate_ledger = result.get("gate_ledger")
    if not isinstance(gate_ledger, list):
        errors.append("gate_ledger must be a list")
    else:
        for index, gate in enumerate(gate_ledger):
            if not isinstance(gate, dict):
                errors.append(f"gate_ledger[{index}] must be an object")
                continue
            if gate.get("result") not in VALID_GATE_RESULTS:
                errors.append(
                    f"gate_ledger[{index}].result must be PASS, FAIL, or NOT_RUN"
                )
            for field in ("command", "reason", "artifacts"):
                if field not in gate:
                    errors.append(f"gate_ledger[{index}] missing {field}")
    if status == "interrupt_requested" and not result.get("interrupt_request"):
        errors.append("interrupt_requested requires interrupt_request")
    if status == "success" and result.get("contract_violations"):
        errors.append("success result must not include contract_violations")
    direct_question_texts: list[str] = []
    summary = result.get("summary")
    if isinstance(summary, str):
        direct_question_texts.append(summary)
    warnings = result.get("worker_warnings")
    if isinstance(warnings, list):
        direct_question_texts.extend(
            warning for warning in warnings if isinstance(warning, str)
        )
    violations = result.get("contract_violations")
    if isinstance(violations, list):
        direct_question_texts.extend(
            violation for violation in violations if isinstance(violation, str)
        )
    lowered = "\n".join(direct_question_texts).lower()
    if any(marker in lowered for marker in DIRECT_USER_QUESTION_MARKERS):
        errors.append("worker_direct_user_question")
    for path in result.get("observed_writes", []):
        if isinstance(path, str) and path.startswith(FORBIDDEN_WORKER_WRITE_PREFIXES):
            errors.append(f"observed_writes contains tool-owned path: {path}")
    return errors


def resolve_runtime_path(workspace_root: Path, value: str, run_id: str) -> Path:
    resolved = value.replace("<run_id>", run_id)
    path = Path(resolved)
    if path.is_absolute():
        return path
    return workspace_root / path


def relpath_or_abs(path: Path, workspace_root: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def gate_record(
    condition: dict[str, Any],
    *,
    result: str,
    reason: str,
    artifacts: list[str] | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return {
        "condition": condition,
        "command": command or f"postcondition:{condition.get('type', 'unknown')}",
        "result": result,
        "reason": reason,
        "artifacts": artifacts or [],
    }


def worker_gate_for_fragments(
    worker_result: dict[str, Any],
    fragments: list[str],
) -> dict[str, Any] | None:
    for gate in worker_result.get("gate_ledger", []):
        if not isinstance(gate, dict):
            continue
        command = gate.get("command")
        if not isinstance(command, str):
            continue
        if all(fragment in command for fragment in fragments):
            return gate
    return None


def worker_gate_condition(
    condition: dict[str, Any],
    worker_result: dict[str, Any],
    fragments: list[str],
    *,
    description: str,
) -> dict[str, Any]:
    gate = worker_gate_for_fragments(worker_result, fragments)
    if gate is None:
        return gate_record(
            condition,
            result="NOT_RUN",
            reason=f"{description} was not reported in worker gate ledger",
            command=" ".join(fragments),
        )
    result = str(gate.get("result"))
    if result not in VALID_GATE_RESULTS:
        result = "FAIL"
    artifacts = gate.get("artifacts", [])
    return gate_record(
        condition,
        result=result,
        reason=str(gate.get("reason") or description),
        artifacts=artifacts if isinstance(artifacts, list) else [],
        command=str(gate.get("command") or " ".join(fragments)),
    )


def _strip_markdown_code(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1].strip()
    return stripped


def roadmap_commit_plan(
    workspace_root: Path,
    roadmap_path: str,
) -> list[dict[str, str]]:
    path = workspace_root / roadmap_path
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    in_commit_plan = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if in_commit_plan and rows:
                break
            in_commit_plan = "commit_plan" in line.lower()
            continue
        if not in_commit_plan or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        first = _strip_markdown_code(cells[0])
        if not first or first == "commit_slice" or set(first) <= {"-"}:
            continue
        if first.lower().startswith(":"):
            continue
        rows.append(
            {
                "slice_id": first,
                "message": _strip_markdown_code(cells[3]),
            }
        )
    return rows


def git_log_since(
    workspace_root: Path,
    base_commit: str,
) -> tuple[list[dict[str, str]], str | None]:
    if not (workspace_root / ".git").exists():
        return [], "git repository is missing"
    if not base_commit:
        return [], "run manifest does not record base_git_commit"
    proc = subprocess.run(
        ["git", "log", "--format=%H%x1f%s", f"{base_commit}..HEAD"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        reason = proc.stderr.strip() or proc.stdout.strip() or "git log failed"
        return [], reason
    commits: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        if "\x1f" not in line:
            continue
        commit_hash, subject = line.split("\x1f", 1)
        commits.append({"hash": commit_hash.strip(), "subject": subject.strip()})
    return commits, None


def evaluate_sliced_commits_recorded(
    workspace_root: Path,
    condition: dict[str, Any],
    *,
    run_id: str,
) -> dict[str, Any]:
    roadmap_path = condition.get("roadmap_path", "docs/Implementation_Roadmap.md")
    if not isinstance(roadmap_path, str):
        return gate_record(
            condition,
            result="FAIL",
            reason="sliced_commits_recorded requires string roadmap_path",
        )
    expected = roadmap_commit_plan(workspace_root, roadmap_path)
    if not expected:
        return gate_record(
            condition,
            result="FAIL",
            reason=f"no commit_plan rows found in {roadmap_path}",
            artifacts=[roadmap_path],
        )
    try:
        manifest = load_run_manifest(workspace_root, run_id)
    except ValueError as exc:
        return gate_record(
            condition,
            result="FAIL",
            reason=str(exc),
        )
    base_commit = manifest.get("base_git_commit")
    commits, error = git_log_since(
        workspace_root,
        str(base_commit) if isinstance(base_commit, str) else "",
    )
    if error:
        return gate_record(
            condition,
            result="FAIL",
            reason=error,
        )
    matched: dict[str, dict[str, str]] = {}
    for row in expected:
        slice_id = row["slice_id"]
        expected_message = row["message"]
        for commit in commits:
            subject = commit["subject"]
            if slice_id in subject or (
                expected_message and subject == expected_message
            ):
                matched[slice_id] = commit
                break
    missing = [row["slice_id"] for row in expected if row["slice_id"] not in matched]
    duplicate_hashes = {
        commit["hash"]
        for commit in matched.values()
        if list(item["hash"] for item in matched.values()).count(commit["hash"]) > 1
    }
    artifacts = [
        f"{commit['hash']} {commit['subject']}"
        for commit in matched.values()
    ]
    if missing:
        return gate_record(
            condition,
            result="FAIL",
            reason="missing semantic commits for commit slices: " + ", ".join(missing),
            artifacts=[roadmap_path, *artifacts],
            command=f"sliced semantic commits from {roadmap_path}",
        )
    if duplicate_hashes:
        return gate_record(
            condition,
            result="FAIL",
            reason=(
                "multiple commit_plan slices resolved to the same commit: "
                + ", ".join(sorted(duplicate_hashes))
            ),
            artifacts=[roadmap_path, *artifacts],
            command=f"sliced semantic commits from {roadmap_path}",
        )
    return gate_record(
        condition,
        result="PASS",
        reason="each roadmap commit_plan slice has a distinct semantic commit",
        artifacts=[roadmap_path, *artifacts],
        command=f"sliced semantic commits from {roadmap_path}",
    )


def evaluate_git_worktree_clean(
    workspace_root: Path,
    condition: dict[str, Any],
) -> dict[str, Any]:
    if not (workspace_root / ".git").exists():
        return gate_record(
            condition,
            result="FAIL",
            reason="git repository is missing",
        )
    ignore_patterns = condition.get(
        "ignore_patterns",
        list(GIT_WORKTREE_CLEAN_IGNORE_PREFIXES),
    )
    if not isinstance(ignore_patterns, list) or not all(
        isinstance(pattern, str) for pattern in ignore_patterns
    ):
        return gate_record(
            condition,
            result="FAIL",
            reason="git_worktree_clean requires string ignore_patterns",
        )
    dirty = [
        path
        for path in git_status_paths(workspace_root)
        if not any(path.startswith(pattern) for pattern in ignore_patterns)
    ]
    return gate_record(
        condition,
        result="PASS" if not dirty else "FAIL",
        reason=(
            "non-tool-owned git worktree is clean"
            if not dirty
            else "uncommitted non-tool-owned paths: " + ", ".join(dirty)
        ),
        artifacts=dirty,
        command="git status --porcelain",
    )


def evaluate_condition(
    workspace_root: Path,
    condition: dict[str, Any],
    *,
    run_id: str,
    worker_result: dict[str, Any],
) -> dict[str, Any]:
    condition_type = condition.get("type")
    if condition_type == "artifact_exists":
        raw_path = condition.get("path")
        if not isinstance(raw_path, str):
            return gate_record(
                condition,
                result="FAIL",
                reason="artifact_exists requires path",
            )
        path = resolve_runtime_path(workspace_root, raw_path, run_id)
        artifact = relpath_or_abs(path, workspace_root)
        if path.exists():
            return gate_record(
                condition,
                result="PASS",
                reason="required artifact exists",
                artifacts=[artifact],
            )
        return gate_record(
            condition,
            result="FAIL",
            reason="required artifact is missing",
            artifacts=[artifact],
        )
    if condition_type == "artifact_matches_schema":
        raw_path = condition.get("path")
        raw_schema = condition.get("schema")
        if not isinstance(raw_path, str) or not isinstance(raw_schema, str):
            return gate_record(
                condition,
                result="FAIL",
                reason="artifact_matches_schema requires path and schema",
            )
        path = resolve_runtime_path(workspace_root, raw_path, run_id)
        artifact = relpath_or_abs(path, workspace_root)
        if not path.exists():
            return gate_record(
                condition,
                result="FAIL",
                reason="schema artifact is missing",
                artifacts=[artifact],
            )
        try:
            data = load_json(path)
        except ValueError as exc:
            return gate_record(
                condition,
                result="FAIL",
                reason=str(exc),
                artifacts=[artifact],
            )
        schema_name = raw_schema.removeprefix("schemas/")
        errors = validate_schema(workspace_root, data, schema_name, artifact)
        return gate_record(
            condition,
            result="PASS" if not errors else "FAIL",
            reason="schema validation passed" if not errors else "; ".join(errors),
            artifacts=[artifact, raw_schema],
        )
    if condition_type == "no_forbidden_writes":
        patterns = condition.get("patterns", [])
        if not isinstance(patterns, list) or not all(
            isinstance(pattern, str) for pattern in patterns
        ):
            return gate_record(
                condition,
                result="FAIL",
                reason="no_forbidden_writes requires string patterns",
            )
        observed = [
            path
            for path in worker_result.get("observed_writes", [])
            if isinstance(path, str)
        ]
        blocked = [
            path
            for path in observed
            if any(path.startswith(pattern) for pattern in patterns)
        ]
        return gate_record(
            condition,
            result="PASS" if not blocked else "FAIL",
            reason=(
                "worker writes stayed within allowed ownership"
                if not blocked
                else f"worker wrote forbidden paths: {', '.join(blocked)}"
            ),
            artifacts=blocked,
        )
    if condition_type == "review_packet_exists":
        stage = condition.get("stage")
        if not isinstance(stage, str):
            return gate_record(
                condition,
                result="FAIL",
                reason="review_packet_exists requires stage",
            )
        packets = sorted(
            (workspace_root / ".evidence" / "review_packets" / stage).glob(
                "*/review_packet.md"
            )
        )
        return gate_record(
            condition,
            result="PASS" if packets else "FAIL",
            reason=(
                "review packet exists"
                if packets
                else "review packet is missing"
            ),
            artifacts=[relpath_or_abs(path, workspace_root) for path in packets],
        )
    if condition_type == "dynamic_context_gate_passes":
        stage = condition.get("stage")
        if not isinstance(stage, str):
            return gate_record(
                condition,
                result="FAIL",
                reason="dynamic_context_gate_passes requires stage",
            )
        return worker_gate_condition(
            condition,
            worker_result,
            ["check_dynamic_context.py", f"--stage {stage}"],
            description=f"dynamic-context gate for {stage}",
        )
    if condition_type == "docchain_gate_passes":
        doc_path = condition.get("doc_path")
        if not isinstance(doc_path, str):
            return gate_record(
                condition,
                result="FAIL",
                reason="docchain_gate_passes requires doc_path",
            )
        return worker_gate_condition(
            condition,
            worker_result,
            ["compile_doc.py", doc_path],
            description=f"docchain gate for {doc_path}",
        )
    if condition_type == "command_passes":
        command = condition.get("command")
        if not isinstance(command, str):
            return gate_record(
                condition,
                result="FAIL",
                reason="command_passes requires command",
            )
        return worker_gate_condition(
            condition,
            worker_result,
            [command],
            description=f"command gate for {command}",
        )
    if condition_type == "sliced_commits_recorded":
        return evaluate_sliced_commits_recorded(
            workspace_root,
            condition,
            run_id=run_id,
        )
    if condition_type == "git_worktree_clean":
        return evaluate_git_worktree_clean(workspace_root, condition)
    if condition_type == "auto_iterate_status":
        allowed = condition.get("allowed_statuses", [])
        if not isinstance(allowed, list) or not all(
            isinstance(status, str) for status in allowed
        ):
            return gate_record(
                condition,
                result="FAIL",
                reason="auto_iterate_status requires allowed_statuses",
            )
        state_file = workspace_root / ".auto_iterate" / "state.json"
        if not state_file.exists():
            return gate_record(
                condition,
                result="FAIL",
                reason="auto-iterate state is missing",
                artifacts=[".auto_iterate/state.json"],
            )
        state = load_json(state_file)
        status = state.get("status") if isinstance(state, dict) else None
        return gate_record(
            condition,
            result="PASS" if status in allowed else "FAIL",
            reason=f"auto-iterate status is {status}",
            artifacts=[".auto_iterate/state.json"],
        )
    if condition_type == "approval_recorded":
        return worker_gate_condition(
            condition,
            worker_result,
            ["approve_contract.py"],
            description="approval evidence gate",
        )
    return gate_record(
        condition,
        result="FAIL",
        reason=f"unsupported postcondition type: {condition_type}",
    )


def node_by_id(registry: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in registry.get("nodes", []):
        if isinstance(node, dict) and node.get("node_id") == node_id:
            return node
    raise ValueError(f"unknown node_id: {node_id}")


def evaluate_node_postconditions(
    workspace_root: Path,
    node: dict[str, Any],
    *,
    run_id: str,
    worker_result: dict[str, Any],
) -> dict[str, Any]:
    gate_ledger = [
        evaluate_condition(
            workspace_root,
            condition,
            run_id=run_id,
            worker_result=worker_result,
        )
        for condition in node.get("postconditions", [])
        if isinstance(condition, dict)
    ]
    failed = [gate for gate in gate_ledger if gate["result"] != "PASS"]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "node_id": node["node_id"],
        "ok": not failed,
        "gate_ledger": gate_ledger,
        "failed_checks": failed,
    }


def postcondition_record_path(
    workspace_root: Path,
    *,
    run_id: str,
    node_id: str,
) -> Path:
    return (
        supervisor_root(workspace_root)
        / "runs"
        / run_id
        / "gate_results"
        / f"{node_id}.postconditions.json"
    )


def load_node_registry(workspace_root: Path) -> dict[str, Any]:
    data = load_json(config_path(workspace_root))
    if not isinstance(data, dict):
        raise ValueError("node registry must be an object")
    return data


def validate_node_registry(
    workspace_root: Path,
    registry: dict[str, Any],
) -> list[str]:
    errors = validate_schema(
        workspace_root,
        registry,
        "workflow_supervisor_nodes.schema.json",
        "node_registry",
    )
    seen: set[str] = set()
    for index, node in enumerate(registry.get("nodes", [])):
        if not isinstance(node, dict):
            continue
        label = f"nodes[{index}]"
        node_id = node.get("node_id")
        if isinstance(node_id, str):
            if node_id in seen:
                errors.append(f"{label}: duplicate node_id {node_id}")
            seen.add(node_id)
        postconditions = node.get("postconditions", [])
        run_when = str(node.get("run_when") or "always")
        if run_when not in VALID_NODE_RUN_WHEN:
            errors.append(
                f"{label}: run_when must be one of {sorted(VALID_NODE_RUN_WHEN)}"
            )
        if node.get("auto_allowed") is True and not postconditions:
            errors.append(f"{label}: auto_allowed nodes require postconditions")
        if node.get("auto_allowed") is True and not node.get("resume_strategy"):
            errors.append(f"{label}: auto_allowed nodes require resume_strategy")
        automation_policy = node.get("automation_policy")
        if automation_policy is not None:
            if not isinstance(automation_policy, dict):
                errors.append(f"{label}: automation_policy must be an object")
            else:
                for key, value in automation_policy.items():
                    if key == "profile":
                        if not isinstance(value, str) or not value:
                            errors.append(
                                f"{label}: automation_policy.profile must be a string"
                            )
                    elif key in AUTOMATION_POLICY_INT_FIELDS:
                        if not isinstance(value, int) or value <= 0:
                            errors.append(
                                f"{label}: automation_policy.{key} must be "
                                "a positive integer"
                            )
                    else:
                        errors.append(
                            f"{label}: unknown automation_policy field {key}"
                        )
        for field in ("preconditions", "postconditions"):
            values = node.get(field, [])
            if not isinstance(values, list):
                continue
            for cond_index, condition in enumerate(values):
                if not isinstance(condition, dict):
                    continue
                cond_type = condition.get("type")
                if cond_type not in VALID_CONDITION_TYPES:
                    errors.append(
                        f"{label}.{field}[{cond_index}]: unknown type {cond_type}"
                    )
        for pattern in node.get("allowed_worker_write_patterns", []):
            if isinstance(pattern, str) and pattern.startswith(
                FORBIDDEN_WORKER_WRITE_PREFIXES
            ):
                errors.append(
                    f"{label}: allowed_worker_write_patterns cannot include "
                    f"tool-owned path {pattern}"
                )
    return errors


def command_validate_worker_result(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    try:
        result = load_json(Path(args.result))
        if not isinstance(result, dict):
            raise ValueError("worker result must be an object")
        errors = validate_worker_result(workspace_root, result)
    except ValueError as exc:
        errors = [str(exc)]
    if errors:
        if args.json:
            print(json.dumps({"ok": False, "errors": errors}, indent=2))
        else:
            for error in errors:
                print(error)
        return EXIT_INVALID_INPUT
    if args.json:
        print(json.dumps({"ok": True, "errors": []}, indent=2))
    else:
        print("PASS")
    return EXIT_OK


def command_validate_nodes(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    try:
        registry = load_node_registry(workspace_root)
        errors = validate_node_registry(workspace_root, registry)
    except ValueError as exc:
        errors = [str(exc)]
    if errors:
        if args.json:
            print(json.dumps({"ok": False, "errors": errors}, indent=2))
        else:
            for error in errors:
                print(error)
        return EXIT_INVALID_INPUT
    if args.json:
        print(json.dumps({"ok": True, "errors": []}, indent=2))
    else:
        print("PASS")
    return EXIT_OK


def command_validate_postconditions(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    try:
        registry = load_node_registry(workspace_root)
        node = node_by_id(registry, args.node_id)
        worker_result: dict[str, Any] = {
            "gate_ledger": [],
            "observed_writes": [],
        }
        if args.worker_result:
            loaded = load_json(Path(args.worker_result))
            if not isinstance(loaded, dict):
                raise ValueError("worker result must be an object")
            errors = validate_worker_result(workspace_root, loaded)
            if loaded.get("run_id") != args.run_id:
                errors.append("worker_result.run_id does not match --run-id")
            if loaded.get("node_id") != args.node_id:
                errors.append("worker_result.node_id does not match --node-id")
            if errors:
                raise ValueError("; ".join(errors))
            worker_result = loaded
        result = evaluate_node_postconditions(
            workspace_root,
            node,
            run_id=args.run_id,
            worker_result=worker_result,
        )
        if args.record:
            path = postcondition_record_path(
                workspace_root,
                run_id=args.run_id,
                node_id=args.node_id,
            )
            atomic_write_json(path, result)
            result["record_path"] = path.relative_to(workspace_root).as_posix()
    except ValueError as exc:
        if args.json:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        else:
            print(str(exc), file=sys.stderr)
        return EXIT_INVALID_INPUT
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for gate in result["gate_ledger"]:
            print(f"{gate['result']} {gate['command']}: {gate['reason']}")
    return EXIT_OK if result["ok"] else EXIT_INVALID_INPUT


def command_monitor_iterate(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    try:
        status_result = auto_iterate_status(workspace_root)
        payload: dict[str, Any] = {
            "ok": True,
            "auto_iterate": status_result.get("stdout"),
            "supervisor_updated": False,
        }
        exit_code = EXIT_OK
        if state_path(workspace_root).exists():
            state = load_state(workspace_root)
            if state.get("segment") == "iterate" and state.get("active_run_id"):
                run_id = str(state["active_run_id"])
                if state.get("status") == "completed":
                    state["status"] = "running"
                    state["current_node_id"] = "iterate_delegate_auto_iterate"
                    acquire_lock(workspace_root, run_id)
                    try:
                        exit_code, status_result = sync_auto_iterate_status(
                            workspace_root,
                            run_id=run_id,
                            state=state,
                            start_result=None,
                        )
                    finally:
                        release_lock(workspace_root, run_id)
                else:
                    exit_code, status_result = sync_auto_iterate_status(
                        workspace_root,
                        run_id=run_id,
                        state=state,
                        start_result=None,
                    )
                payload["auto_iterate"] = status_result.get("stdout")
                payload["supervisor_updated"] = True
                payload["supervisor"] = status_payload(workspace_root)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        else:
            print(str(exc), file=sys.stderr)
        return EXIT_INVALID_INPUT
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        auto = payload.get("auto_iterate")
        if isinstance(auto, dict):
            print(f"{auto.get('status')} halt={auto.get('halt_reason')}")
        else:
            print("unknown")
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Control the Harness workflow supervisor runtime."
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Repository root or subdirectory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--segment", required=True, choices=sorted(VALID_SEGMENTS))
    start.add_argument("--goal")
    start.add_argument("--goal-file")
    start.add_argument("--dry-run", action="store_true")
    start.add_argument("--complete", action="store_true")
    start.add_argument("--auto", action="store_true")
    start.add_argument(
        "--worker-mode",
        choices=["none", "codex"],
        default="none",
    )
    start.add_argument(
        "--worker-command",
        help=(
            "Command template that writes worker result JSON. Available "
            "fields: {workspace_root}, {run_id}, {node_id}, {skill}, "
            "{result_path}, {prompt_path}."
        ),
    )
    start.add_argument("--codex-home")
    start.add_argument("--allow-external-downloads", action="store_true")
    start.add_argument("--dataset-source")
    start.add_argument("--dataset-target")
    start.add_argument("--baseline-repo", action="append")
    start.add_argument("--baseline-target")
    start.add_argument("--auto-goal", default="docs/auto_iterate_goal.md")
    start.add_argument("--auto-config")
    start.add_argument("--auto-dry-run", action="store_true")
    start.add_argument("--max-rounds", type=int)
    start.add_argument("--skip-dynamic-preflight", action="store_true")
    start.add_argument("--skip-dynamic-preflight-reason")
    start.add_argument("--allow-draft-contract", action="store_true")
    start.add_argument("--allow-review-required", action="store_true")
    start.add_argument("--json", action="store_true")
    start.set_defaults(func=command_start)

    status = subparsers.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    pause = subparsers.add_parser("pause")
    pause.add_argument("--reason", required=True)
    pause.add_argument("--json", action="store_true")
    pause.set_defaults(func=lambda args: mutate_state_status(args, "paused"))

    stop = subparsers.add_parser("stop")
    stop.add_argument("--reason", required=True)
    stop.add_argument("--json", action="store_true")
    stop.set_defaults(func=lambda args: mutate_state_status(args, "stopped"))

    resume = subparsers.add_parser("resume")
    resume.add_argument("--request-id", required=True)
    resume.add_argument("--json", action="store_true")
    resume.set_defaults(func=command_resume)

    answer = subparsers.add_parser("answer")
    answer.add_argument("--request-id", required=True)
    answer.add_argument("--json", dest="json_file", required=True)
    answer.set_defaults(func=command_answer)

    approve = subparsers.add_parser("approve")
    approve.add_argument("--request-id", required=True)
    approve.add_argument(
        "--decision",
        required=True,
        choices=["approve", "revise", "reject"],
    )
    approve.add_argument("--approved-by", required=True)
    approve.add_argument("--approval-source")
    approve.add_argument("--idempotency-key")
    approve.add_argument("--json", action="store_true")
    approve.set_defaults(func=command_approve)

    recover = subparsers.add_parser("recover")
    recover.add_argument("--run-id")
    recover.add_argument("--auto-resume-answered", action="store_true")
    recover.add_argument("--repair-stale-running", action="store_true")
    recover.add_argument("--json", action="store_true")
    recover.set_defaults(func=command_recover)

    tail = subparsers.add_parser("tail")
    tail.add_argument("--jsonl", action="store_true")
    tail.add_argument("--lines", type=int, default=30)
    tail.set_defaults(func=command_tail)

    worker_event = subparsers.add_parser("worker-event")
    worker_event.add_argument("--run-id", required=True)
    worker_event.add_argument("--node-id", required=True)
    worker_event.add_argument(
        "--phase",
        required=True,
        choices=sorted(VALID_WORKER_EVENT_PHASES),
    )
    worker_event.add_argument("--message", required=True)
    worker_event.add_argument("--command", dest="command_text")
    worker_event.add_argument("--result", choices=sorted(VALID_GATE_RESULTS))
    worker_event.add_argument("--artifact", action="append")
    worker_event.add_argument("--json", action="store_true")
    worker_event.set_defaults(func=command_worker_event)

    worker_status = subparsers.add_parser("worker-status")
    worker_status.add_argument("--run-id")
    worker_status.add_argument("--node-id")
    worker_status.add_argument("--json", action="store_true")
    worker_status.set_defaults(func=command_worker_status)

    worker = subparsers.add_parser("validate-worker-result")
    worker.add_argument("--result", required=True)
    worker.add_argument("--json", action="store_true")
    worker.set_defaults(func=command_validate_worker_result)

    nodes = subparsers.add_parser("validate-nodes")
    nodes.add_argument("--json", action="store_true")
    nodes.set_defaults(func=command_validate_nodes)

    postconditions = subparsers.add_parser("validate-postconditions")
    postconditions.add_argument("--node-id", required=True)
    postconditions.add_argument("--run-id", required=True)
    postconditions.add_argument("--worker-result")
    postconditions.add_argument("--record", action="store_true")
    postconditions.add_argument("--json", action="store_true")
    postconditions.set_defaults(func=command_validate_postconditions)

    monitor_iterate = subparsers.add_parser("monitor-iterate")
    monitor_iterate.add_argument("--json", action="store_true")
    monitor_iterate.set_defaults(func=command_monitor_iterate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INVALID_INPUT
    except Exception as exc:
        print(f"fatal workflow supervisor error: {exc}", file=sys.stderr)
        return EXIT_FATAL


if __name__ == "__main__":
    raise SystemExit(main())
