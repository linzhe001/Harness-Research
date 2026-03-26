from __future__ import annotations

from pathlib import Path
from typing import Any

from .ai import get_status, tail_events
from .config import RemoteControlConfig
from .hints import recommended_actions
from .logs import latest_log_paths


def build_summary(workspace_root: Path, cfg: RemoteControlConfig) -> dict[str, Any]:
    status_result = get_status(workspace_root)
    status = status_result.data

    latest_event = None
    tail_result = tail_events(workspace_root, lines=1)
    if tail_result.ok:
        events = tail_result.data.get("events", [])
        if events:
            latest_event = events[-1]

    auto_iterate_present = (workspace_root / ".auto_iterate").exists()
    staged_goal_present = (workspace_root / ".auto_iterate" / "goal.next.md").exists()

    ai_summary = {
        "present": auto_iterate_present,
        "status": None,
        "halt_reason": None,
        "current_round_index": None,
        "current_phase_key": None,
        "selected_account_id": None,
        "metric_name": None,
        "best_primary_metric": None,
    }
    if status and not status.get("error"):
        ai_summary.update(
            {
                "status": status.get("status"),
                "halt_reason": status.get("halt_reason"),
                "current_round_index": status.get("current_round_index"),
                "current_phase_key": status.get("current_phase_key"),
                "selected_account_id": status.get("accounts", {}).get("selected_account_id"),
                "metric_name": status.get("objective", {}).get("primary_metric", {}).get("name"),
                "best_primary_metric": status.get("best", {}).get("primary_metric"),
            }
        )
    elif status.get("error"):
        ai_summary["status"] = "inactive"

    return {
        "workspace": {
            "name": workspace_root.name,
            "root": str(workspace_root),
        },
        "remote_control": {
            "default_goal_path": str(cfg.default_goal_path) if cfg.default_goal_path else None,
            "default_controller_config": str(cfg.default_controller_config) if cfg.default_controller_config else None,
            "default_accounts_config": str(cfg.default_accounts_config) if cfg.default_accounts_config else None,
        },
        "auto_iterate": ai_summary,
        "latest_event": latest_event,
        "latest_logs": latest_log_paths(workspace_root),
        "staged_goal_present": staged_goal_present,
        "recommended_actions": recommended_actions(
            {
                "workspace": {"name": workspace_root.name, "root": str(workspace_root)},
                "auto_iterate": ai_summary,
            }
        ),
    }
