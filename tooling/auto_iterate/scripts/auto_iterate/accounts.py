"""Account registry for Codex auth selection.

The default mode is ``external_current``: the controller points each Codex
subprocess at the current ``CODEX_HOME`` (normally ``~/.codex``) and expects an
external tool such as Windows Cockpit to update ``auth.json`` when quota is
low. In that mode quota/auth failures trigger a fresh Codex process for the
same phase instead of disabling the logical account.

Legacy per-account registries are still accepted for older workspaces. When a
YAML file contains an ``accounts`` list, the controller picks an account before
each phase launch and sets ``CODEX_HOME`` in the subprocess environment.
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


class NoAccountAvailableError(Exception):
    """No enabled account is currently ready."""


_DEFAULT_AUTH_FAILURE_COOLDOWN_SEC = 300
EXTERNAL_CURRENT_ACCOUNT_ID = "external_current"
EXTERNAL_CURRENT_MODE = "external_current"
_EXTERNAL_MODE_ALIASES = {
    EXTERNAL_CURRENT_MODE,
    "current_auth",
    "external_current_auth",
}


class AccountRegistry:
    """Manages the active Codex auth source."""

    def __init__(self, *, mode: str = "configured_pool") -> None:
        self.mode = mode
        self.accounts: list[dict[str, Any]] = []
        # Runtime state: tracks cooldowns and transient status.
        self._runtime: dict[str, dict[str, Any]] = {}
        self._selected_account_id: str | None = None

    @classmethod
    def load(cls, accounts_path: str | Path | None = None) -> "AccountRegistry":
        """Load accounts from YAML, or default to external current auth."""
        if accounts_path is None:
            return cls.external_current()

        path = Path(accounts_path)
        if not path.exists():
            return cls.external_current()

        if yaml is None:
            raise ImportError(
                "PyYAML is required to load account YAML files. "
                "Install with: pip install pyyaml"
            )

        with open(path) as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            return cls.external_current()

        mode = str(raw.get("mode") or raw.get("account_mode") or "").strip().lower()
        if mode in _EXTERNAL_MODE_ALIASES:
            return cls.external_current(
                codex_home=raw.get("codex_home"),
                account_id=raw.get("id"),
            )

        entries = raw.get("accounts")
        if not entries:
            return cls.external_current(
                codex_home=raw.get("codex_home"),
                account_id=raw.get("id"),
            )

        reg = cls(mode="configured_pool")
        for entry in entries:
            if isinstance(entry, dict) and entry.get("enabled", True):
                normalized = dict(entry)
                if "codex_home" in normalized:
                    normalized["codex_home"] = _normalize_codex_home(
                        normalized["codex_home"]
                    )
                reg.accounts.append(normalized)
                reg._runtime[normalized["id"]] = {
                    "cooldown_until": None,
                    "status": "ready",
                    "used_calls": 0,
                }
        return reg

    @classmethod
    def external_current(
        cls,
        *,
        codex_home: Any = None,
        account_id: Any = None,
    ) -> "AccountRegistry":
        """Build a registry backed by the current externally managed auth."""
        reg = cls(mode=EXTERNAL_CURRENT_MODE)
        aid = str(account_id or EXTERNAL_CURRENT_ACCOUNT_ID)
        reg.accounts.append({
            "id": aid,
            "codex_home": _normalize_codex_home(codex_home or _default_codex_home()),
            "enabled": True,
            "priority": 100,
            "external_switching": True,
            "tags": ["external", "current-auth"],
        })
        reg._runtime[aid] = {
            "cooldown_until": None,
            "status": "ready",
            "used_calls": 0,
        }
        reg._selected_account_id = aid
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
            if self.uses_external_switching(account_id):
                return True
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
        if self.uses_external_switching(account_id):
            rt["cooldown_until"] = None
            rt["last_cooldown_reason"] = reason
            rt["last_external_retry_at"] = _utcnow_iso()
            rt["status"] = "ready"
            self._selected_account_id = account_id
            return

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
        if self.uses_external_switching(account_id):
            rt["cooldown_until"] = None
            rt["last_external_retry_at"] = rt["last_auth_failure_at"]
            rt["status"] = "ready"
            self._selected_account_id = account_id
            return None

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

    def is_external_current_mode(self) -> bool:
        """Return True when auth switching is owned by an external tool."""
        return self.mode == EXTERNAL_CURRENT_MODE

    def uses_external_switching(self, account_id: str) -> bool:
        """Return True if the account follows externally updated auth."""
        entry = self._get_or_none(account_id)
        return bool(entry and entry.get("external_switching"))

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
                "last_cooldown_reason": rt.get("last_cooldown_reason"),
                "last_external_retry_at": rt.get("last_external_retry_at"),
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
            "mode": self.mode,
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


def _default_codex_home() -> Path:
    raw = os.environ.get("CODEX_HOME")
    if raw and raw.strip():
        return Path(raw.strip())
    return Path.home() / ".codex"


def _normalize_codex_home(raw: Any) -> str:
    text = str(raw).strip()
    if not text:
        raise ValueError("codex_home must not be empty")
    expanded = os.path.expandvars(os.path.expanduser(text))
    return str(Path(expanded))


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
