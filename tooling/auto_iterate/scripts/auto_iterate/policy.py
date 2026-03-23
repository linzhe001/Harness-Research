"""Controller policy configuration loader.

Loads ``tooling/auto_iterate/config/auto_iterate_controller.yaml`` (or a custom path) and
merges with goal-extracted values following the frozen precedence order::

    CLI overrides > validated goal > controller policy config > doc defaults

The ``freeze()`` method produces an immutable dict suitable for
initializing ``state.json`` fields.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Defaults (doc defaults — lowest precedence)
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "timeouts": {
        "plan": 1800,
        "code": 3600,
        "run_screening": 14400,
        "run_full": 28800,
        "eval": 1800,
    },
    "terminate_grace_sec": 30,
    "retry_policy": {
        "max_phase_attempts": 2,
    },
    "budget": {
        "gpu_count": 1,
    },
    "llm_budget": {
        "max_calls": 200,
        "max_cost_usd": 50.0,
    },
    "patience": {
        "max_no_improve_rounds": 5,
        "min_primary_delta": 0.1,
    },
    "event_log": {
        "rotate_bytes": 1_048_576,  # 1 MB
    },
    "heartbeat": {
        "interval_sec": 30,
        "stale_threshold_sec": 120,
    },
}


class PolicyConfig:
    """Load, merge, and freeze controller policy configuration."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = copy.deepcopy(DEFAULT_POLICY)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "PolicyConfig":
        """Load policy from a YAML file, falling back to defaults."""
        pc = cls()
        if config_path is None:
            return pc

        path = Path(config_path)
        if not path.exists():
            return pc

        if yaml is None:
            raise ImportError(
                "PyYAML is required to load YAML config files. "
                "Install with: pip install pyyaml"
            )

        with open(path) as f:
            raw = yaml.safe_load(f)

        if isinstance(raw, dict):
            _deep_merge(pc._data, raw)
        return pc

    def merge_with_goal(self, parsed_goal: dict[str, Any]) -> None:
        """Apply goal-extracted values (higher precedence than config)."""
        goal_patience = parsed_goal.get("patience", {})
        if goal_patience:
            _deep_merge(self._data.setdefault("patience", {}), goal_patience)

        goal_budget = parsed_goal.get("budget", {})
        if goal_budget:
            _deep_merge(self._data.setdefault("budget", {}), goal_budget)

        goal_screening = parsed_goal.get("screening_policy", {})
        if goal_screening:
            self._data["screening_policy"] = goal_screening

    def merge_with_cli(self, cli_overrides: dict[str, Any]) -> None:
        """Apply CLI overrides (highest precedence)."""
        _deep_merge(self._data, cli_overrides)

    def freeze(self) -> dict[str, Any]:
        """Return a deep-copied, read-only snapshot of the merged config."""
        return copy.deepcopy(self._data)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Get a value using dotted notation, e.g. ``'timeouts.plan'``."""
        parts = dotted_key.split(".")
        node: Any = self._data
        for part in parts:
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return default
            if node is None:
                return default
        return node


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (mutates *base*)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
