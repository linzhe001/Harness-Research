#!/usr/bin/env python3
"""Create or validate Grill execution-readiness candidate inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from state import (
    atomic_write_json,
    load_json,
    repo_root,
    resolve_path,
    utc_now,
)


def empty_readiness(source: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": utc_now(),
        "source": source,
        "inputs": [],
    }


def validate_readiness(root: Path, data: dict[str, Any]) -> list[str]:
    schema = load_json(root / "schemas" / "execution_readiness.schema.json")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    rendered: list[str] = []
    for error in errors:
        location = "readiness"
        for part in error.path:
            location += f"[{part}]" if isinstance(part, int) else f".{part}"
        rendered.append(f"{location}: {error.message}")
    return rendered


def verify_path_inputs(root: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for index, item in enumerate(data.get("inputs", [])):
        if not isinstance(item, dict) or item.get("kind") != "path":
            continue
        value = item.get("value")
        if not isinstance(value, str) or not value.strip():
            errors.append(f"readiness.inputs[{index}].value: path value required")
            continue
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            errors.append(
                f"readiness.inputs[{index}].value: path does not exist: {value}"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Initialize or validate Grill execution readiness JSON."
    )
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument(
        "--output",
        default=".workflow_supervisor/readiness.json",
        help="Supervisor-owned readiness JSON path.",
    )
    parser.add_argument("--source", default="grill")
    parser.add_argument("--input-json")
    parser.add_argument(
        "--verify-paths",
        action="store_true",
        help="Check that path-kind input values exist.",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--write-readiness",
        action="store_true",
        help="Write supervisor-owned readiness JSON after validation.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root(args.workspace_root)
    output = resolve_path(root, args.output)
    try:
        data = (
            load_json(Path(args.input_json))
            if args.input_json
            else empty_readiness(args.source)
        )
        errors = validate_readiness(root, data)
        if not errors and args.verify_paths:
            errors.extend(verify_path_inputs(root, data))
        if errors:
            raise ValueError("; ".join(errors))
        should_write = args.write_readiness and not args.check and not args.dry_run
        if should_write:
            atomic_write_json(output, data)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        else:
            print(str(exc), file=sys.stderr)
        return 2

    payload = {
        "ok": True,
        "output": str(output),
        "written": should_write,
        "verified_path_count": (
            sum(1 for item in data.get("inputs", []) if item.get("kind") == "path")
            if args.verify_paths
            else 0
        ),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
