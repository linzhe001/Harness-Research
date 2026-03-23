#!/usr/bin/env python3
"""Auto-iterate V7 CLI frontend.

Subcommands: start, status, pause, stop, resume, tail, override.
Exit codes are frozen in 01_contract_freeze.md §8.5.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auto_iterate.controller import (
    EXIT_FATAL,
    EXIT_GOAL_VALIDATION,
    EXIT_INVALID_ARGS,
    EXIT_OK,
    LoopController,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="auto_iterate_ctl",
        description="Auto-iterate V7 controller CLI",
    )
    parser.add_argument(
        "--workspace-root", default=".",
        help="Project workspace root (default: current directory)",
    )
    sub = parser.add_subparsers(dest="command")

    # -- start --------------------------------------------------------------
    p_start = sub.add_parser("start", help="Start a new auto-iterate loop")
    p_start.add_argument("--goal", required=True, help="Path to goal markdown file")
    p_start.add_argument("--config", default=None, help="Controller config YAML")
    p_start.add_argument("--accounts", default=None, help="Accounts registry YAML")
    p_start.add_argument("--tool", default="codex", choices=["codex"])
    p_start.add_argument("--dry-run", action="store_true", help="Skip real Codex invocation")
    p_start.add_argument("--max-rounds", type=int, default=None)

    # -- status -------------------------------------------------------------
    p_status = sub.add_parser("status", help="Show loop status")
    p_status.add_argument("--json", action="store_true", dest="as_json")

    # -- pause --------------------------------------------------------------
    sub.add_parser("pause", help="Pause at next phase boundary")

    # -- stop ---------------------------------------------------------------
    sub.add_parser("stop", help="Stop at next phase boundary")

    # -- resume -------------------------------------------------------------
    p_resume = sub.add_parser("resume", help="Resume an interrupted loop")
    p_resume.add_argument("--config", default=None)
    p_resume.add_argument("--accounts", default=None)

    # -- tail ---------------------------------------------------------------
    p_tail = sub.add_parser("tail", help="Show recent events")
    p_tail.add_argument("--jsonl", action="store_true")
    p_tail.add_argument("--lines", type=int, default=20)

    # -- override -----------------------------------------------------------
    p_override = sub.add_parser("override", help="Stage a goal update")
    p_override.add_argument("--goal", required=True)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return EXIT_INVALID_ARGS

    workspace = Path(args.workspace_root).resolve()
    ctl = LoopController(workspace, dry_run=getattr(args, "dry_run", False))

    if args.command == "start":
        cli_overrides = {}
        if args.max_rounds is not None:
            cli_overrides["budget"] = {"max_rounds": args.max_rounds}
        return ctl.start_loop(
            goal_path=args.goal,
            config_path=args.config,
            accounts_path=args.accounts,
            tool=args.tool,
            cli_overrides=cli_overrides or None,
        )

    elif args.command == "status":
        result = ctl.status(as_json=args.as_json)
        if args.as_json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result)
        return EXIT_OK

    elif args.command == "pause":
        ctl.pause()
        print("Pause signal created. Loop will pause at next phase boundary.")
        return EXIT_OK

    elif args.command == "stop":
        ctl.stop()
        print("Stop signal created. Loop will stop at next phase boundary.")
        return EXIT_OK

    elif args.command == "resume":
        return ctl.resume_loop(
            config_path=args.config,
            accounts_path=args.accounts,
        )

    elif args.command == "tail":
        events = ctl.tail_events(lines=args.lines, jsonl=args.jsonl)
        if args.jsonl:
            for e in events:
                print(json.dumps(e, ensure_ascii=False))
        else:
            for e in events:
                ts = e.get("ts", "")
                event = e.get("event", "")
                phase = e.get("phase_key", "")
                ri = e.get("round_index", "")
                print(f"{ts}  R{ri}  {event:30s} {phase}")
        return EXIT_OK

    elif args.command == "override":
        return ctl.override_goal(args.goal)

    return EXIT_INVALID_ARGS


if __name__ == "__main__":
    sys.exit(main())
