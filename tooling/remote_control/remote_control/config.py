from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import resolve_path

try:
    import yaml
except Exception:  # pragma: no cover - environment dependent
    yaml = None


@dataclass
class RemoteControlConfig:
    workspace_root: Path
    default_goal_path: Path | None
    default_controller_config: Path | None
    default_accounts_config: Path | None
    default_tail_lines: int = 20
    default_log_lines: int = 40


def _default_config(workspace_root: Path) -> RemoteControlConfig:
    goal = workspace_root / "docs" / "auto_iterate_goal.md"
    ctl_cfg = workspace_root / "tooling" / "auto_iterate" / "config" / "controller.local.yaml"
    accounts = workspace_root / "tooling" / "auto_iterate" / "config" / "accounts.local.yaml"
    return RemoteControlConfig(
        workspace_root=workspace_root,
        default_goal_path=goal if goal.exists() else None,
        default_controller_config=ctl_cfg if ctl_cfg.exists() else None,
        default_accounts_config=accounts if accounts.exists() else None,
        default_tail_lines=20,
        default_log_lines=40,
    )


def _load_mapping(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load remote control config files.")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"Remote control config must decode to a mapping: {path}")
    return data


def load_config(workspace_root: Path, explicit_path: str | Path | None = None) -> RemoteControlConfig:
    cfg = _default_config(workspace_root)

    candidate = resolve_path(workspace_root, explicit_path)
    if candidate is None:
        default_candidate = workspace_root / "tooling" / "remote_control" / "config" / "remote_control.local.yaml"
        candidate = default_candidate if default_candidate.exists() else None

    if candidate is None:
        return cfg

    if not candidate.exists():
        raise RuntimeError(f"Remote control config not found: {candidate}")

    data = _load_mapping(candidate)
    cfg.default_goal_path = resolve_path(workspace_root, data.get("default_goal_path")) or cfg.default_goal_path
    cfg.default_controller_config = (
        resolve_path(workspace_root, data.get("default_controller_config")) or cfg.default_controller_config
    )
    cfg.default_accounts_config = (
        resolve_path(workspace_root, data.get("default_accounts_config")) or cfg.default_accounts_config
    )
    if "default_tail_lines" in data:
        cfg.default_tail_lines = int(data["default_tail_lines"])
    if "default_log_lines" in data:
        cfg.default_log_lines = int(data["default_log_lines"])
    return cfg
