#!/usr/bin/env python3
"""Scan manuscript materials for figure and table requirement cues."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

TEXT_EXTENSIONS = {".md", ".txt", ".tex", ".rst"}
PDF_EXTENSIONS = {".pdf"}
CUE_PATTERNS = (
    r"\bfig(?:ure)?\.?\s*\d*",
    r"\btable\s*\d*",
    r"\bdiagram\b",
    r"\bchart\b",
    r"\bplot\b",
    r"\bpanel\s+[a-z]\b",
    r"\bvisuali[sz]ation\b",
    r"\bschematic\b",
    r"图表",
    r"图\s*\d+",
    r"表格",
    r"架构图",
    r"路线图",
    r"热力图",
    r"雷达图",
    r"气泡图",
    r"三联图",
    r"四联图",
    r"示意图",
    r"可视化",
)
TABLE_PATTERNS = (
    r"\btable\s*\d*",
    r"表格",
    r"补充表",
)


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    path: Path


@dataclass(frozen=True)
class FigureCue:
    item_id: str
    source_id: str
    source_location: str
    cue_text: str
    figure_or_table_need: str
    evidence_type: str
    suggested_artifact: str
    owner: str
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan local manuscript materials for figure/table cues."
    )
    parser.add_argument("paths", nargs="*", help="Files or folders to scan.")
    parser.add_argument("--paper-id", default="paper")
    parser.add_argument("--artifact-dir", help="Directory for output artifact.")
    parser.add_argument("--root", default=".", help="Workspace root.")
    parser.add_argument(
        "--source-index",
        help="Optional source_index.md. Used when paths are omitted.",
    )
    parser.add_argument("--max-candidates", type=int, default=80)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def split_table_line(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells if cell)


def source_refs_from_index(path: Path, root: Path) -> list[SourceRef]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for index, line in enumerate(lines):
        if "|" not in line or index + 1 >= len(lines):
            continue
        header = [cell.lower() for cell in split_table_line(line)]
        separator = split_table_line(lines[index + 1])
        if "source id" not in header or "path" not in header:
            continue
        if not is_separator(separator):
            continue
        source_id_index = header.index("source id")
        path_index = header.index("path")
        refs: list[SourceRef] = []
        for raw in lines[index + 2 :]:
            if "|" not in raw:
                break
            cells = split_table_line(raw)
            if len(cells) <= max(source_id_index, path_index):
                continue
            source_path = Path(cells[path_index])
            if not source_path.is_absolute():
                source_path = root / source_path
            refs.append(SourceRef(cells[source_id_index], source_path))
        return refs
    return []


def iter_input_files(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")
        iterator = [path] if path.is_file() else path.rglob("*")
        for candidate in iterator:
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in TEXT_EXTENSIONS | PDF_EXTENSIONS:
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(candidate)
    return sorted(found, key=lambda item: item.as_posix())


def read_pdf_text(path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", path.as_posix(), "-"],
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pdftotext is required to scan PDF figure cues") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"pdftotext failed for {path}: {exc.stderr.strip()}"
        ) from exc
    return result.stdout


def read_source_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return read_pdf_text(path)
    if suffix in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported source type for figure scan: {path}")


def has_match(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def classify_need(text: str) -> str:
    if has_match(TABLE_PATTERNS, text):
        return "table"
    return "figure"


def escape_cell(value: str) -> str:
    return " ".join(value.replace("|", "\\|").split())


def scan_sources(
    refs: list[SourceRef],
    root: Path,
    max_candidates: int,
) -> list[FigureCue]:
    cues: list[FigureCue] = []
    for ref in refs:
        text = read_source_text(ref.path)
        try:
            display_path = ref.path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            display_path = ref.path.as_posix()
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not has_match(CUE_PATTERNS, line):
                continue
            item_id = f"fig_need_{len(cues) + 1:03d}"
            cues.append(
                FigureCue(
                    item_id=item_id,
                    source_id=ref.source_id,
                    source_location=f"{display_path}:{line_number}",
                    cue_text=line.strip()[:240],
                    figure_or_table_need=classify_need(line),
                    evidence_type="source_material_cue",
                    suggested_artifact="figure_contract.md",
                    owner="auto-paper-figure",
                    status="candidate",
                )
            )
            if len(cues) >= max_candidates:
                return cues
    return cues


def markdown(cues: list[FigureCue], paper_id: str) -> str:
    lines = [
        "# Figure Requirement Scan",
        "",
        f"- `paper_id`: `{paper_id}`",
        f"- Candidate cues: {len(cues)}",
        "",
        "| item_id | source_id | source_location | cue_text | "
        "figure_or_table_need | evidence_type | suggested_artifact | owner | status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cue in cues:
        lines.append(
            "| "
            + " | ".join(
                escape_cell(value)
                for value in (
                    cue.item_id,
                    cue.source_id,
                    cue.source_location,
                    cue.cue_text,
                    cue.figure_or_table_need,
                    cue.evidence_type,
                    cue.suggested_artifact,
                    cue.owner,
                    cue.status,
                )
            )
            + " |"
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
    if args.paths:
        files = iter_input_files([Path(value) for value in args.paths])
        refs = [
            SourceRef(f"src_input_{index:03d}", path)
            for index, path in enumerate(files, 1)
        ]
    else:
        source_index = (
            Path(args.source_index)
            if args.source_index
            else artifact_dir / "source_index.md"
        )
        refs = [
            ref
            for ref in source_refs_from_index(source_index, root)
            if ref.path.suffix.lower() in TEXT_EXTENSIONS | PDF_EXTENSIONS
        ]
    cues = scan_sources(refs, root, args.max_candidates)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    output_path = artifact_dir / "figure_requirement_scan.md"
    output_path.write_text(markdown(cues, args.paper_id), encoding="utf-8")

    if args.json:
        print(json.dumps([asdict(cue) for cue in cues], indent=2))
    else:
        print(f"Wrote {output_path} with {len(cues)} candidate cues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
