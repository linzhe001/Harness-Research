#!/usr/bin/env python3
"""Gate external model review calls through Harness review route context."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from redaction import denied_review_path_reason

RUNTIME_SESSION = Path(".harness_hooks/session.json")
REVIEW_TRACE_ROOT = Path(".agents/state/review_traces/code-review")
REQUIRED_SKILL = "code-review"
REQUIRED_INTENT = "code_review_heavy"
REVIEWER_SCRIPTS = {
    "agentic": "agentic_review.py",
    "chat": "external_chat.py",
}
FORBIDDEN_PASSTHROUGH_ARGS = {"--base-url", "--config"}
INPUT_PATH_ARGS = {"--prompt-file", "--system-file", "--task-file"}
OUTPUT_PATH_ARGS = {"--meta-json", "--output", "--request-json", "--trace-json"}
DEFAULT_TIMEOUT_SEC = 900
CHAT_DEFAULT_ARGS = ("--thinking-scope", "none")


class HarnessExternalReviewError(RuntimeError):
    """External review request is not allowed by Harness session policy."""


def repo_root(cwd: str | Path | None = None) -> Path:
    start = Path(cwd or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        if (path / ".git").exists():
            return path
    return start


def load_session(root: Path) -> dict[str, object]:
    path = root / RUNTIME_SESSION
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HarnessExternalReviewError(
            f"invalid Harness session file: {path}"
        ) from exc
    if not isinstance(data, dict):
        raise HarnessExternalReviewError(f"Harness session must be an object: {path}")
    return data


def validate_review_session(root: Path) -> dict[str, object]:
    """Require a `$code-review heavy` Harness route hint."""
    session = load_session(root)
    skill = session.get("candidate_skill") or session.get("active_skill")
    intent = session.get("intent_class")
    if skill != REQUIRED_SKILL or intent != REQUIRED_INTENT:
        raise HarnessExternalReviewError(
            "external model review requires `$code-review heavy` route "
            f"context; got skill={skill!r}, intent_class={intent!r}"
        )
    return session


def _resolve_workspace_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _require_review_trace_output(root: Path, flag: str, value: str) -> None:
    if not value:
        raise HarnessExternalReviewError(f"{flag} requires a non-empty path")
    target = _resolve_workspace_path(root, value)
    allowed = (root / REVIEW_TRACE_ROOT).resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise HarnessExternalReviewError(
            f"{flag} must write under {REVIEW_TRACE_ROOT.as_posix()}; got {value!r}"
        ) from exc
    if target == allowed:
        raise HarnessExternalReviewError(f"{flag} must name a file, not the trace root")


def _require_review_trace_input(root: Path, flag: str, value: str) -> None:
    if not value:
        raise HarnessExternalReviewError(f"{flag} requires a non-empty path")
    target = _resolve_workspace_path(root, value)
    workspace = root.resolve()
    allowed = (root / REVIEW_TRACE_ROOT).resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise HarnessExternalReviewError(
            f"{flag} must read under {REVIEW_TRACE_ROOT.as_posix()}; got {value!r}"
        ) from exc
    if target == allowed:
        raise HarnessExternalReviewError(f"{flag} must name a file, not the trace root")
    if not target.is_file():
        raise HarnessExternalReviewError(f"{flag} input file does not exist: {value!r}")
    rel = target.relative_to(workspace).as_posix()
    denied_reason = denied_review_path_reason(rel)
    if denied_reason:
        raise HarnessExternalReviewError(f"{denied_reason}: {value!r}")


def validate_passthrough_args(root: Path, args: Sequence[str]) -> None:
    index = 0
    while index < len(args):
        item = args[index]
        if item in FORBIDDEN_PASSTHROUGH_ARGS or any(
            item.startswith(f"{flag}=") for flag in FORBIDDEN_PASSTHROUGH_ARGS
        ):
            raise HarnessExternalReviewError(
                f"{item} is not allowed through the network-approved wrapper; "
                "configure providers in tooling/model_api/providers.local.yaml "
                "instead"
            )
        matched_value_flag = False
        for flag in INPUT_PATH_ARGS:
            if item == flag:
                if index + 1 >= len(args):
                    raise HarnessExternalReviewError(f"{flag} requires a path")
                _require_review_trace_input(root, flag, args[index + 1])
                matched_value_flag = True
                break
            if item.startswith(f"{flag}="):
                _require_review_trace_input(root, flag, item.split("=", 1)[1])
                matched_value_flag = True
                break
        if matched_value_flag:
            index += 2 if item in INPUT_PATH_ARGS else 1
            continue
        for flag in OUTPUT_PATH_ARGS:
            if item == flag:
                if index + 1 >= len(args):
                    raise HarnessExternalReviewError(f"{flag} requires a path")
                _require_review_trace_output(root, flag, args[index + 1])
                matched_value_flag = True
                break
            if item.startswith(f"{flag}="):
                _require_review_trace_output(root, flag, item.split("=", 1)[1])
                matched_value_flag = True
                break
        index += 2 if matched_value_flag and item in OUTPUT_PATH_ARGS else 1


def has_passthrough_flag(args: Sequence[str], flag: str) -> bool:
    return any(item == flag or item.startswith(f"{flag}=") for item in args)


def build_reviewer_command(
    root: Path,
    reviewer: str,
    reviewer_args: Sequence[str],
) -> list[str]:
    if reviewer not in REVIEWER_SCRIPTS:
        raise HarnessExternalReviewError(f"unknown reviewer mode: {reviewer!r}")
    validate_passthrough_args(root, reviewer_args)
    script = root / "tooling" / "model_api" / REVIEWER_SCRIPTS[reviewer]
    if not script.exists():
        raise HarnessExternalReviewError(f"missing reviewer script: {script}")
    command_args = list(reviewer_args)
    if reviewer == "chat" and not has_passthrough_flag(
        command_args,
        "--thinking-scope",
    ):
        command_args.extend(CHAT_DEFAULT_ARGS)
    return [sys.executable, script.as_posix(), *command_args]


def run_reviewer(command: Sequence[str], *, timeout_sec: int) -> int:
    try:
        result = subprocess.run(list(command), check=False, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        print(
            f"ERROR: external review timed out after {timeout_sec}s",
            file=sys.stderr,
        )
        return 124
    return int(result.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run Harness external model review only from an active "
            "`$code-review heavy` session."
        )
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=DEFAULT_TIMEOUT_SEC,
        help="Whole-child timeout for the external reviewer process.",
    )
    parser.add_argument(
        "reviewer",
        choices=sorted(REVIEWER_SCRIPTS),
        help="Underlying external reviewer to run.",
    )
    parser.add_argument(
        "reviewer_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the selected reviewer script.",
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Repository root used to find Harness runtime state.",
    )
    args = parser.parse_args(argv)

    try:
        root = repo_root(args.workspace_root)
        if args.timeout_sec <= 0:
            raise HarnessExternalReviewError("--timeout-sec must be positive")
        validate_review_session(root)
        command = build_reviewer_command(root, args.reviewer, args.reviewer_args)
    except HarnessExternalReviewError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return run_reviewer(command, timeout_sec=args.timeout_sec)


if __name__ == "__main__":
    raise SystemExit(main())
