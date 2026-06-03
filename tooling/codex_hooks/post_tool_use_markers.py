from __future__ import annotations

from harness_contracts import (
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
    record_direct_tool_read(root, event)
    record_command_reads(root, command, event)
    mark_tool_activity(root, event)
    mark_pending_for_changes(root, event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
