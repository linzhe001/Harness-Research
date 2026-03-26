from __future__ import annotations

from pathlib import Path


def resolve_workspace_root(workspace_root: str | Path | None = None) -> Path:
    if workspace_root is None:
        return Path.cwd().resolve()
    return Path(workspace_root).resolve()


def resolve_path(base: Path, value: str | Path | None) -> Path | None:
    if value in (None, ""):
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


def ctl_script_path(workspace_root: Path) -> Path:
    return workspace_root / "tooling" / "auto_iterate" / "scripts" / "auto_iterate_ctl.sh"


def runtime_dir(workspace_root: Path) -> Path:
    return workspace_root / ".auto_iterate" / "runtime"
