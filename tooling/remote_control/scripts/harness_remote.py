#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remote_control.ai import (
    get_status,
    override_goal,
    pause_loop,
    read_logs,
    resume_loop,
    start_loop,
    stop_loop,
    tail_events,
)
from remote_control.config import load_config
from remote_control.hints import build_hint
from remote_control.paths import resolve_workspace_root
from remote_control.render import render_hint_text, render_summary_text
from remote_control.result import CommandResult, make_result
from remote_control.summary import build_summary


def _emit(result: CommandResult, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.message)
    return result.exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness_remote", description="Harness remote control wrapper")
    parser.add_argument("--workspace-root", default=".", help="Workspace root (default: current directory)")
    parser.add_argument("--remote-config", default=None, help="Optional remote control config path")

    sub = parser.add_subparsers(dest="command")

    p_summary = sub.add_parser("summary", help="Show workspace summary for future home cards")
    p_summary.add_argument("--json", action="store_true", dest="as_json")

    p_hint = sub.add_parser("hint", help="Show context-aware next-step hints")
    p_hint.add_argument(
        "--context",
        default="default",
        choices=["default", "workspace-switched", "session-switched", "ai-paused", "provider-switched"],
    )
    p_hint.add_argument("--json", action="store_true", dest="as_json")

    p_ai = sub.add_parser("ai", help="Auto-iterate remote commands")
    ai_sub = p_ai.add_subparsers(dest="ai_command")

    p_start = ai_sub.add_parser("start", help="Start a loop")
    p_start.add_argument("--goal", default=None)
    p_start.add_argument("--config", dest="controller_config", default=None)
    p_start.add_argument("--accounts", dest="accounts_config", default=None)
    p_start.add_argument("--max-rounds", type=int, default=None)
    p_start.add_argument("--dry-run", action="store_true")
    p_start.add_argument("--json", action="store_true", dest="as_json")

    p_status = ai_sub.add_parser("status", help="Show loop status")
    p_status.add_argument("--json", action="store_true", dest="as_json")

    p_tail = ai_sub.add_parser("tail", help="Show recent loop events")
    p_tail.add_argument("--lines", type=int, default=None)
    p_tail.add_argument("--json", action="store_true", dest="as_json")

    p_pause = ai_sub.add_parser("pause", help="Pause the loop")
    p_pause.add_argument("--json", action="store_true", dest="as_json")

    p_stop = ai_sub.add_parser("stop", help="Stop the loop")
    p_stop.add_argument("--json", action="store_true", dest="as_json")

    p_resume = ai_sub.add_parser("resume", help="Resume the loop")
    p_resume.add_argument("--json", action="store_true", dest="as_json")

    p_override = ai_sub.add_parser("override", help="Stage a goal override")
    p_override.add_argument("--goal", required=True)
    p_override.add_argument("--json", action="store_true", dest="as_json")

    p_logs = ai_sub.add_parser("logs", help="Read recent runtime logs")
    p_logs.add_argument("--stream", choices=["stdout", "stderr"], default="stdout")
    p_logs.add_argument("--lines", type=int, default=None)
    p_logs.add_argument("--json", action="store_true", dest="as_json")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 100

    workspace_root = resolve_workspace_root(args.workspace_root)
    cfg = load_config(workspace_root, args.remote_config)

    try:
        if args.command == "ai":
            if args.ai_command == "status":
                return _emit(get_status(workspace_root), as_json=args.as_json)
            if args.ai_command == "tail":
                lines = args.lines if args.lines is not None else cfg.default_tail_lines
                return _emit(tail_events(workspace_root, lines=lines), as_json=args.as_json)
            if args.ai_command == "pause":
                return _emit(pause_loop(workspace_root), as_json=args.as_json)
            if args.ai_command == "stop":
                return _emit(stop_loop(workspace_root), as_json=args.as_json)
            if args.ai_command == "resume":
                return _emit(resume_loop(workspace_root, cfg), as_json=args.as_json)
            if args.ai_command == "start":
                return _emit(
                    start_loop(
                        workspace_root,
                        cfg,
                        goal=args.goal,
                        controller_config=args.controller_config,
                        accounts_config=args.accounts_config,
                        max_rounds=args.max_rounds,
                        dry_run=args.dry_run,
                    ),
                    as_json=args.as_json,
                )
            if args.ai_command == "override":
                return _emit(override_goal(workspace_root, goal=args.goal), as_json=args.as_json)
            if args.ai_command == "logs":
                lines = args.lines if args.lines is not None else cfg.default_log_lines
                return _emit(read_logs(workspace_root, stream=args.stream, lines=lines), as_json=args.as_json)
        if args.command == "summary":
            data = build_summary(workspace_root, cfg)
            result = make_result(ok=True, exit_code=0, message=render_summary_text(data), data=data)
            return _emit(result, as_json=args.as_json)
        if args.command == "hint":
            summary = build_summary(workspace_root, cfg)
            data = build_hint(args.context, summary)
            result = make_result(ok=True, exit_code=0, message=render_hint_text(data), data=data)
            return _emit(result, as_json=args.as_json)

        parser.print_help()
        return 100
    except Exception as exc:  # pragma: no cover - wrapper safety net
        result = make_result(ok=False, exit_code=109, message=str(exc))
        return _emit(result, as_json=getattr(args, "as_json", False))


if __name__ == "__main__":
    sys.exit(main())
