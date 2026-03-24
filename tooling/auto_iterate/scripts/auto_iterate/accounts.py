"""Account registry for per-process Codex home selection.

Accounts are defined in a project-supplied YAML registry such as
``tooling/auto_iterate/config/accounts.local.yaml``. The controller picks an
account before each phase launch and sets ``CODEX_HOME`` in the subprocess
environment — it never modifies the global ``~/.codex/auth.json``.

Selection follows the frozen rules in ``02_controller_runtime_plan.md`` §8:

1. Prefer the currently selected account if it is still ``ready``.
2. Otherwise pick an enabled account that is not on cooldown and not
   currently blocked by a transient ``auth_failure``, preferring fewer
   ``used_calls`` and higher ``priority``.
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


_DEFAULT_AUTH_FAILURE_COOLDOWN_SEC = 300


class AccountRegistry:
    """Manages the account pool defined in an accounts YAML file."""

    def __init__(self) -> None:
        self.accounts: list[dict[str, Any]] = []
        # Runtime state: tracks cooldowns and transient status.
        self._runtime: dict[str, dict[str, Any]] = {}
        self._selected_account_id: str | None = None

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

        phase_retry_cap = _phase_retry_cap(state)
        phase_account_attempts = _phase_account_attempts(state)

        def eligible(account_id: str) -> bool:
            if not self.is_ready(account_id):
                return False
            if phase_retry_cap is None:
                return True
            return phase_account_attempts.get(account_id, 0) < phase_retry_cap

        # 1. Prefer current selection if still ready.
        if state:
            current_id = state.get("accounts", {}).get("selected_account_id")
            if current_id and eligible(current_id):
                self._selected_account_id = current_id
                return self._get(current_id)

        # 2. Pick from ready accounts: fewest used_calls, highest priority.
        ready = [a for a in self.accounts if eligible(a["id"])]
        if not ready:
            if phase_retry_cap is None:
                raise NoAccountAvailableError(
                    "All accounts are on cooldown or unavailable"
                )
            raise NoAccountAvailableError(
                "All accounts reached the per-phase retry cap or are unavailable"
            )

        ready.sort(key=lambda a: (
            self._runtime.get(a["id"], {}).get("used_calls", 0),
            -a.get("priority", 0),
        ))
        selected = ready[0]
        self._selected_account_id = selected["id"]
        return selected

    def restore_runtime(self, accounts_state: dict[str, Any] | None) -> None:
        """Hydrate runtime counters and cooldowns from persisted state."""
        if not accounts_state:
            return

        selected_id = accounts_state.get("selected_account_id")
        if selected_id in {a["id"] for a in self.accounts}:
            self._selected_account_id = selected_id

        by_account = accounts_state.get("by_account", {})
        if not isinstance(by_account, dict):
            return

        for aid, snapshot in by_account.items():
            if aid not in self._runtime or not isinstance(snapshot, dict):
                continue
            rt = self._runtime[aid]
            for key in ("cooldown_until", "status", "used_calls", "last_used_at"):
                if key in snapshot:
                    rt[key] = snapshot[key]

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    def is_ready(self, account_id: str) -> bool:
        """Return True if the account is available for use."""
        rt = self._refresh_runtime(account_id)
        if rt is None:
            return False
        if rt.get("status") == "auth_failure":
            return False
        return rt.get("cooldown_until") is None

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
        rt["status"] = "ready"
        if self._selected_account_id == account_id:
            self._selected_account_id = None

    def mark_auth_failure(
        self,
        account_id: str,
        cooldown_sec: int | None = None,
    ) -> str | None:
        """Mark an account as having an auth failure and retry later."""
        rt = self._runtime.setdefault(account_id, {})
        rt["status"] = "auth_failure"
        rt["last_auth_failure_at"] = _utcnow_iso()
        if cooldown_sec is None:
            entry = self._get_or_none(account_id)
            if entry is not None:
                cooldown_sec = entry.get(
                    "auth_failure_cooldown_sec",
                    _DEFAULT_AUTH_FAILURE_COOLDOWN_SEC,
                )
            else:
                cooldown_sec = _DEFAULT_AUTH_FAILURE_COOLDOWN_SEC
        from datetime import timedelta
        rt["cooldown_until"] = (
            datetime.now(timezone.utc) + timedelta(seconds=cooldown_sec)
        ).isoformat()
        if self._selected_account_id == account_id:
            self._selected_account_id = None
        return rt["cooldown_until"]

    def record_usage(self, account_id: str, calls: int = 1) -> None:
        """Increment the used_calls counter for an account."""
        rt = self._runtime.setdefault(account_id, {})
        rt["used_calls"] = rt.get("used_calls", 0) + calls
        rt["last_used_at"] = _utcnow_iso()
        self._selected_account_id = account_id

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
        selected: str | None = self._selected_account_id

        for acc in self.accounts:
            aid = acc["id"]
            rt = self._refresh_runtime(aid) or {}
            by_account[aid] = {
                "used_calls": rt.get("used_calls", 0),
                "last_used_at": rt.get("last_used_at"),
                "cooldown_until": rt.get("cooldown_until"),
                "status": rt.get("status", "ready"),
            }

        if selected is not None and not self.is_ready(selected):
            selected = None

        if selected is None:
            ready = [a for a in self.accounts if self.is_ready(a["id"])]
            if ready:
                ready.sort(key=lambda a: (
                    self._runtime.get(a["id"], {}).get("used_calls", 0),
                    -a.get("priority", 0),
                ))
                selected = ready[0]["id"]

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

    def _refresh_runtime(self, account_id: str) -> dict[str, Any] | None:
        rt = self._runtime.get(account_id)
        if rt is None:
            return None

        cooldown = rt.get("cooldown_until")
        if cooldown is None:
            if rt.get("status") == "auth_failure":
                rt["status"] = "ready"
            return rt

        cooldown_dt: datetime | None = None
        if isinstance(cooldown, str):
            try:
                cooldown_dt = datetime.fromisoformat(cooldown.replace("Z", "+00:00"))
            except ValueError:
                rt["cooldown_until"] = None
        elif isinstance(cooldown, datetime):
            cooldown_dt = cooldown
        else:
            rt["cooldown_until"] = None

        if cooldown_dt is None:
            if rt.get("status") == "auth_failure":
                rt["status"] = "ready"
            return rt

        if cooldown_dt.tzinfo is None:
            cooldown_dt = cooldown_dt.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) >= cooldown_dt:
            rt["cooldown_until"] = None
            if rt.get("status") == "auth_failure":
                rt["status"] = "ready"
        return rt


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _phase_retry_cap(state: dict[str, Any] | None) -> int | None:
    if not isinstance(state, dict):
        return None
    retry_policy = state.get("retry_policy", {})
    if not isinstance(retry_policy, dict):
        return None
    raw = retry_policy.get("max_attempts_per_account")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _phase_account_attempts(state: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(state, dict):
        return {}
    raw = state.get("phase_account_attempts", {})
    if not isinstance(raw, dict):
        return {}

    attempts: dict[str, int] = {}
    for key, value in raw.items():
        try:
            attempts[str(key)] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return attempts
