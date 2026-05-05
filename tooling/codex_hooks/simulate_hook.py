from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_BY_EVENT = {
    "UserPromptSubmit": "user_prompt_submit.py",
    "PreToolUse": "pre_tool_use_policy.py",
    "PostToolUse": "post_tool_use_markers.py",
    "Stop": "require_gate_ledger.py",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a Harness Codex hook script with a synthetic event."
    )
    parser.add_argument("event", choices=sorted(SCRIPT_BY_EVENT))
    parser.add_argument(
        "--workspace-root", default=".", help="Repository root used as event cwd."
    )
    parser.add_argument("--event-json", help="Inline JSON event override.")
    parser.add_argument("--event-file", help="Path to JSON event override.")
    args = parser.parse_args()

    root = Path(args.workspace_root).resolve()
    event = {
        "cwd": str(root),
        "hook_event_name": args.event,
        "hookEventName": args.event,
    }
    if args.event_json:
        event.update(json.loads(args.event_json))
    if args.event_file:
        event.update(json.loads(Path(args.event_file).read_text(encoding="utf-8")))

    script = root / "tooling" / "codex_hooks" / SCRIPT_BY_EVENT[args.event]
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(event),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=root,
        check=False,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
