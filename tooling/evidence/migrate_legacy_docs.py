#!/usr/bin/env python3
"""Move old docs/legacy content into the canonical docs/90_legacy archive."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any


def archive_date() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def archive_time() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%H%M%S")


def flattened_name(relative: Path, timestamp: str) -> str:
    stem_parts = [*relative.with_suffix("").parts]
    return "__".join(stem_parts) + f"__{timestamp}{relative.suffix}"


def should_migrate_file(path: Path) -> bool:
    return path.is_file() and path.name != ".gitkeep"


def unique_destination(path: Path, reserved: set[Path] | None = None) -> Path:
    reserved_paths = reserved or set()
    if not path.exists() and path not in reserved_paths:
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}__{index}{suffix}")
        if not candidate.exists() and candidate not in reserved_paths:
            return candidate
    raise RuntimeError(f"could not find unique destination for {path}")


def migration_plan(
    workspace_root: Path,
    *,
    date: str | None = None,
    timestamp: str | None = None,
) -> list[dict[str, str]]:
    workspace = workspace_root.resolve()
    source_root = workspace / "docs" / "legacy"
    if not source_root.exists():
        return [{"action": "skip_missing_source", "path": "docs/legacy"}]
    archive_root = workspace / "docs" / "90_legacy" / (date or archive_date())
    planned: list[dict[str, str]] = []
    reserved_destinations: set[Path] = set()
    stamp = timestamp or archive_time()
    for source in sorted(path for path in source_root.rglob("*") if should_migrate_file(path)):
        relative = source.relative_to(source_root)
        destination = unique_destination(archive_root / flattened_name(relative, stamp), reserved_destinations)
        reserved_destinations.add(destination)
        planned.append(
            {
                "action": "move",
                "source": source.relative_to(workspace).as_posix(),
                "destination": destination.relative_to(workspace).as_posix(),
            }
        )
    if not planned:
        return [{"action": "skip_empty_source", "path": "docs/legacy"}]
    return planned


def migrate_legacy_docs(
    workspace_root: Path,
    *,
    apply: bool = False,
    date: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    actions = migration_plan(workspace, date=date, timestamp=timestamp)
    if apply:
        for action in actions:
            if action.get("action") != "move":
                continue
            source = workspace / action["source"]
            destination = workspace / action["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
    return {
        "ok": True,
        "applied": apply,
        "actions": actions,
        "move_count": sum(1 for action in actions if action.get("action") == "move"),
    }


def print_text(summary: dict[str, Any]) -> None:
    mode = "applied" if summary["applied"] else "dry-run"
    print(f"legacy docs migration {mode}: moves={summary['move_count']}")
    for action in summary["actions"]:
        if action.get("action") == "move":
            print(f"- {action['source']} -> {action['destination']}")
        else:
            print(f"- {action['action']}: {action.get('path', '')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate docs/legacy files into docs/90_legacy/<date>.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="Actually move files. Without this flag the command is a dry run.")
    parser.add_argument("--date", help="Archive date directory, YYYY-MM-DD. Defaults to current UTC date.")
    parser.add_argument("--time", dest="timestamp", help="Archive filename timestamp, HHMMSS. Defaults to current UTC time.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    summary = migrate_legacy_docs(
        args.workspace_root,
        apply=args.apply,
        date=args.date,
        timestamp=args.timestamp,
    )
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print_text(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
