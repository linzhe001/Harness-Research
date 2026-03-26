from __future__ import annotations

from pathlib import Path

from .paths import runtime_dir


def find_runtime_logs(workspace_root: Path) -> dict[str, list[Path]]:
    root = runtime_dir(workspace_root)
    if not root.exists():
        return {"stdout": [], "stderr": []}

    stdout_logs = sorted(root.glob("*.stdout.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    stderr_logs = sorted(root.glob("*.stderr.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"stdout": stdout_logs, "stderr": stderr_logs}


def latest_log_paths(workspace_root: Path) -> dict[str, str | None]:
    logs = find_runtime_logs(workspace_root)
    return {
        "stdout": str(logs["stdout"][0]) if logs["stdout"] else None,
        "stderr": str(logs["stderr"][0]) if logs["stderr"] else None,
    }


def read_latest_log(workspace_root: Path, stream: str = "stdout", lines: int = 40) -> dict[str, object]:
    if stream not in ("stdout", "stderr"):
        raise ValueError("stream must be 'stdout' or 'stderr'")

    logs = find_runtime_logs(workspace_root)
    selected = logs[stream]
    if not selected:
        raise FileNotFoundError(f"No {stream} runtime logs found under {runtime_dir(workspace_root)}")

    path = selected[0]
    text = path.read_text(encoding="utf-8", errors="replace")
    content_lines = text.splitlines()
    tail = content_lines[-lines:] if lines > 0 else content_lines
    return {
        "stream": stream,
        "path": str(path),
        "lines": len(tail),
        "content": "\n".join(tail),
    }
