"""Account registry for per-process Codex home selection.

Accounts are defined in ``config/auto_iterate_accounts.yaml``.  The
controller picks an account before each phase launch and sets
``CODEX_HOME`` in the subprocess environment — it never modifies
the global ``~/.codex/auth.json``.

Selection follows the frozen rules in ``02_controller_runtime_plan.md`` §8:

1. Prefer the currently selected account if it is still ``ready``.
2. Otherwise pick an enabled account that is not on cooldown and not
   marked ``auth_failure``, preferring fewer ``used_calls`` and higher
   ``priority``.
3. If no account is available, halt with ``waiting_for_account``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]


class NoAccountAvailableError(Exception):
    """No enabled account is currently ready."""


class AccountRegistry:
    """Manages the account pool defined in an accounts YAML file."""

    def __init__(self) -> None:
        self.accounts: list[dict[str, Any]] = []
        # Runtime state: tracks cooldowns and transient status.
        self._runtime: dict[str, dict[str, Any]] = {}

    @classmethod
    def load(cls, accounts_path: str | Path | None = None) -> "AccountRegistry":
        """Load accounts from a YAML file.  Returns an empty registry if
        the path is ``None`` or does not exist."""
        reg = cls()
        if accounts_path is None:
            return reg

        path = Path(accounts_path)
        if not path.exists():
            return reg

        if yaml is None:
            raise ImportError(
                "PyYAML is required to load account YAML files. "
                "Install with: pip install pyyaml"
            )

        with open(path) as f:
            raw = yaml.safe_load(f)

        if isinstance(raw, dict) and "accounts" in raw:
            for entry in raw["accounts"]:
                if isinstance(entry, dict) and entry.get("enabled", True):
                    reg.accounts.append(entry)
                    reg._runtime[entry["id"]] = {
                        "cooldown_until": None,
                        "status": "ready",
                        "used_calls": 0,
                    }
        return reg

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select_account(self, state: dict[str, Any] | None = None) -> dict[str, Any]:
        """Select the best available account and return its registry entry.

        Raises ``NoAccountAvailableError`` if nothing is ready.
        """
        if not self.accounts:
            raise NoAccountAvailableError("No accounts configured")

        # 1. Prefer current selection if still ready.
        if state:
            current_id = state.get("accounts", {}).get("selected_account_id")
            if current_id and self.is_ready(current_id):
                return self._get(current_id)

        # 2. Pick from ready accounts: fewest used_calls, highest priority.
        ready = [a for a in self.accounts if self.is_ready(a["id"])]
        if not ready:
            raise NoAccountAvailableError("All accounts are on cooldown or unavailable")

        ready.sort(key=lambda a: (
            self._runtime.get(a["id"], {}).get("used_calls", 0),
            -a.get("priority", 0),
        ))
        return ready[0]

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    def is_ready(self, account_id: str) -> bool:
        """Return True if the account is available for use."""
        rt = self._runtime.get(account_id)
        if rt is None:
            return False
        if rt.get("status") == "auth_failure":
            return False
        cooldown = rt.get("cooldown_until")
        if cooldown is not None:
            now = datetime.now(timezone.utc)
            if isinstance(cooldown, str):
                cooldown = datetime.fromisoformat(cooldown.replace("Z", "+00:00"))
            if now < cooldown:
                return False
        return True

    def mark_cooldown(
        self,
        account_id: str,
        reason: str,
        cooldown_sec: int | None = None,
    ) -> None:
        """Put an account on cooldown."""
        rt = self._runtime.setdefault(account_id, {})
        if cooldown_sec is None:
            # Use the account's own cooldown_sec, or default 1800.
            entry = self._get_or_none(account_id)
            cooldown_sec = entry.get("cooldown_sec", 1800) if entry else 1800

        from datetime import timedelta
        rt["cooldown_until"] = (
            datetime.now(timezone.utc) + timedelta(seconds=cooldown_sec)
        ).isoformat()
        rt["last_cooldown_reason"] = reason

    def mark_auth_failure(self, account_id: str) -> None:
        """Mark an account as having an auth failure (not auto-recoverable)."""
        rt = self._runtime.setdefault(account_id, {})
        rt["status"] = "auth_failure"

    def record_usage(self, account_id: str, calls: int = 1) -> None:
        """Increment the used_calls counter for an account."""
        rt = self._runtime.setdefault(account_id, {})
        rt["used_calls"] = rt.get("used_calls", 0) + calls

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_codex_home(self, account_id: str) -> str:
        """Return the ``codex_home`` path for the given account."""
        entry = self._get(account_id)
        return entry["codex_home"]

    def get_ids(self) -> list[str]:
        """Return all account IDs."""
        return [a["id"] for a in self.accounts]

    def to_state_dict(self) -> dict[str, Any]:
        """Build the ``accounts`` sub-structure for ``state.json``."""
        by_account: dict[str, Any] = {}
        selected: str | None = None

        for acc in self.accounts:
            aid = acc["id"]
            rt = self._runtime.get(aid, {})
            by_account[aid] = {
                "used_calls": rt.get("used_calls", 0),
                "last_used_at": rt.get("last_used_at"),
                "cooldown_until": rt.get("cooldown_until"),
                "status": rt.get("status", "ready"),
            }
            if selected is None and self.is_ready(aid):
                selected = aid

        return {
            "selected_account_id": selected,
            "by_account": by_account,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get(self, account_id: str) -> dict[str, Any]:
        for a in self.accounts:
            if a["id"] == account_id:
                return a
        raise NoAccountAvailableError(f"Account {account_id!r} not found")

    def _get_or_none(self, account_id: str) -> dict[str, Any] | None:
        for a in self.accounts:
            if a["id"] == account_id:
                return a
        return None
