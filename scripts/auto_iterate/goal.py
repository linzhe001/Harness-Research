"""Goal file parser, validator, and staged activation manager.

The goal file (``docs/auto_iterate_goal.md``) is the operator-facing
specification of the research objective.  The controller consumes a
*parsed* form of this file, not the raw markdown.

Supported goal format
---------------------
Markdown with structured ``**key**: value`` field lines under well-known
headings.  See ``docs/auto_iterate_goal_template.md`` for the canonical
template and ``01_contract_freeze.md`` §5 for the frozen schema.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from .state import atomic_write_json, load_json

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class GoalParseError(Exception):
    """The goal file is missing required fields or is malformed."""


class GoalMetricIdentityError(Exception):
    """The new goal changes primary_metric.name or direction."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_FIELD_RE = re.compile(r"^\s*[-*]\s*\*\*(\w+)\*\*\s*:\s*(.+)$")
_CONSTRAINT_RE = re.compile(r"^\s*[-*]\s+(.+)$")
_HEADING_RE = re.compile(r"^#+\s+(.+)$")
_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.+)$")


def parse(goal_path: str | Path) -> dict[str, Any]:
    """Parse a goal markdown file and return the extracted schema dict.

    Returns a dict with the structure::

        {
            "objective": {
                "primary_metric": {"name": ..., "direction": ..., "target": ...},
                "constraints": [...]
            },
            "patience": {"max_no_improve_rounds": ..., "min_primary_delta": ...},
            "budget": {"max_rounds": ..., "max_gpu_hours": ...},
            "screening_policy": {"enabled": ..., "threshold_pct": ..., "default_steps": ...},
            "initial_hypotheses": [...],
            "forbidden_directions": [...]
        }
    """
    path = Path(goal_path)
    if not path.exists():
        raise GoalParseError(f"Goal file not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    result: dict[str, Any] = {
        "objective": {
            "primary_metric": {},
            "constraints": [],
        },
        "patience": {},
        "budget": {},
        "screening_policy": {},
        "initial_hypotheses": [],
        "forbidden_directions": [],
    }

    current_section: str | None = None
    current_subsection: str | None = None

    for line in lines:
        stripped = line.strip()

        # Track headings
        hm = _HEADING_RE.match(stripped)
        if hm:
            heading = hm.group(1).strip().lower()
            if "primary metric" in heading:
                current_section = "objective"
                current_subsection = "primary_metric"
            elif "constraint" in heading:
                current_section = "objective"
                current_subsection = "constraints"
            elif "patience" in heading:
                current_section = "patience"
                current_subsection = None
            elif "budget" in heading:
                current_section = "budget"
                current_subsection = None
            elif "screening" in heading:
                current_section = "screening_policy"
                current_subsection = None
            elif "initial hypothes" in heading:
                current_section = "initial_hypotheses"
                current_subsection = None
            elif "forbidden" in heading:
                current_section = "forbidden_directions"
                current_subsection = None
            elif "objective" in heading:
                current_section = "objective"
                current_subsection = None
            else:
                # Unknown heading — stop collecting into current section.
                current_section = None
                current_subsection = None
            continue

        if current_section is None:
            continue

        # Field lines: **key**: value
        fm = _FIELD_RE.match(stripped)
        if fm:
            key = fm.group(1).strip()
            raw_val = fm.group(2).strip()
            val = _coerce(raw_val)

            if current_section == "objective" and current_subsection == "primary_metric":
                result["objective"]["primary_metric"][key] = val
            elif current_section in ("patience", "budget", "screening_policy"):
                result[current_section][key] = val
            continue

        # List items for constraints / hypotheses / forbidden
        if current_section == "objective" and current_subsection == "constraints":
            cm = _CONSTRAINT_RE.match(stripped)
            if cm:
                item = cm.group(1).strip()
                if item and not item.startswith("{{") and not item.startswith("<!--"):
                    result["objective"]["constraints"].append(item)
            continue

        if current_section == "initial_hypotheses":
            nm = _NUMBERED_RE.match(stripped)
            if nm:
                item = nm.group(1).strip()
                if item and not item.startswith("{{"):
                    result["initial_hypotheses"].append(item)
            continue

        if current_section == "forbidden_directions":
            cm = _CONSTRAINT_RE.match(stripped)
            if cm:
                item = cm.group(1).strip()
                if item and not item.startswith("{{") and not item.startswith("<!--"):
                    result["forbidden_directions"].append(item)
            continue

    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_METRIC_FIELDS = {"name", "direction", "target"}
_VALID_DIRECTIONS = {"maximize", "minimize"}


def validate(parsed_goal: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []

    pm = parsed_goal.get("objective", {}).get("primary_metric", {})
    for field in _REQUIRED_METRIC_FIELDS:
        if field not in pm or pm[field] is None:
            errors.append(f"objective.primary_metric.{field} is required")
    if pm.get("direction") and pm["direction"] not in _VALID_DIRECTIONS:
        errors.append(
            f"objective.primary_metric.direction must be one of {_VALID_DIRECTIONS}, "
            f"got {pm['direction']!r}"
        )

    patience = parsed_goal.get("patience", {})
    if "max_no_improve_rounds" not in patience:
        errors.append("patience.max_no_improve_rounds is required")

    budget = parsed_goal.get("budget", {})
    if "max_rounds" not in budget:
        errors.append("budget.max_rounds is required")

    sp = parsed_goal.get("screening_policy", {})
    if "enabled" not in sp:
        errors.append("screening_policy.enabled is required")

    return errors


def check_metric_identity(
    parsed_goal: dict[str, Any],
    current_state: dict[str, Any],
) -> list[str]:
    """Return errors if the goal changes the primary metric name or direction.

    Per v7 contract (01§5.5), ``primary_metric.name`` and ``direction``
    must not change across goal activations.
    """
    errors: list[str] = []
    new_pm = parsed_goal.get("objective", {}).get("primary_metric", {})
    old_pm = current_state.get("objective", {}).get("primary_metric", {})

    if old_pm.get("name") and new_pm.get("name") != old_pm["name"]:
        errors.append(
            f"primary_metric.name changed: {old_pm['name']!r} -> {new_pm['name']!r}"
        )
    if old_pm.get("direction") and new_pm.get("direction") != old_pm["direction"]:
        errors.append(
            f"primary_metric.direction changed: {old_pm['direction']!r} -> {new_pm['direction']!r}"
        )
    return errors


# ---------------------------------------------------------------------------
# GoalManager — snapshot and staged activation
# ---------------------------------------------------------------------------

class GoalManager:
    """Manages goal files within ``.auto_iterate/``."""

    def __init__(self, auto_iterate_dir: str | Path) -> None:
        self.root = Path(auto_iterate_dir)
        self.goal_path = self.root / "goal.md"
        self.goal_next_path = self.root / "goal.next.md"

    def snapshot_to(self, source_path: str | Path) -> None:
        """Copy source goal to ``.auto_iterate/goal.md`` (atomic)."""
        self.root.mkdir(parents=True, exist_ok=True)
        src = Path(source_path)
        if not src.exists():
            raise GoalParseError(f"Source goal not found: {src}")
        # Atomic: copy to temp then rename.
        tmp = self.goal_path.with_suffix(".tmp")
        shutil.copy2(str(src), str(tmp))
        tmp.replace(self.goal_path)

    def stage_next(self, source_path: str | Path) -> None:
        """Write a staged goal to ``.auto_iterate/goal.next.md``."""
        self.root.mkdir(parents=True, exist_ok=True)
        src = Path(source_path)
        if not src.exists():
            raise GoalParseError(f"Source goal not found: {src}")
        tmp = self.goal_next_path.with_suffix(".tmp")
        shutil.copy2(str(src), str(tmp))
        tmp.replace(self.goal_next_path)

    def activate_staged(
        self,
        current_state: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate and activate ``goal.next.md`` as the new active goal.

        Returns ``(success, errors)``.  On success, ``goal.next.md`` is
        consumed (deleted) and ``goal.md`` is overwritten.
        """
        if not self.goal_next_path.exists():
            return True, []  # Nothing staged — no-op success.

        parsed = parse(self.goal_next_path)
        errors = validate(parsed)
        if errors:
            return False, errors

        identity_errors = check_metric_identity(parsed, current_state)
        if identity_errors:
            return False, identity_errors

        # Activate: overwrite goal.md and remove goal.next.md.
        self.snapshot_to(self.goal_next_path)
        self.goal_next_path.unlink(missing_ok=True)
        return True, []

    def has_staged(self) -> bool:
        return self.goal_next_path.exists()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce(raw: str) -> Any:
    """Best-effort coercion of a string value to int / float / bool / str."""
    # Remove placeholder markers
    if raw.startswith("{{") and raw.endswith("}}"):
        return raw

    low = raw.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False

    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass

    return raw
