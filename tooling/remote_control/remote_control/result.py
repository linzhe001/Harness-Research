from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EXIT_CODE_TO_CATEGORY = {
    0: "ok",
    100: "invalid_args",
    101: "invalid_state",
    102: "lock_conflict",
    103: "goal_validation_failed",
    104: "runtime_invocation_failed",
    105: "manual_action_required",
    106: "budget_exhausted",
    107: "waiting_for_account",
    108: "resumable_interruption",
    109: "fatal",
}

DEFAULT_CATEGORY_MESSAGES = {
    "ok": "Command completed successfully.",
    "invalid_args": "The command arguments are invalid.",
    "invalid_state": "The controller state is invalid.",
    "lock_conflict": "Another loop appears to hold the controller lock.",
    "goal_validation_failed": "The goal file failed validation.",
    "runtime_invocation_failed": "The runtime invocation failed.",
    "manual_action_required": "Manual action is required before the loop can continue.",
    "budget_exhausted": "The loop budget has been exhausted.",
    "waiting_for_account": "No usable Codex account is currently available.",
    "resumable_interruption": "The loop was interrupted but can be resumed.",
    "fatal": "A fatal controller error occurred.",
}


def category_for_exit_code(exit_code: int) -> str:
    return EXIT_CODE_TO_CATEGORY.get(exit_code, "fatal")


def default_message_for_category(category: str) -> str:
    return DEFAULT_CATEGORY_MESSAGES.get(category, DEFAULT_CATEGORY_MESSAGES["fatal"])


@dataclass
class CommandResult:
    ok: bool
    category: str
    message: str
    exit_code: int
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "category": self.category,
            "message": self.message,
            "data": self.data,
            "exit_code": self.exit_code,
        }


def make_result(
    *,
    ok: bool,
    exit_code: int,
    message: str | None = None,
    data: dict[str, Any] | None = None,
) -> CommandResult:
    category = category_for_exit_code(exit_code)
    return CommandResult(
        ok=ok,
        category=category,
        message=message or default_message_for_category(category),
        exit_code=exit_code,
        data=data or {},
    )
