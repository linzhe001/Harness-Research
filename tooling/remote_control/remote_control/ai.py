from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .config import RemoteControlConfig
from .logs import read_latest_log
from .paths import ctl_script_path, resolve_path
from .render import render_logs_text, render_status_text, render_tail_text
from .result import CommandResult, make_result


def _run_ctl(workspace_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    script = ctl_script_path(workspace_root)
    if not script.exists():
        raise FileNotFoundError(f"auto_iterate_ctl.sh not found: {script}")
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=str(workspace_root),
        capture_output=True,
        text=True,
        check=False,
    )


def _stdout_or_default(proc: subprocess.CompletedProcess[str], fallback: str) -> str:
    return proc.stdout.strip() or proc.stderr.strip() or fallback


def _error_from_process(proc: subprocess.CompletedProcess[str], fallback: str) -> CommandResult:
    return make_result(
        ok=False,
        exit_code=proc.returncode,
        message=_stdout_or_default(proc, fallback),
        data={"stdout": proc.stdout, "stderr": proc.stderr},
    )


def get_status(workspace_root: Path) -> CommandResult:
    proc = _run_ctl(workspace_root, ["status", "--json"])
    if proc.returncode != 0:
        return _error_from_process(proc, "Failed to load loop status.")

    data = json.loads(proc.stdout)
    return make_result(ok=True, exit_code=0, message=render_status_text(data), data=data)


def tail_events(workspace_root: Path, *, lines: int) -> CommandResult:
    proc = _run_ctl(workspace_root, ["tail", "--jsonl", "--lines", str(lines)])
    if proc.returncode != 0:
        return _error_from_process(proc, "Failed to read recent loop events.")

    events: list[dict[str, Any]] = []
    for raw_line in proc.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return make_result(ok=True, exit_code=0, message=render_tail_text(events), data={"events": events})


def pause_loop(workspace_root: Path) -> CommandResult:
    proc = _run_ctl(workspace_root, ["pause"])
    if proc.returncode != 0:
        return _error_from_process(proc, "Failed to pause the loop.")
    return make_result(ok=True, exit_code=0, message=_stdout_or_default(proc, "Pause signal created."))


def stop_loop(workspace_root: Path) -> CommandResult:
    proc = _run_ctl(workspace_root, ["stop"])
    if proc.returncode != 0:
        return _error_from_process(proc, "Failed to stop the loop.")
    return make_result(ok=True, exit_code=0, message=_stdout_or_default(proc, "Stop signal created."))


def resume_loop(workspace_root: Path, cfg: RemoteControlConfig) -> CommandResult:
    args = ["resume"]
    if cfg.default_controller_config and cfg.default_controller_config.exists():
        args.extend(["--config", str(cfg.default_controller_config)])
    if cfg.default_accounts_config and cfg.default_accounts_config.exists():
        args.extend(["--accounts", str(cfg.default_accounts_config)])
    proc = _run_ctl(workspace_root, args)
    if proc.returncode != 0:
        return _error_from_process(proc, "Failed to resume the loop.")
    return make_result(ok=True, exit_code=0, message=_stdout_or_default(proc, "Loop resumed successfully."))


def start_loop(
    workspace_root: Path,
    cfg: RemoteControlConfig,
    *,
    goal: str | Path | None = None,
    controller_config: str | Path | None = None,
    accounts_config: str | Path | None = None,
    max_rounds: int | None = None,
    dry_run: bool = False,
) -> CommandResult:
    goal_path = resolve_path(workspace_root, goal) or cfg.default_goal_path
    if goal_path is None:
        return make_result(ok=False, exit_code=100, message="Goal path is required for ai start.")

    args = ["start", "--goal", str(goal_path)]

    config_path = resolve_path(workspace_root, controller_config) or cfg.default_controller_config
    if config_path and config_path.exists():
        args.extend(["--config", str(config_path)])

    accounts_path = resolve_path(workspace_root, accounts_config) or cfg.default_accounts_config
    if accounts_path and accounts_path.exists():
        args.extend(["--accounts", str(accounts_path)])

    if max_rounds is not None:
        args.extend(["--max-rounds", str(max_rounds)])
    if dry_run:
        args.append("--dry-run")

    proc = _run_ctl(workspace_root, args)
    if proc.returncode != 0:
        return _error_from_process(proc, "Failed to start the loop.")
    return make_result(ok=True, exit_code=0, message=_stdout_or_default(proc, "Loop started successfully."))


def override_goal(workspace_root: Path, *, goal: str | Path) -> CommandResult:
    goal_path = resolve_path(workspace_root, goal)
    if goal_path is None:
        return make_result(ok=False, exit_code=100, message="Goal path is required for ai override.")

    proc = _run_ctl(workspace_root, ["override", "--goal", str(goal_path)])
    if proc.returncode != 0:
        return _error_from_process(proc, "Failed to stage the goal override.")
    return make_result(ok=True, exit_code=0, message=_stdout_or_default(proc, "Goal override staged successfully."))


def read_logs(workspace_root: Path, *, stream: str, lines: int) -> CommandResult:
    try:
        log_info = read_latest_log(workspace_root, stream=stream, lines=lines)
    except FileNotFoundError as exc:
        return make_result(ok=False, exit_code=101, message=str(exc))
    except ValueError as exc:
        return make_result(ok=False, exit_code=100, message=str(exc))
    return make_result(ok=True, exit_code=0, message=render_logs_text(log_info), data=log_info)
