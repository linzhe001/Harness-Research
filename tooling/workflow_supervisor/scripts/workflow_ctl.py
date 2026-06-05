#!/usr/bin/env python3
"""Lightweight Harness workflow supervisor control CLI.

This v0 controller owns only ``.workflow_supervisor/**``. It records typed
state, events, pending human requests, and validation results, but it does not
invoke Stage Skills or mark canonical workflow stages complete.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
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
    "review_packet_exists",
    "approval_recorded",
    "auto_iterate_status",
    "no_forbidden_writes",
}
FORBIDDEN_WORKER_WRITE_PREFIXES = (
    ".evidence/",
    ".auto_iterate/",
    ".workflow_supervisor/",
    "docs/_views/",
    "docs/_site/",
)
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


def acquire_lock(workspace_root: Path, run_id: str) -> None:
    path = lock_path(workspace_root)
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
            "max_llm_calls": 0,
            "max_node_attempts": 1,
            "pause_on_gate_fail": True,
            "allow_external_downloads": False,
        },
    }


def new_run_id() -> str:
    return "sup_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def new_request_id() -> str:
    return "req_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


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
        "inputs": [],
    }


def rejected_readiness_preflight(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": utc_now(),
        "source": "prepare_preflight",
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
) -> list[str]:
    errors: list[str] = []
    for index, item in enumerate(readiness.get("inputs", [])):
        if not isinstance(item, dict) or item.get("kind") != "path":
            continue
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
        else:
            item["verification_status"] = "rejected"
            errors.append(
                f"readiness.inputs[{index}].value path does not exist: {value}"
            )
    readiness["updated_at"] = utc_now()
    return errors


def run_prepare_readiness_preflight(
    workspace_root: Path,
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
        readiness = copy.deepcopy(loaded)
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

    errors = verify_readiness_inputs(workspace_root, readiness)
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
                "docs/Execution_Readiness_Packet.md",
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
        "reason": "evaluation_contract_approval_required",
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
            "prepare_hitl_poc does not unlock build, iterate, or release.",
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


def guard_segment_start(workspace_root: Path, segment: str) -> None:
    if segment not in {"build", "iterate", "release"}:
        return
    if not state_path(workspace_root).exists():
        return
    state = load_state(workspace_root)
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
    state["current_node_id"] = "release_claim_approval"
    save_state(workspace_root, state)
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
        return emit_status(workspace_root, args.json, exit_code=EXIT_MANUAL_ACTION)

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
    state["completed_nodes"] = ["release_claim_approval"]
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
        manifest = run_manifest(
            workspace_root=workspace_root,
            run_id=run_id,
            segment=segment,
            goal=goal,
            entrypoint=f"harness {segment}",
        )
        manifest_path = write_run_manifest(workspace_root, manifest)
        append_event(
            workspace_root,
            "RUN_STARTED",
            run_id=run_id,
            segment=segment,
            status="running",
            payload={"dry_run": bool(args.dry_run), "manifest": str(manifest_path)},
        )
        state = base_state(run_id, segment)
        save_state(workspace_root, state)

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

        if segment == "prepare":
            return start_prepare_hitl_poc(
                workspace_root,
                args=args,
                run_id=run_id,
                state=state,
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


def status_payload(workspace_root: Path) -> dict[str, Any]:
    state = load_state(workspace_root)
    pending_ref = None
    if pending_request_path(workspace_root).exists():
        pending = load_json(pending_request_path(workspace_root))
        if isinstance(pending, dict):
            pending_ref = {
                "request_id": pending.get("request_id"),
                "path": f"{SUPERVISOR_DIR}/pending_request.json",
            }
    return {
        "schema_version": SCHEMA_VERSION,
        "state": state,
        "pending_request_ref": pending_ref,
        "last_event_seq": latest_event_seq(workspace_root),
    }


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
    decision = answer_decision(answer_record)
    segment_status = "v0_resume_recorded"
    resume_status = "completed"
    resume_exit_code = EXIT_OK
    if (
        state.get("segment") == "prepare"
        and request.get("reason") == "evaluation_contract_approval_required"
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


def command_recover(args: argparse.Namespace) -> int:
    workspace_root = repo_root(args.workspace_root)
    if not state_path(workspace_root).exists():
        return EXIT_NO_ACTIVE_RUN
    state = load_state(workspace_root)
    errors = validate_state_invariants(state, workspace_root)
    event_seq = latest_event_seq(workspace_root)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id or state.get("active_run_id"),
        "state_valid": not errors,
        "errors": errors,
        "latest_event_seq": event_seq,
        "state_last_event_seq": state.get("last_event_seq"),
        "recommended_action": "manual_recover" if errors else "status_only",
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload["recommended_action"])
    return EXIT_MANUAL_ACTION if errors else EXIT_OK


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
    failed = [gate for gate in gate_ledger if gate["result"] == "FAIL"]
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
        if node.get("auto_allowed") is True and not postconditions:
            errors.append(f"{label}: auto_allowed nodes require postconditions")
        if node.get("auto_allowed") is True and not node.get("resume_strategy"):
            errors.append(f"{label}: auto_allowed nodes require resume_strategy")
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
    recover.add_argument("--json", action="store_true")
    recover.set_defaults(func=command_recover)

    tail = subparsers.add_parser("tail")
    tail.add_argument("--jsonl", action="store_true")
    tail.add_argument("--lines", type=int, default=30)
    tail.set_defaults(func=command_tail)

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
