#!/usr/bin/env python3
"""Validate and collect Harness intent-router examples."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from router import ROUTES, route_prompt

DEFAULT_APPROVED = Path(__file__).resolve().parent / "examples" / "approved.jsonl"
DEFAULT_PENDING = Path(__file__).resolve().parent / "examples" / "pending.jsonl"


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{lineno}: example must be an object")
        rows.append(value)
    return rows


def validate_example(row: dict[str, Any], *, strict_route: bool) -> list[str]:
    errors: list[str] = []
    prompt = row.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        errors.append("prompt must be a non-empty string")
    expected_route = row.get("expected_route")
    if expected_route not in ROUTES - {"unknown"}:
        errors.append("expected_route must be a known non-unknown route")
    privacy = row.get("privacy")
    if privacy not in {"raw_ok", "redacted", "paraphrase_only"}:
        errors.append("privacy must be raw_ok, redacted, or paraphrase_only")
    if prompt and expected_route in ROUTES and strict_route:
        observed = route_prompt(prompt)
        if observed["route"] != expected_route:
            errors.append(
                "route mismatch: expected "
                f"{expected_route}, observed {observed['route']}"
            )
    return errors


def command_validate(args: argparse.Namespace) -> int:
    errors: list[str] = []
    for path_text in args.file:
        path = Path(path_text)
        strict = args.strict
        for index, row in enumerate(iter_jsonl(path), 1):
            row_errors = validate_example(row, strict_route=strict)
            errors.extend(f"{path}:{index}: {error}" for error in row_errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print("PASS")
    return 0


def command_add(args: argparse.Namespace) -> int:
    prompt = args.prompt or ""
    observed_route: dict[str, Any] | None = None
    if args.from_last_route:
        last = (
            Path(args.workspace_root)
            / ".harness_hooks"
            / "last_route.json"
        )
        loaded = json.loads(last.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"{last} must contain a route object")
        observed_route = loaded
        prompt = prompt or str(loaded.get("prompt_preview") or "")
    if not prompt.strip():
        raise ValueError("--prompt or --from-last-route is required")
    if args.expected_route not in ROUTES - {"unknown"}:
        raise ValueError("--expected-route must be a known non-unknown route")
    observed_route = observed_route or route_prompt(prompt)
    row = {
        "schema_version": 1,
        "id": f"route-{observed_route['prompt_hash'].split(':', 1)[1][:12]}",
        "created_at": utc_now(),
        "language": args.language,
        "privacy": args.privacy,
        "prompt": prompt,
        "expected_route": args.expected_route,
        "expected_intent": args.expected_intent,
        "observed_route": args.observed_route or observed_route["route"],
        "observed_confidence": observed_route.get("confidence"),
        "reason": args.reason,
    }
    errors = validate_example(row, strict_route=False)
    if errors:
        raise ValueError("; ".join(errors))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    if args.json:
        print(json.dumps({"ok": True, "written": str(output), "example": row}))
    else:
        print(f"ADDED {output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--file", action="append", default=[str(DEFAULT_APPROVED)])
    validate.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Require current router output to match expected_route.",
    )
    validate.set_defaults(func=command_validate)

    add = subparsers.add_parser("add")
    add.add_argument("--prompt", default="")
    add.add_argument("--from-last-route", action="store_true")
    add.add_argument("--workspace-root", default=".")
    add.add_argument("--expected-route", required=True)
    add.add_argument("--expected-intent", default="unknown")
    add.add_argument("--observed-route", default="")
    add.add_argument("--reason", required=True)
    add.add_argument(
        "--privacy",
        default="paraphrase_only",
        choices=["raw_ok", "redacted", "paraphrase_only"],
    )
    add.add_argument("--language", default="unknown")
    add.add_argument("--output", default=str(DEFAULT_PENDING))
    add.add_argument("--json", action="store_true")
    add.set_defaults(func=command_add)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

