from __future__ import annotations

from harness_contracts import (
    consume_gate_ledger_notice,
    emit,
    mark_pending_for_changes,
    mark_tool_activity,
    read_hook_event,
    record_command_reads,
    record_direct_tool_read,
    repo_root,
    tool_text,
)


def main() -> int:
    event = read_hook_event()
    root = repo_root(event.get("cwd"))
    command = tool_text(event)
    recorded = record_direct_tool_read(root, event)
    recorded.extend(record_command_reads(root, command, event))
    mark_tool_activity(root, event)
    pending = mark_pending_for_changes(root, event)
    notes = []
    if recorded:
        notes.append("Recorded Harness read set files: " + ", ".join(recorded))
    if consume_gate_ledger_notice(root, pending):
        notes.append("Harness Gate ledger will be required before final response.")
    if notes:
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "\n".join(notes),
                }
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
