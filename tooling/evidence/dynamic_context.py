"""Shared dynamic-context detection helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


CONTEXT_MODEL_VERSION = "dynamic-protocol-v1"
WORKFLOW_MODE_DYNAMIC = "dynamic_context"
WORKFLOW_MODE_STANDARD = "standard"
WORKFLOW_MODE_COMPATIBILITY = "compatibility"
VALID_WORKFLOW_MODES = {
    WORKFLOW_MODE_DYNAMIC,
    WORKFLOW_MODE_STANDARD,
    WORKFLOW_MODE_COMPATIBILITY,
}
DYNAMIC_CONTEXT_DIRS = (
    "docs/10_contract",
    "docs/20_facts",
    "docs/30_evidence",
    "docs/35_protocol",
)


def is_dynamic_context_workspace(workspace_root: Path, state: dict[str, Any]) -> bool:
    """Return True when a workspace has opted into numbered dynamic context."""
    if state.get("workflow_mode") == WORKFLOW_MODE_DYNAMIC:
        return True
    if state.get("context_model_version") == CONTEXT_MODEL_VERSION:
        return True
    return any((workspace_root / relative).exists() for relative in DYNAMIC_CONTEXT_DIRS)


def workflow_mode(state: dict[str, Any]) -> str | None:
    mode = state.get("workflow_mode")
    return mode if isinstance(mode, str) else None


def is_new_workflow_project(workspace_root: Path, state: dict[str, Any]) -> bool:
    """Return True when the state says the project should follow current WF gates."""
    mode = workflow_mode(state)
    if mode == WORKFLOW_MODE_COMPATIBILITY:
        return False
    if mode in {WORKFLOW_MODE_DYNAMIC, WORKFLOW_MODE_STANDARD}:
        return True
    return is_dynamic_context_workspace(workspace_root, state)
