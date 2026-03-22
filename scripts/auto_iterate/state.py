"""Atomic JSON persistence and schema-versioned state management.

All controller-owned files under `.auto_iterate/` use the helpers in this module
to guarantee crash-safe reads and writes.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

CURRENT_SCHEMA_VERSION = 1


class SchemaVersionError(Exception):
    """Raised when a loaded file has an incompatible schema_version."""


class StateLoadError(Exception):
    """Raised when a state file cannot be loaded or is malformed."""


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------

def atomic_write_json(path: str | Path, data: Any, *, indent: int = 2) -> None:
    """Write *data* as JSON to *path* via temp-file + atomic rename.

    The temp file is created in the same directory so that ``os.replace``
    is guaranteed to be an atomic rename on POSIX.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        # Clean up the temp file on any failure.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# JSON load helpers
# ---------------------------------------------------------------------------

def load_json(path: str | Path) -> Any:
    """Load and return parsed JSON from *path*.

    Raises ``StateLoadError`` if the file is missing or not valid JSON.
    """
    path = Path(path)
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise StateLoadError(f"File not found: {path}")
    except json.JSONDecodeError as exc:
        raise StateLoadError(f"Invalid JSON in {path}: {exc}")


def validate_schema_version(
    data: dict[str, Any],
    *,
    expected: int = CURRENT_SCHEMA_VERSION,
    label: str = "file",
) -> None:
    """Raise ``SchemaVersionError`` if *data* has an incompatible version."""
    version = data.get("schema_version")
    if version != expected:
        raise SchemaVersionError(
            f"{label} schema_version={version!r}, expected {expected}"
        )


# ---------------------------------------------------------------------------
# StateStore — thin convenience wrapper
# ---------------------------------------------------------------------------

class StateStore:
    """Manages `.auto_iterate/state.json` and `.auto_iterate/lock.json`."""

    def __init__(self, auto_iterate_dir: str | Path) -> None:
        self.root = Path(auto_iterate_dir)
        self.state_path = self.root / "state.json"
        self.lock_path = self.root / "lock.json"

    # -- state.json ----------------------------------------------------------

    def load_state(self) -> dict[str, Any]:
        data = load_json(self.state_path)
        validate_schema_version(data, label="state.json")
        return data

    def save_state(self, data: dict[str, Any]) -> None:
        atomic_write_json(self.state_path, data)

    # -- lock.json -----------------------------------------------------------

    def load_lock(self) -> dict[str, Any]:
        data = load_json(self.lock_path)
        validate_schema_version(data, label="lock.json")
        return data

    def save_lock(self, data: dict[str, Any]) -> None:
        atomic_write_json(self.lock_path, data)

    # -- directory -----------------------------------------------------------

    def ensure_dirs(self) -> None:
        """Create the `.auto_iterate/` tree if it does not exist."""
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "runtime").mkdir(exist_ok=True)
        (self.root / "logs").mkdir(exist_ok=True)
