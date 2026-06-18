#!/usr/bin/env python3
"""Machine-readable run health watchdog for Harness experiment loops.

The watchdog is intentionally notification-free. It writes JSON/TXT status
files that humans, cron, SSH wrappers, or workflow tooling can poll.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_BASE = "/tmp/harness-run-health"
DEFAULT_INTERVAL = 60
DEFAULT_IDLE_GRACE_SECONDS = 600
DEFAULT_STALLED_GRACE_SECONDS = 900
GPU_IDLE_THRESHOLD = 5
OOM_PATTERNS = (
    "out of memory",
    "cuda out of memory",
    "cublas_status_alloc_failed",
    "runtimeerror: cuda",
)
BAD_STATUSES = {"DEAD", "OOM", "STALLED", "IDLE_WARN", "FAILED", "ERROR"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def epoch_now() -> float:
    return time.time()


def paths(base_dir: str | Path) -> dict[str, Path]:
    base = Path(base_dir)
    return {
        "base": base,
        "pid": base / "watchdog.pid",
        "tasks": base / "tasks.json",
        "status": base / "status",
        "summary_json": base / "status" / "summary.json",
        "summary_txt": base / "status" / "summary.txt",
        "alerts": base / "alerts.log",
    }


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def load_tasks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")
    return [item for item in data if isinstance(item, dict)]


def validate_task(task: dict[str, Any]) -> None:
    missing = [key for key in ("name", "type", "session") if not task.get(key)]
    if missing:
        raise ValueError(f"missing required task fields: {', '.join(missing)}")
    if task["type"] not in {"training", "download", "command"}:
        raise ValueError("task type must be training, download, or command")
    if task.get("session_type") not in {None, "screen", "tmux", "pid", "none"}:
        raise ValueError("session_type must be screen, tmux, pid, or none")


def register_task(base_dir: str | Path, task_json: str) -> dict[str, Any]:
    p = paths(base_dir)
    p["base"].mkdir(parents=True, exist_ok=True)
    p["status"].mkdir(parents=True, exist_ok=True)
    task = json.loads(task_json)
    if not isinstance(task, dict):
        raise ValueError("--register JSON must be an object")
    validate_task(task)
    task.setdefault("session_type", "screen")
    task.setdefault("registered_at", utc_now())
    tasks = load_tasks(p["tasks"]) if p["tasks"].exists() else []
    tasks = [item for item in tasks if item.get("name") != task["name"]]
    tasks.append(task)
    atomic_write_json(p["tasks"], tasks)
    return task


def unregister_task(base_dir: str | Path, name: str) -> bool:
    p = paths(base_dir)
    tasks = load_tasks(p["tasks"]) if p["tasks"].exists() else []
    remaining = [item for item in tasks if item.get("name") != name]
    changed = len(remaining) != len(tasks)
    atomic_write_json(p["tasks"], remaining)
    status_file = p["status"] / f"{name}.json"
    status_file.unlink(missing_ok=True)
    write_summary(base_dir)
    return changed


def run_command(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def session_alive(session: str, session_type: str = "screen") -> bool:
    if session_type == "none":
        return True
    if session_type == "pid":
        try:
            os.kill(int(session), 0)
        except (OSError, ValueError):
            return False
        return True
    if session_type == "tmux":
        try:
            return run_command(["tmux", "has-session", "-t", session]).returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    try:
        result = run_command(["screen", "-list"])
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return session in result.stdout


def gpu_snapshot() -> list[dict[str, int]]:
    try:
        result = run_command(
            [
                "nvidia-smi",
                "--query-gpu=index,utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
            ]
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    gpus: list[dict[str, int]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            gpus.append(
                {
                    "index": int(parts[0]),
                    "utilization": int(parts[1]),
                    "memory_mb": int(parts[2]),
                }
            )
        except ValueError:
            continue
    return gpus


def selected_gpu_snapshot(task: dict[str, Any]) -> list[dict[str, int]]:
    gpus = gpu_snapshot()
    selected = task.get("gpus")
    if not isinstance(selected, list) or not selected:
        return gpus
    wanted = {int(item) for item in selected if isinstance(item, int)}
    return [item for item in gpus if item["index"] in wanted]


def path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def log_tail(path: Path, max_bytes: int = 16_384) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as handle:
        try:
            handle.seek(-max_bytes, os.SEEK_END)
        except OSError:
            handle.seek(0)
        return handle.read().decode("utf-8", errors="replace")


def tail_hash(text: str) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def previous_status(status_dir: Path, task_name: str) -> dict[str, Any]:
    path = status_dir / f"{task_name}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def progress_fields(task: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    target = task.get("target_path")
    if isinstance(target, str) and target:
        result["target_size"] = path_size(Path(target))
    log_path = task.get("log_path")
    if isinstance(log_path, str) and log_path:
        path = Path(log_path)
        if path.exists():
            stat = path.stat()
            result["log_mtime"] = stat.st_mtime
            result["log_size"] = stat.st_size
            result["log_tail_hash"] = tail_hash(log_tail(path))
    return result


def detect_progress(prev: dict[str, Any], current: dict[str, Any]) -> bool:
    for key in ("target_size", "log_mtime", "log_size", "log_tail_hash"):
        if current.get(key) != prev.get(key):
            return True
    return False


def output_complete(task: dict[str, Any]) -> bool:
    value = task.get("output_check")
    return isinstance(value, str) and bool(value) and Path(value).exists()


def task_status(task: dict[str, Any], status_dir: Path) -> dict[str, Any]:
    validate_task(task)
    name = str(task["name"])
    now = epoch_now()
    now_iso = utc_now()
    prev = previous_status(status_dir, name)
    current_progress = progress_fields(task)
    if output_complete(task):
        return {
            **base_status(task, "COMPLETED", now_iso),
            **current_progress,
            "last_progress_ts": now,
            "msg": "output_check exists",
            "suggested_action": "collect_artifacts",
        }

    log_path = task.get("log_path")
    if isinstance(log_path, str) and log_path:
        tail = log_tail(Path(log_path)).lower()
        if any(pattern in tail for pattern in OOM_PATTERNS):
            return {
                **base_status(task, "OOM", now_iso),
                **current_progress,
                "last_progress_ts": prev.get("last_progress_ts", now),
                "msg": "OOM signature found in log tail",
                "suggested_action": "reduce_batch_or_restart_from_checkpoint",
            }

    session_type = str(task.get("session_type", "screen"))
    if not session_alive(str(task["session"]), session_type):
        return {
            **base_status(task, "DEAD", now_iso),
            **current_progress,
            "last_progress_ts": prev.get("last_progress_ts", now),
            "msg": f"{session_type} session is not alive",
            "suggested_action": "inspect_logs_and_resume_or_unregister",
        }

    current_progress["gpu"] = selected_gpu_snapshot(task)
    active_gpu = any(
        item.get("utilization", 0) >= GPU_IDLE_THRESHOLD
        for item in current_progress["gpu"]
    )
    made_progress = active_gpu or detect_progress(prev, current_progress)
    last_progress_ts = (
        now if made_progress else float(prev.get("last_progress_ts", now))
    )
    idle_grace = int(task.get("idle_grace_seconds", DEFAULT_IDLE_GRACE_SECONDS))
    stalled_grace = int(
        task.get("stalled_grace_seconds", DEFAULT_STALLED_GRACE_SECONDS)
    )
    idle_age = now - last_progress_ts
    if task["type"] == "training" and current_progress["gpu"] and not active_gpu:
        if idle_age >= idle_grace:
            return {
                **base_status(task, "IDLE_WARN", now_iso),
                **current_progress,
                "last_progress_ts": last_progress_ts,
                "msg": f"selected GPUs idle for {int(idle_age)}s",
                "suggested_action": "inspect_training_log_or_scheduler",
            }
    if idle_age >= stalled_grace:
        return {
            **base_status(task, "STALLED", now_iso),
            **current_progress,
            "last_progress_ts": last_progress_ts,
            "msg": f"no observed progress for {int(idle_age)}s",
            "suggested_action": "inspect_session_log_and_resume_or_stop",
        }
    return {
        **base_status(task, "OK", now_iso),
        **current_progress,
        "last_progress_ts": last_progress_ts,
        "msg": "session alive and progress recently observed",
        "suggested_action": "none",
    }


def base_status(task: dict[str, Any], status: str, ts: str) -> dict[str, Any]:
    result = {
        "status": status,
        "task": task.get("name"),
        "type": task.get("type"),
        "session": task.get("session"),
        "session_type": task.get("session_type", "screen"),
        "ts": ts,
    }
    for key in (
        "registered_by",
        "workspace_root",
        "phase_key",
        "loop_id",
        "round_index",
        "iteration_id",
        "result_path",
        "log_path",
        "stderr_path",
        "output_check",
    ):
        if key in task:
            result[key] = task.get(key)
    return result


def write_status(base_dir: str | Path, status: dict[str, Any]) -> None:
    p = paths(base_dir)
    p["status"].mkdir(parents=True, exist_ok=True)
    atomic_write_json(p["status"] / f"{status['task']}.json", status)
    if status.get("status") in BAD_STATUSES:
        line = (
            f"[{status.get('ts')}] {status.get('task')}: "
            f"{status.get('status')} {status.get('msg', '')}\n"
        )
        with p["alerts"].open("a", encoding="utf-8") as handle:
            handle.write(line)


def check_all(base_dir: str | Path) -> list[dict[str, Any]]:
    p = paths(base_dir)
    p["base"].mkdir(parents=True, exist_ok=True)
    p["status"].mkdir(parents=True, exist_ok=True)
    statuses: list[dict[str, Any]] = []
    for task in load_tasks(p["tasks"]):
        try:
            status = task_status(task, p["status"])
        except Exception as exc:  # noqa: BLE001 - watchdog must keep polling
            status = {
                "status": "ERROR",
                "task": task.get("name", "<unknown>"),
                "type": task.get("type", "unknown"),
                "ts": utc_now(),
                "msg": str(exc),
                "suggested_action": "fix_task_registration",
            }
        write_status(base_dir, status)
        statuses.append(status)
    write_summary(base_dir)
    return statuses


def write_summary(base_dir: str | Path) -> dict[str, Any]:
    p = paths(base_dir)
    p["status"].mkdir(parents=True, exist_ok=True)
    statuses: list[dict[str, Any]] = []
    for status_file in sorted(p["status"].glob("*.json")):
        if status_file.name == "summary.json":
            continue
        try:
            data = json.loads(status_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            statuses.append(data)
    summary = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "task_count": len(statuses),
        "statuses": statuses,
    }
    atomic_write_json(p["summary_json"], summary)
    lines = []
    for item in statuses:
        lines.append(
            f"{item.get('task')}({item.get('type')}): "
            f"{item.get('status')} - {item.get('msg', '')}"
        )
    p["summary_txt"].write_text(
        "\n".join(lines) + ("\n" if lines else "no tasks\n"),
        encoding="utf-8",
    )
    return summary


def run_watchdog(base_dir: str | Path, interval: int) -> None:
    p = paths(base_dir)
    p["base"].mkdir(parents=True, exist_ok=True)
    p["status"].mkdir(parents=True, exist_ok=True)
    p["pid"].write_text(str(os.getpid()), encoding="utf-8")

    def cleanup(_signum: int, _frame: Any) -> None:
        p["pid"].unlink(missing_ok=True)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    while True:
        check_all(base_dir)
        time.sleep(interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=DEFAULT_BASE)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    parser.add_argument("--register", metavar="JSON")
    parser.add_argument("--unregister", metavar="NAME")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.register:
            task = register_task(args.base_dir, args.register)
            print(f"registered: {task['name']}")
            return 0
        if args.unregister:
            changed = unregister_task(args.base_dir, args.unregister)
            print(f"unregistered: {args.unregister}" if changed else "not registered")
            return 0
        if args.once:
            statuses = check_all(args.base_dir)
            if args.json:
                print(json.dumps(statuses, indent=2, ensure_ascii=False))
            return 0
        if args.status:
            summary = write_summary(args.base_dir)
            if args.json:
                print(json.dumps(summary, indent=2, ensure_ascii=False))
            else:
                print(paths(args.base_dir)["summary_txt"].read_text(encoding="utf-8"))
            return 0
        run_watchdog(args.base_dir, args.interval)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
