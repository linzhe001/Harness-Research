from __future__ import annotations

from harness_contracts import emit, read_hook_event, repo_root, stop_decision


def main() -> int:
    event = read_hook_event()
    root = repo_root(event.get("cwd"))
    decision = stop_decision(root, event)
    if decision:
        emit(decision)
    else:
        emit({"continue": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
