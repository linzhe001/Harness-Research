from __future__ import annotations

from harness_contracts import (
    block_pre_tool,
    emit,
    hook_block,
    read_hook_event,
    repo_root,
)


def main() -> int:
    event = read_hook_event()
    root = repo_root(event.get("cwd"))
    reason = block_pre_tool(root, event)
    if reason:
        emit(hook_block("PreToolUse", reason))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
