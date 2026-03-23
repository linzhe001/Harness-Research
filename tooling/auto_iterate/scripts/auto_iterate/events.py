"""Append-only event logger for the auto-iterate controller.

Events are written as one JSON object per line to `.auto_iterate/events.jsonl`.
Rotation (archiving the current file and starting fresh) is atomic and may only
happen at round boundaries or when the loop is not ``running``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def iso_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EventLogger:
    """Manages `.auto_iterate/events.jsonl`."""

    def __init__(self, events_path: str | Path) -> None:
        self.events_path = Path(events_path)

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def emit(
        self,
        event: str,
        loop_id: str,
        status: str,
        *,
        round_index: int | None = None,
        phase_key: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one event line and return the event dict."""
        entry: dict[str, Any] = {
            "v": 1,
            "ts": iso_now(),
            "event": event,
            "loop_id": loop_id,
            "status": status,
        }
        if round_index is not None:
            entry["round_index"] = round_index
        if phase_key is not None:
            entry["phase_key"] = phase_key
        if payload is not None:
            entry["payload"] = payload

        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

        return entry

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    def rotate_if_needed(self, max_bytes: int) -> str | None:
        """Rotate the event log if it exceeds *max_bytes*.

        Returns the archive path on success, or ``None`` if rotation was
        not needed or the file does not exist.

        Rotation is an atomic rename; a new empty ``events.jsonl`` is created
        after the rename.  If the rename fails but the active file is still
        writable, this is a non-fatal warning (returns ``None``).
        """
        if not self.events_path.exists():
            return None
        if self.events_path.stat().st_size < max_bytes:
            return None

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = self.events_path.with_name(f"events.{ts}.jsonl")

        try:
            os.replace(str(self.events_path), str(archive))
        except OSError:
            # Non-fatal: keep appending to the current file.
            return None

        # Create a fresh (empty) events file.
        self.events_path.touch()
        return str(archive)

    # ------------------------------------------------------------------
    # Tail
    # ------------------------------------------------------------------

    def tail(self, lines: int = 20, *, jsonl: bool = False) -> list[Any]:
        """Return the last *lines* events.

        If *jsonl* is True, returns raw dicts parsed from each line.
        Otherwise returns the same dicts (caller can format as needed).
        """
        if not self.events_path.exists():
            return []

        all_lines = self.events_path.read_text().splitlines()
        tail_lines = all_lines[-lines:] if lines < len(all_lines) else all_lines

        result: list[Any] = []
        for raw in tail_lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                result.append(json.loads(raw))
            except json.JSONDecodeError:
                # Skip malformed lines in tail output.
                continue
        return result

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return the number of event lines in the file."""
        if not self.events_path.exists():
            return 0
        return sum(1 for line in self.events_path.read_text().splitlines() if line.strip())

    def size_bytes(self) -> int:
        """Return the file size in bytes, or 0 if absent."""
        if not self.events_path.exists():
            return 0
        return self.events_path.stat().st_size
