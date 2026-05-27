#!/usr/bin/env python3
"""Extract a structural inventory from a LaTeX root file."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from latex_guard import read_text, resolve_tex_reference, strip_comments

INPUT_RE = re.compile(r"\\(input|include)\{([^{}]+)\}")
SECTION_RE = re.compile(
    r"\\(part|chapter|section|subsection|subsubsection)\*?\{([^{}]+)\}"
)
LABEL_RE = re.compile(r"\\label\{([^{}]+)\}")
REF_RE = re.compile(r"\\(?:ref|autoref|cref|Cref|eqref)\{([^{}]+)\}")
CITE_RE = re.compile(r"\\cite\w*\*?(?:\[[^\]]*\]){0,2}\{([^{}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}")
ENV_RE = re.compile(r"\\(begin|end)\{([^{}]+)\}")


@dataclass(frozen=True)
class Location:
    file: str
    line: int


@dataclass(frozen=True)
class CommandItem:
    value: str
    file: str
    line: int


@dataclass(frozen=True)
class SectionItem:
    level: str
    title: str
    file: str
    line: int


@dataclass(frozen=True)
class EnvironmentItem:
    environment: str
    file: str
    line: int


@dataclass(frozen=True)
class AnchorItem:
    anchor_id: str
    kind: str
    file: str
    line: int
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build auto-paper TeX inventory.")
    parser.add_argument("tex", type=Path, help="Main or wrapper .tex file.")
    parser.add_argument("--output", type=Path, help="Write tex_inventory.json.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    return parser.parse_args()


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def collect_graph(
    tex_path: Path,
    seen: set[Path] | None = None,
) -> tuple[list[Path], dict[str, list[str]]]:
    seen = seen or set()
    resolved = tex_path.resolve()
    if resolved in seen:
        return [], {}
    seen.add(resolved)
    if not resolved.exists():
        return [resolved], {resolved.as_posix(): []}

    files = [resolved]
    graph: dict[str, list[str]] = {resolved.as_posix(): []}
    text = strip_comments(read_text(resolved))
    for match in INPUT_RE.finditer(text):
        child = resolve_tex_reference(resolved.parent, match.group(2).strip())
        child_resolved = child.resolve()
        graph[resolved.as_posix()].append(child_resolved.as_posix())
        child_files, child_graph = collect_graph(child_resolved, seen)
        files.extend(child_files)
        graph.update(child_graph)
    return files, graph


def command_items(
    pattern: re.Pattern[str],
    text: str,
    file_name: str,
) -> list[CommandItem]:
    items: list[CommandItem] = []
    for match in pattern.finditer(text):
        values = [item.strip() for item in match.group(1).split(",")]
        for value in [item for item in values if item]:
            items.append(
                CommandItem(
                    value=value,
                    file=file_name,
                    line=line_number(text, match.start()),
                )
            )
    return items


def section_items(text: str, file_name: str) -> list[SectionItem]:
    return [
        SectionItem(
            level=match.group(1),
            title=match.group(2).strip(),
            file=file_name,
            line=line_number(text, match.start()),
        )
        for match in SECTION_RE.finditer(text)
    ]


def environment_items(
    text: str,
    file_name: str,
    names: set[str],
) -> list[EnvironmentItem]:
    items: list[EnvironmentItem] = []
    for match in ENV_RE.finditer(text):
        if match.group(1) == "begin" and match.group(2) in names:
            items.append(
                EnvironmentItem(
                    environment=match.group(2),
                    file=file_name,
                    line=line_number(text, match.start()),
                )
            )
    return items


def paragraph_anchors(text: str, file_name: str) -> list[AnchorItem]:
    anchors: list[AnchorItem] = []
    offset = 0
    index = 1
    for paragraph in re.split(r"\n\s*\n", text):
        stripped = " ".join(paragraph.split())
        start = text.find(paragraph, offset)
        offset = start + len(paragraph) if start >= 0 else offset
        if len(stripped) < 80:
            continue
        anchors.append(
            AnchorItem(
                anchor_id=f"para_{index:03d}",
                kind="paragraph",
                file=file_name,
                line=line_number(text, max(start, 0)),
                text=stripped[:160],
            )
        )
        index += 1
    return anchors


def section_anchors(sections: list[SectionItem]) -> list[AnchorItem]:
    return [
        AnchorItem(
            anchor_id=f"section_{index:03d}",
            kind=item.level,
            file=item.file,
            line=item.line,
            text=item.title,
        )
        for index, item in enumerate(sections, start=1)
    ]


def build_inventory(tex_path: Path) -> dict[str, object]:
    root = tex_path.resolve().parent
    files, graph = collect_graph(tex_path)
    sections: list[SectionItem] = []
    labels: list[CommandItem] = []
    refs: list[CommandItem] = []
    cites: list[CommandItem] = []
    graphics: list[CommandItem] = []
    tables: list[EnvironmentItem] = []
    equations: list[EnvironmentItem] = []
    anchors: list[AnchorItem] = []

    for path in files:
        if not path.exists():
            continue
        file_name = rel(path, root)
        text = strip_comments(read_text(path))
        current_sections = section_items(text, file_name)
        sections.extend(current_sections)
        labels.extend(command_items(LABEL_RE, text, file_name))
        refs.extend(command_items(REF_RE, text, file_name))
        cites.extend(command_items(CITE_RE, text, file_name))
        graphics.extend(command_items(GRAPHICS_RE, text, file_name))
        tables.extend(
            environment_items(text, file_name, {"table", "tabular", "tabularx"})
        )
        equations.extend(
            environment_items(
                text,
                file_name,
                {"equation", "align", "align*", "gather", "multline"},
            )
        )
        anchors.extend(section_anchors(current_sections))
        anchors.extend(paragraph_anchors(text, file_name))

    missing_inputs = [rel(path, root) for path in files if not path.exists()]
    return {
        "schema_version": "0.1",
        "tex_root": tex_path.resolve().as_posix(),
        "files": [rel(path, root) for path in files if path.exists()],
        "missing_inputs": missing_inputs,
        "input_graph": {
            rel(Path(parent), root): [rel(Path(child), root) for child in children]
            for parent, children in graph.items()
        },
        "sections": [asdict(item) for item in sections],
        "labels": [asdict(item) for item in labels],
        "refs": [asdict(item) for item in refs],
        "cites": [asdict(item) for item in cites],
        "graphics": [asdict(item) for item in graphics],
        "tables": [asdict(item) for item in tables],
        "equations": [asdict(item) for item in equations],
        "line_anchors": [asdict(item) for item in anchors],
    }


def main() -> int:
    args = parse_args()
    if not args.tex.exists():
        raise SystemExit(f"TeX file not found: {args.tex}")
    inventory = build_inventory(args.tex)
    text = json.dumps(inventory, indent=2 if args.pretty else None)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
