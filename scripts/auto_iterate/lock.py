"""Single-active-loop lock with heartbeat-based stale detection.

The lock file `.auto_iterate/lock.json` ensures only one controller loop
runs in a workspace at a time.  A background heartbeat worker (see
``runtime.py``) periodically refreshes ``heartbeat_at``; if the heartbeat
goes stale, ``resume`` may clear the lock and take over.
"""

from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state import (
    SchemaVersionError,
    StateLoadError,
    atomic_write_json,
    load_json,
    validate_schema_version,
)

# Exit code for live lock conflict (frozen in 01_contract_freeze §8.5).
EXIT_LOCK_CONFLICT = 102


class LockConflictError(Exception):
    """Another live controller holds the lock."""


class LockManager:
    """Manage `.auto_iterate/lock.json`."""

    def __init__(self, lock_path: str | Path, *, stale_threshold_sec: int = 120) -> None:
        self.lock_path = Path(lock_path)
        self.stale_threshold_sec = stale_threshold_sec

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def acquire(
        self,
        loop_id: str,
        tool: str,
        workspace_root: str,
    ) -> dict[str, Any]:
        """Create a new lock.  Raises ``LockConflictError`` if a live lock exists."""
        conflict = self.check_conflict()
        if conflict == "live":
            raise LockConflictError(
                f"Live lock held by pid={self._last_lock.get('pid')} "  # type: ignore[union-attr]
                f"on {self._last_lock.get('host')}"  # type: ignore[union-attr]
            )
        # Stale or absent — safe to (re)create.
        now = _utcnow_iso()
        lock_data: dict[str, Any] = {
            "schema_version": 1,
            "loop_id": loop_id,
            "pid": os.getpid(),
            "host": platform.node(),
            "started_at": now,
            "heartbeat_at": now,
            "tool": tool,
            "workspace_root": workspace_root,
        }
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.lock_path, lock_data)
        return lock_data

    def release(self) -> None:
        """Remove the lock file."""
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass

    def update_heartbeat(self) -> None:
        """Refresh ``heartbeat_at`` in the existing lock (atomic write)."""
        data = load_json(self.lock_path)
        data["heartbeat_at"] = _utcnow_iso()
        atomic_write_json(self.lock_path, data)

    # ------------------------------------------------------------------
    # Conflict / staleness inspection
    # ------------------------------------------------------------------

    def check_conflict(self) -> str:
        """Return ``"live"``, ``"stale"``, or ``"none"``.

        Also stores the loaded lock in ``self._last_lock`` for diagnostics.
        """
        self._last_lock: dict[str, Any] | None = None
        try:
            data = load_json(self.lock_path)
        except StateLoadError:
            return "none"
        try:
            validate_schema_version(data, label="lock.json")
        except SchemaVersionError:
            # Incompatible lock — treat as stale (the old controller is
            # certainly not running a compatible version).
            self._last_lock = data
            return "stale"

        self._last_lock = data

        if self.is_stale(data):
            return "stale"

        # Check if the PID is still alive (best-effort on the same host).
        pid = data.get("pid")
        host = data.get("host")
        if host == platform.node() and pid is not None:
            if not _pid_alive(pid):
                return "stale"

        return "live"

    def is_stale(self, lock_data: dict[str, Any] | None = None) -> bool:
        """Return True if *lock_data* heartbeat is older than the threshold."""
        if lock_data is None:
            try:
                lock_data = load_json(self.lock_path)
            except StateLoadError:
                return False

        heartbeat = lock_data.get("heartbeat_at")
        if heartbeat is None:
            return True

        try:
            hb_dt = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return True

        age = (datetime.now(timezone.utc) - hb_dt).total_seconds()
        return age > self.stale_threshold_sec

    def clear_stale(self) -> dict[str, Any] | None:
        """Remove a stale lock and return its data (or ``None`` if not stale)."""
        conflict = self.check_conflict()
        if conflict != "stale":
            return None
        cleared = self._last_lock
        self.release()
        return cleared

    def load(self) -> dict[str, Any] | None:
        """Load lock data or return None if absent."""
        try:
            return load_json(self.lock_path)
        except StateLoadError:
            return None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pid_alive(pid: int) -> bool:
    """Best-effort check whether *pid* is alive (POSIX only)."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
