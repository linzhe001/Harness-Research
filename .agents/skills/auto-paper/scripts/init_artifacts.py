#!/usr/bin/env python3
"""Initialize an auto-paper artifact directory from bundled templates."""

from __future__ import annotations

import argparse
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize auto-paper artifacts.")
    parser.add_argument("--paper-id", help="Stable ASCII paper slug.")
    parser.add_argument(
        "--artifact-dir",
        help="Output artifact directory. Defaults to auto_paper_output/<paper-id>.",
    )
    parser.add_argument(
        "--workflow",
        default="rewrite_existing_latex",
        choices=("rewrite_existing_latex", "build_from_materials"),
    )
    parser.add_argument("--force", action="store_true", help="Overwrite files.")
    parser.add_argument("--list", action="store_true", help="List template files.")
    return parser.parse_args()


def render(text: str, replacements: dict[str, str]) -> str:
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def template_files() -> list[Path]:
    return sorted(path for path in TEMPLATE_DIR.iterdir() if path.is_file())


def initialize(
    paper_id: str,
    artifact_dir: Path,
    workflow: str,
    force: bool,
) -> list[Path]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    replacements = {
        "paper_id": paper_id,
        "artifact_dir": artifact_dir.as_posix(),
        "workflow": workflow,
    }
    written: list[Path] = []
    for template in template_files():
        target = artifact_dir / template.name
        if target.exists() and not force:
            continue
        text = template.read_text(encoding="utf-8")
        target.write_text(render(text, replacements), encoding="utf-8")
        written.append(target)
    return written


def main() -> int:
    args = parse_args()
    if args.list:
        for path in template_files():
            print(path.name)
        return 0
    if not args.paper_id:
        raise SystemExit("--paper-id is required unless --list is used")
    artifact_dir = (
        Path(args.artifact_dir)
        if args.artifact_dir
        else Path("auto_paper_output") / args.paper_id
    )
    written = initialize(args.paper_id, artifact_dir, args.workflow, args.force)
    print(f"Wrote {len(written)} template artifacts to {artifact_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
