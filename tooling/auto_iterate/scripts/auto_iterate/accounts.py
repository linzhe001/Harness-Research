"""External current-auth source for Codex auto-iterate.

Auto-iterate no longer maintains its own Codex account pool. It always launches
Codex with one logical account, backed by the current ``CODEX_HOME``. External
tooling such as Windows Cockpit owns account switching by updating the auth file
that ``CODEX_HOME`` points at.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXTERNAL_CURRENT_ACCOUNT_ID = "external_current"
EXTERNAL_CURRENT_MODE = "external_current"


class AccountRegistry:
    """Single external current-auth source used by controller phases."""

    def __init__(self) -> None:
        self.mode = EXTERNAL_CURRENT_MODE
        self.account_id = EXTERNAL_CURRENT_ACCOUNT_ID
        self.codex_home = _normalize_codex_home(_default_codex_home())
        self._runtime: dict[str, Any] = {
            "used_calls": 0,
            "last_used_at": None,
            "status": "ready",
            "last_retry_reason": None,
            "last_external_retry_at": None,
        }

    @classmethod
    def external_current(cls) -> "AccountRegistry":
        """Build the only supported auth registry from the current environment."""
        return cls()

    def select_account(self, state: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the external current-auth account entry."""
        return {
            "id": self.account_id,
            "codex_home": self.codex_home,
            "enabled": True,
            "external_switching": True,
            "tags": ["external", "current-auth"],
        }

    def restore_runtime(self, accounts_state: dict[str, Any] | None) -> None:
        """Hydrate counters for the external account from persisted state."""
        if not isinstance(accounts_state, dict):
            return

        by_account = accounts_state.get("by_account", {})
        if not isinstance(by_account, dict):
            return

        snapshot = by_account.get(self.account_id)
        if not isinstance(snapshot, dict):
            return

        for key in (
            "used_calls",
            "last_used_at",
            "status",
            "last_retry_reason",
            "last_external_retry_at",
        ):
            if key in snapshot:
                self._runtime[key] = snapshot[key]
        self._runtime["status"] = "ready"

    def is_ready(self, account_id: str) -> bool:
        """Return True only for the external current-auth account."""
        return account_id == self.account_id

    def record_external_retry(self, account_id: str, reason: str) -> None:
        """Record that external auth should have switched before retry."""
        self._ensure_current_account(account_id)
        self._runtime["status"] = "ready"
        self._runtime["last_retry_reason"] = reason
        self._runtime["last_external_retry_at"] = _utcnow_iso()

    def record_usage(self, account_id: str, calls: int = 1) -> None:
        """Increment the runtime invocation counter."""
        self._ensure_current_account(account_id)
        self._runtime["used_calls"] = int(self._runtime.get("used_calls") or 0) + calls
        self._runtime["last_used_at"] = _utcnow_iso()
        self._runtime["status"] = "ready"

    def get_codex_home(self, account_id: str) -> str:
        """Return the current ``CODEX_HOME`` path."""
        self._ensure_current_account(account_id)
        return self.codex_home

    def get_ids(self) -> list[str]:
        """Return the single logical account ID."""
        return [self.account_id]

    def is_external_current_mode(self) -> bool:
        """Return True because this is the only supported mode."""
        return True

    def uses_external_switching(self, account_id: str) -> bool:
        """Return True for the external current-auth account."""
        return account_id == self.account_id

    def to_state_dict(self) -> dict[str, Any]:
        """Build the ``accounts`` sub-structure for ``state.json``."""
        return {
            "mode": EXTERNAL_CURRENT_MODE,
            "selected_account_id": self.account_id,
            "by_account": {
                self.account_id: {
                    "used_calls": int(self._runtime.get("used_calls") or 0),
                    "last_used_at": self._runtime.get("last_used_at"),
                    "status": "ready",
                    "last_retry_reason": self._runtime.get("last_retry_reason"),
                    "last_external_retry_at": self._runtime.get(
                        "last_external_retry_at"
                    ),
                }
            },
        }

    def _ensure_current_account(self, account_id: str) -> None:
        if account_id != self.account_id:
            raise ValueError(
                f"Unknown auth account {account_id!r}; expected {self.account_id!r}"
            )


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_codex_home() -> Path:
    raw = os.environ.get("CODEX_HOME")
    if raw and raw.strip():
        return Path(raw.strip())
    return Path.home() / ".codex"


def _normalize_codex_home(raw: Any) -> str:
    text = str(raw).strip()
    if not text:
        raise ValueError("CODEX_HOME resolved to an empty path")
    expanded = os.path.expandvars(os.path.expanduser(text))
    return str(Path(expanded))
