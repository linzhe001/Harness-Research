"""External current-auth configuration for Codex auto-iterate.

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

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]


class AccountConfigError(ValueError):
    """The external auth configuration is invalid."""


EXTERNAL_CURRENT_ACCOUNT_ID = "external_current"
EXTERNAL_CURRENT_MODE = "external_current"
_EXTERNAL_MODE_ALIASES = {
    EXTERNAL_CURRENT_MODE,
    "current_auth",
    "external_current_auth",
}


class AccountRegistry:
    """Single external current-auth source used by controller phases."""

    def __init__(
        self,
        *,
        codex_home: Any = None,
        account_id: Any = None,
    ) -> None:
        self.mode = EXTERNAL_CURRENT_MODE
        self.account_id = str(account_id or EXTERNAL_CURRENT_ACCOUNT_ID)
        raw_codex_home = _default_codex_home() if codex_home is None else codex_home
        self.codex_home = _normalize_codex_home(raw_codex_home)
        self._runtime: dict[str, Any] = {
            "used_calls": 0,
            "last_used_at": None,
            "status": "ready",
            "last_retry_reason": None,
            "last_external_retry_at": None,
        }

    @classmethod
    def load(cls, accounts_path: str | Path | None = None) -> "AccountRegistry":
        """Load optional external current-auth YAML.

        ``accounts:`` lists from the removed controller-owned account pool are
        rejected instead of silently ignored.
        """
        if accounts_path is None:
            return cls.external_current()

        path = Path(accounts_path)
        if not path.exists():
            raise AccountConfigError(f"External auth config not found: {path}")

        if yaml is None:
            raise ImportError(
                "PyYAML is required to load account YAML files. "
                "Install with: pip install pyyaml"
            )

        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if raw is None:
            return cls.external_current()
        if not isinstance(raw, dict):
            raise AccountConfigError(
                "External auth config must be a YAML mapping with mode/codex_home"
            )
        if "accounts" in raw:
            raise AccountConfigError(
                "Legacy auto-iterate account pools are no longer supported. "
                "Remove the accounts: list and use mode: external_current."
            )

        mode = str(raw.get("mode") or raw.get("account_mode") or EXTERNAL_CURRENT_MODE)
        mode = mode.strip().lower()
        if mode not in _EXTERNAL_MODE_ALIASES:
            raise AccountConfigError(
                f"Unsupported auth mode {mode!r}; expected external_current"
            )

        return cls.external_current(
            codex_home=raw.get("codex_home"),
            account_id=raw.get("id"),
        )

    @classmethod
    def external_current(
        cls,
        *,
        codex_home: Any = None,
        account_id: Any = None,
    ) -> "AccountRegistry":
        """Build the only supported auth registry."""
        return cls(codex_home=codex_home, account_id=account_id)

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
            raise AccountConfigError(
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
        raise AccountConfigError("codex_home must not be empty")
    expanded = os.path.expandvars(os.path.expanduser(text))
    return str(Path(expanded))
