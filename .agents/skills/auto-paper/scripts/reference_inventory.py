#!/usr/bin/env python3
"""Build an auto-paper source_index.md from local manuscript materials."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

EXCLUDED_PARTS = {
    ".git",
    ".auto_iterate",
    ".auto_paper",
    "auto_paper_output",
    "outputs",
    "logs",
    "__pycache__",
}

BASE_EXTENSIONS = {
    ".bib": "bibliography",
    ".ris": "bibliography",
    ".enw": "bibliography",
    ".png": "figure",
    ".jpg": "figure",
    ".jpeg": "figure",
    ".webp": "figure",
    ".pdf": "reference_pdf",
    ".txt": "note",
    ".md": "note",
    ".tex": "latex",
    ".cls": "latex",
    ".bst": "latex",
    ".csv": "data",
    ".json": "data",
    ".yaml": "data",
    ".yml": "data",
}

SOURCE_PREFIX = {
    "bibliography": "src_bib",
    "figure": "src_fig",
    "reference_pdf": "src_pdf",
    "note": "src_note",
    "latex": "src_tex",
    "data": "src_data",
}


@dataclass(frozen=True)
class SourceItem:
    source_id: str
    kind: str
    title: str
    path: str
    why_included: str
    used_for: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index local files for an auto-paper writing run."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional files or folders to scan. Defaults to --root.",
    )
    parser.add_argument("--paper-id", default="paper", help="Stable paper slug.")
    parser.add_argument("--artifact-dir", help="Directory for source_index.md.")
    parser.add_argument("--root", default=".", help="Workspace or paper root.")
    parser.add_argument("--include-docs", action="store_true")
    parser.add_argument("--include-pdfs", action="store_true")
    parser.add_argument("--include-tex", action="store_true")
    parser.add_argument("--max-files", type=int, default=300)
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout.")
    return parser.parse_args()


def allowed_extensions(args: argparse.Namespace) -> dict[str, str]:
    extensions = {
        ext: kind
        for ext, kind in BASE_EXTENSIONS.items()
        if kind not in {"note", "reference_pdf", "latex"}
    }
    if args.include_docs:
        extensions.update({".txt": "note", ".md": "note"})
    if args.include_pdfs:
        extensions[".pdf"] = "reference_pdf"
    if args.include_tex:
        extensions.update({".tex": "latex", ".cls": "latex", ".bst": "latex"})
    return extensions


def has_excluded_part(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def iter_candidates(paths: list[Path], extensions: dict[str, str]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for root in paths:
        if not root.exists():
            continue
        iterator = [root] if root.is_file() else root.rglob("*")
        for path in iterator:
            if not path.is_file():
                continue
            if has_excluded_part(path):
                continue
            if path.suffix.lower() not in extensions:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(path)
    return sorted(found, key=lambda item: item.as_posix())


def source_id(kind: str, counts: dict[str, int]) -> str:
    prefix = SOURCE_PREFIX.get(kind, "src_other")
    counts[prefix] = counts.get(prefix, 0) + 1
    return f"{prefix}_{counts[prefix]:03d}"


def describe(kind: str) -> tuple[str, str]:
    if kind == "bibliography":
        return (
            "Bibliography file discovered for citation key inventory.",
            "citation support and citation-key validation",
        )
    if kind == "figure":
        return (
            "Figure asset discovered for manuscript source mapping.",
            "figure/caption consistency and LaTeX graphics validation",
        )
    if kind == "reference_pdf":
        return (
            "Local PDF discovered as a possible reference or exemplar.",
            "reference reading, style learning, or claim support assessment",
        )
    if kind == "latex":
        return (
            "LaTeX source or template file discovered for TeX inventory.",
            "source structure, labels, citations, and patch planning",
        )
    if kind == "note":
        return (
            "Local note discovered for author evidence or writing context.",
            "research dossier and claim-boundary evidence",
        )
    return (
        "Local data/config artifact discovered for source inventory.",
        "result, table, or reproducibility context",
    )


def make_items(
    paths: list[Path],
    extensions: dict[str, str],
    max_files: int,
    root: Path,
) -> list[SourceItem]:
    counts: dict[str, int] = {}
    items: list[SourceItem] = []
    for path in iter_candidates(paths, extensions)[:max_files]:
        kind = extensions[path.suffix.lower()]
        why, used_for = describe(kind)
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = path.resolve().as_posix()
        title = path.stem.replace("_", " ").replace("-", " ")
        items.append(
            SourceItem(
                source_id=source_id(kind, counts),
                kind=kind,
                title=title,
                path=rel,
                why_included=why,
                used_for=used_for,
            )
        )
    return items


def markdown(items: list[SourceItem], args: argparse.Namespace) -> str:
    lines = [
        "# Source Index",
        "",
        f"- `paper_id`: `{args.paper_id}`",
        f"- Indexed items: {len(items)}",
        "",
        "| Source ID | Type | Title/Name | Path | Why Included | Used For |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| {item.source_id} | {item.kind} | {item.title} | {item.path} | "
            f"{item.why_included} | {item.used_for} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    artifact_dir = (
        Path(args.artifact_dir)
        if args.artifact_dir
        else Path("auto_paper_output") / args.paper_id
    )
    scan_paths = [Path(value) for value in args.paths] if args.paths else [root]
    extensions = allowed_extensions(args)
    items = make_items(scan_paths, extensions, args.max_files, root)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    index_path = artifact_dir / "source_index.md"
    index_path.write_text(markdown(items, args), encoding="utf-8")

    if args.json:
        print(json.dumps([asdict(item) for item in items], indent=2))
    else:
        print(f"Wrote {index_path} with {len(items)} indexed items.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
