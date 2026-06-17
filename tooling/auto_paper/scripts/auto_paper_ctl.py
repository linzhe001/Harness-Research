#!/usr/bin/env python3
"""Minimal stateful controller for the auto-paper artifact chain."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
AUTO_ITERATE_SCRIPTS = REPO_ROOT / "tooling" / "auto_iterate" / "scripts"
AUTO_PAPER_SKILL_SCRIPTS = (
    REPO_ROOT / ".agents" / "skills" / "auto-paper" / "scripts"
)
for candidate in (AUTO_ITERATE_SCRIPTS, AUTO_PAPER_SKILL_SCRIPTS):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from artifact_check import PHASES, run_checks  # noqa: E402
from auto_iterate.events import EventLogger, iso_now  # noqa: E402
from auto_iterate.lock import LockConflictError, LockManager  # noqa: E402
from auto_iterate.state import (  # noqa: E402
    StateLoadError,
    atomic_write_json,
    load_json,
)

SCHEMA_VERSION = 1
CLOSED_REQUEST_STATUSES = {
    "accepted",
    "cancelled",
    "closed",
    "complete",
    "completed",
    "done",
    "not_needed",
}
PHASE_ORDER = list(PHASES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Control an auto-paper run.")
    parser.add_argument("--workspace-root", default=".", type=Path)
    parser.add_argument("--auto-paper-dir", default=".auto_paper", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start or re-evaluate a paper run.")
    start.add_argument("--paper-id", required=True)
    start.add_argument("--artifact-dir", type=Path)
    start.add_argument("--dry-run", action="store_true")

    resume = subparsers.add_parser("resume", help="Resume from saved state.")
    resume.add_argument("--paper-id")
    resume.add_argument("--artifact-dir", type=Path)
    resume.add_argument("--dry-run", action="store_true")

    status = subparsers.add_parser("status", help="Print controller state.")
    status.add_argument("--json", action="store_true")

    stop = subparsers.add_parser("stop", help="Release the controller lock.")
    stop.add_argument("--json", action="store_true")
    return parser.parse_args()


def resolve_path(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def state_path(root: Path, auto_paper_dir: Path) -> Path:
    return resolve_path(root, auto_paper_dir) / "state.json"


def events_path(root: Path, auto_paper_dir: Path) -> Path:
    return resolve_path(root, auto_paper_dir) / "events.jsonl"


def lock_path(root: Path, auto_paper_dir: Path) -> Path:
    return resolve_path(root, auto_paper_dir) / "lock.json"


def default_artifact_dir(root: Path, paper_id: str) -> Path:
    return root / "auto_paper_output" / paper_id


def load_state(path: Path) -> dict[str, Any] | None:
    try:
        data = load_json(path)
    except StateLoadError:
        return None
    if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION:
        return data
    return None


def new_state(root: Path, paper_id: str, artifact_dir: Path) -> dict[str, Any]:
    now = iso_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "controller": "auto-paper",
        "paper_id": paper_id,
        "artifact_dir": artifact_dir.resolve().relative_to(root).as_posix()
        if artifact_dir.is_relative_to(root)
        else artifact_dir.as_posix(),
        "status": "running",
        "current_phase_key": PHASE_ORDER[0],
        "phase_attempt": 0,
        "last_decision": "START",
        "halt_reason": "",
        "last_failure": [],
        "completed_phases": [],
        "started_at": now,
        "updated_at": now,
    }


def pending_run_requests(artifact_dir: Path) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    requests.extend(pending_json_requests(artifact_dir / "run_request_register.json"))
    if requests:
        return requests
    return pending_markdown_requests(artifact_dir / "run_request_register.md")


def pending_json_requests(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [
            {
                "request_id": "run_req_parse_error",
                "status": "invalid",
                "needed_evidence": f"{path.name} is invalid JSON",
            }
        ]
    values = data.get("requests") if isinstance(data, dict) else None
    if not isinstance(values, list):
        return []
    pending: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "pending")).strip().lower()
        if status not in CLOSED_REQUEST_STATUSES:
            pending.append(item)
    return pending


def split_table_line(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def pending_markdown_requests(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for index, line in enumerate(lines):
        if "|" not in line or index + 1 >= len(lines):
            continue
        header = [cell.lower() for cell in split_table_line(line)]
        separator = split_table_line(lines[index + 1])
        if "status" not in header or not all(
            set(cell) <= {"-", ":"} for cell in separator
        ):
            continue
        rows: list[dict[str, Any]] = []
        for raw in lines[index + 2 :]:
            if "|" not in raw:
                break
            cells = split_table_line(raw)
            row = {
                header[cell_index]: cell
                for cell_index, cell in enumerate(cells)
                if cell_index < len(header)
            }
            status = row.get("status", "pending").strip().lower()
            if status not in CLOSED_REQUEST_STATUSES:
                rows.append(row)
        return rows
    return []


def next_phase(phase: str) -> str | None:
    try:
        index = PHASE_ORDER.index(phase)
    except ValueError:
        return PHASE_ORDER[0]
    if index + 1 >= len(PHASE_ORDER):
        return None
    return PHASE_ORDER[index + 1]


def evaluate_state(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    artifact_dir = resolve_path(root, Path(state["artifact_dir"]))
    phase = str(state.get("current_phase_key") or PHASE_ORDER[0])
    now = iso_now()
    state["updated_at"] = now
    state["phase_attempt"] = int(state.get("phase_attempt", 0)) + 1

    run_requests = pending_run_requests(artifact_dir)
    if run_requests:
        state.update(
            {
                "status": "paused",
                "last_decision": "RUN_REQUEST",
                "halt_reason": "Pending run_request_register entries need $run.",
                "last_failure": run_requests,
            }
        )
        return state

    findings = run_checks(artifact_dir, phase)
    errors = [asdict(item) for item in findings if item.severity == "error"]
    if errors:
        decision = "USER_GATE" if phase == "intake" else f"REWORK_{phase.upper()}"
        state.update(
            {
                "status": "paused",
                "last_decision": decision,
                "halt_reason": f"{len(errors)} blocking artifact issue(s).",
                "last_failure": errors,
            }
        )
        return state

    completed = list(state.get("completed_phases", []))
    if phase not in completed:
        completed.append(phase)
    following = next_phase(phase)
    if following is None:
        state.update(
            {
                "status": "complete",
                "last_decision": "COMPLETE",
                "halt_reason": "",
                "last_failure": [],
                "completed_phases": completed,
            }
        )
        return state

    state.update(
        {
            "status": "paused",
            "current_phase_key": following,
            "last_decision": "NEXT_PHASE",
            "halt_reason": f"Ready for `{following}`.",
            "last_failure": [],
            "completed_phases": completed,
        }
    )
    return state


def emit_event(
    root: Path,
    auto_paper_dir: Path,
    event: str,
    state: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> None:
    EventLogger(events_path(root, auto_paper_dir)).emit(
        event,
        str(state["paper_id"]),
        str(state["status"]),
        phase_key=str(state.get("current_phase_key", "")),
        payload=payload,
    )


def start_or_resume(args: argparse.Namespace, *, start: bool) -> int:
    root = args.workspace_root.resolve()
    path = state_path(root, args.auto_paper_dir)
    existing = load_state(path)
    if start or existing is None:
        if not args.paper_id:
            raise SystemExit("--paper-id is required when no saved state exists")
        artifact_dir = (
            resolve_path(root, args.artifact_dir)
            if args.artifact_dir
            else default_artifact_dir(root, args.paper_id)
        )
        state = new_state(root, args.paper_id, artifact_dir)
    else:
        state = existing
        if args.paper_id:
            state["paper_id"] = args.paper_id
        if args.artifact_dir:
            state["artifact_dir"] = resolve_path(root, args.artifact_dir).as_posix()

    evaluated = evaluate_state(root, state)
    if args.dry_run:
        print(json.dumps(evaluated, indent=2, ensure_ascii=False))
        return 0

    lock = LockManager(lock_path(root, args.auto_paper_dir))
    try:
        lock.acquire(str(evaluated["paper_id"]), "auto-paper", root.as_posix())
    except LockConflictError as exc:
        print(f"auto-paper lock conflict: {exc}", file=sys.stderr)
        return 102
    try:
        atomic_write_json(path, evaluated)
        emit_event(
            root,
            args.auto_paper_dir,
            "start" if start else "resume",
            evaluated,
            {"decision": evaluated["last_decision"]},
        )
    finally:
        lock.release()
    print(json.dumps(evaluated, indent=2, ensure_ascii=False))
    return 0


def print_status(args: argparse.Namespace) -> int:
    root = args.workspace_root.resolve()
    state = load_state(state_path(root, args.auto_paper_dir))
    if state is None:
        state = {
            "schema_version": SCHEMA_VERSION,
            "controller": "auto-paper",
            "status": "absent",
        }
    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print(f"status: {state.get('status')}")
        if state.get("paper_id"):
            print(f"paper_id: {state.get('paper_id')}")
        if state.get("current_phase_key"):
            print(f"current_phase_key: {state.get('current_phase_key')}")
        if state.get("last_decision"):
            print(f"last_decision: {state.get('last_decision')}")
        if state.get("halt_reason"):
            print(f"halt_reason: {state.get('halt_reason')}")
    return 0


def stop(args: argparse.Namespace) -> int:
    root = args.workspace_root.resolve()
    lock = LockManager(lock_path(root, args.auto_paper_dir))
    lock.release()
    state = load_state(state_path(root, args.auto_paper_dir))
    if state is not None:
        state["status"] = "stopped"
        state["updated_at"] = iso_now()
        atomic_write_json(state_path(root, args.auto_paper_dir), state)
        emit_event(root, args.auto_paper_dir, "stop", state)
    if args.json:
        print(json.dumps(state or {"status": "absent"}, indent=2, ensure_ascii=False))
    else:
        print("stopped" if state else "absent")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "start":
        return start_or_resume(args, start=True)
    if args.command == "resume":
        return start_or_resume(args, start=False)
    if args.command == "status":
        return print_status(args)
    if args.command == "stop":
        return stop(args)
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
