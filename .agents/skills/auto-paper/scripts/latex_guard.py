#!/usr/bin/env python3
"""Static guard checks for auto-paper LaTeX patching."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

GRAPHIC_EXTENSIONS = [
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".eps",
    ".tif",
    ".tiff",
]
INPUT_RE = re.compile(r"\\(?:input|include)\{([^{}]+)\}")
BIB_RE = re.compile(r"\\bibliography\{([^{}]+)\}")


@dataclass(frozen=True)
class Finding:
    severity: str
    check: str
    message: str
    line: int | None = None
    file: str | None = None


@dataclass(frozen=True)
class TexDocument:
    root: Path
    files: list[Path]
    text: str


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def strip_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        cut = None
        for match in re.finditer(r"(?<!\\)%", line):
            cut = match.start()
            break
        lines.append(line if cut is None else line[:cut])
    return "\n".join(lines)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def resolve_tex_reference(base: Path, raw: str) -> Path:
    path = (base / raw).expanduser()
    if path.suffix:
        return path
    return path.with_suffix(".tex")


def collect_tex(path: Path, seen: set[Path] | None = None) -> list[Path]:
    seen = seen or set()
    resolved = path.resolve()
    if resolved in seen:
        return []
    seen.add(resolved)
    if not resolved.exists():
        return [resolved]

    files = [resolved]
    text = strip_comments(read_text(resolved))
    for match in INPUT_RE.finditer(text):
        child = resolve_tex_reference(resolved.parent, match.group(1).strip())
        files.extend(collect_tex(child, seen))
    return files


def load_document(root: Path) -> TexDocument:
    files = collect_tex(root)
    chunks: list[str] = []
    for path in files:
        if not path.exists():
            continue
        rel = path.as_posix()
        chunks.append(f"\n% AUTO_PAPER_FILE_BEGIN {rel}\n")
        chunks.append(strip_comments(read_text(path)))
        chunks.append(f"\n% AUTO_PAPER_FILE_END {rel}\n")
    return TexDocument(root=root.resolve(), files=files, text="\n".join(chunks))


def parse_bib_keys(paths: list[Path]) -> set[str]:
    keys: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        keys.update(re.findall(r"@\w+\s*\{\s*([^,\s]+)", read_text(path)))
    return keys


def discover_bib_paths(document: TexDocument) -> list[Path]:
    paths: list[Path] = []
    for match in BIB_RE.finditer(document.text):
        for raw in match.group(1).split(","):
            item = raw.strip()
            if not item:
                continue
            candidate = document.root.parent / item
            if not candidate.suffix:
                candidate = candidate.with_suffix(".bib")
            paths.append(candidate.resolve())
    return paths


def find_file_at_offset(document: TexDocument, offset: int) -> str | None:
    marker = "% AUTO_PAPER_FILE_BEGIN "
    before = document.text[:offset]
    index = before.rfind(marker)
    if index < 0:
        return None
    line = before[index:].splitlines()[0]
    return line.replace(marker, "").strip() or None


def add(
    findings: list[Finding],
    severity: str,
    check: str,
    message: str,
    document: TexDocument,
    offset: int | None = None,
) -> None:
    findings.append(
        Finding(
            severity=severity,
            check=check,
            message=message,
            line=None if offset is None else line_number(document.text, offset),
            file=None if offset is None else find_file_at_offset(document, offset),
        )
    )


def check_document_markers(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    if "\\begin{document}" not in document.text:
        add(findings, "error", "document", "Missing \\begin{document}.", document)
    if "\\end{document}" not in document.text:
        add(findings, "error", "document", "Missing \\end{document}.", document)
    return findings


def check_missing_inputs(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    for path in document.files:
        if not path.exists():
            findings.append(
                Finding(
                    severity="error",
                    check="input",
                    message=f"Input/include file not found: {path}",
                    file=path.as_posix(),
                )
            )
    return findings


def check_merge_markers(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    for marker in ("<<<<<<<", "=======", ">>>>>>>"):
        for match in re.finditer(re.escape(marker), document.text):
            add(
                findings,
                "error",
                "merge-marker",
                f"Found merge/conflict marker {marker}.",
                document,
                match.start(),
            )
    return findings


def check_braces(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    stack: list[int] = []
    for match in re.finditer(r"(?<!\\)[{}]", document.text):
        token = match.group(0)
        if token == "{":
            stack.append(match.start())
        elif stack:
            stack.pop()
        else:
            add(
                findings,
                "error",
                "braces",
                "Closing brace without matching opening brace.",
                document,
                match.start(),
            )
    for offset in stack[-10:]:
        add(
            findings,
            "error",
            "braces",
            "Opening brace without matching closing brace.",
            document,
            offset,
        )
    return findings


def check_environments(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    stack: list[tuple[str, int]] = []
    for match in re.finditer(r"\\(begin|end)\{([^{}]+)\}", document.text):
        action, env = match.group(1), match.group(2)
        if action == "begin":
            stack.append((env, match.start()))
            continue
        if not stack:
            add(
                findings,
                "error",
                "environment",
                f"\\end{{{env}}} has no matching begin.",
                document,
                match.start(),
            )
            continue
        last_env, last_offset = stack.pop()
        if last_env != env:
            last_line = line_number(document.text, last_offset)
            add(
                findings,
                "error",
                "environment",
                f"\\end{{{env}}} closes \\begin{{{last_env}}} from line "
                f"{last_line}.",
                document,
                match.start(),
            )
    for env, offset in stack[-10:]:
        add(
            findings,
            "error",
            "environment",
            f"\\begin{{{env}}} is not closed.",
            document,
            offset,
        )
    return findings


def check_labels_and_refs(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    labels: dict[str, int] = {}
    for match in re.finditer(r"\\label\{([^{}]+)\}", document.text):
        key = match.group(1)
        if key in labels:
            add(
                findings,
                "error",
                "label",
                f"Duplicate label `{key}` also defined at line {labels[key]}.",
                document,
                match.start(),
            )
        else:
            labels[key] = line_number(document.text, match.start())

    ref_pattern = re.compile(r"\\(?:ref|autoref|cref|Cref|eqref)\{([^{}]+)\}")
    for match in ref_pattern.finditer(document.text):
        keys = [item.strip() for item in match.group(1).split(",")]
        for key in [item for item in keys if item]:
            if key not in labels:
                add(
                    findings,
                    "warning",
                    "reference",
                    f"Reference `{key}` has no matching label.",
                    document,
                    match.start(),
                )
    return findings


def check_citations(document: TexDocument, bib_paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    bib_keys = parse_bib_keys(bib_paths)
    cite_pattern = re.compile(r"\\cite\w*\*?(?:\[[^\]]*\]){0,2}\{([^{}]+)\}")
    used: set[str] = set()
    for match in cite_pattern.finditer(document.text):
        keys = [item.strip() for item in match.group(1).split(",")]
        for key in [item for item in keys if item]:
            used.add(key)
            if bib_paths and "#" not in key and key not in bib_keys:
                add(
                    findings,
                    "error",
                    "citation",
                    f"Citation key `{key}` not found in BibTeX files.",
                    document,
                    match.start(),
                )
    if used and not bib_paths:
        findings.append(
            Finding(
                severity="warning",
                check="citation",
                message="Citations found, but no BibTeX file was provided.",
            )
        )
    return findings


def graphic_roots(document: TexDocument) -> list[Path]:
    roots = {document.root.parent.resolve()}
    pattern = re.compile(r"\\graphicspath\{((?:\{[^{}]+\})+)\}", re.DOTALL)
    for match in pattern.finditer(document.text):
        for item in re.findall(r"\{([^{}]+)\}", match.group(1)):
            roots.add((document.root.parent / item).resolve())
    return sorted(roots)


def graphic_exists(name: str, roots: list[Path]) -> bool:
    candidate = Path(name)
    names = (
        [candidate]
        if candidate.suffix
        else [Path(str(candidate) + ext) for ext in GRAPHIC_EXTENSIONS]
    )
    return any((root / item).exists() for root in roots for item in names)


def check_graphics(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    roots = graphic_roots(document)
    pattern = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}")
    for match in pattern.finditer(document.text):
        name = match.group(1)
        if not graphic_exists(name, roots):
            add(
                findings,
                "warning",
                "graphics",
                f"Graphic `{name}` was not found relative to known paths.",
                document,
                match.start(),
            )
    return findings


def check_placeholders(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    patterns = (
        r"\[NEED DATA:[^\]]*\]",
        r"\[NEED CITATION:[^\]]*\]",
        r"TODO",
        r"FIXME",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, document.text, flags=re.IGNORECASE):
            add(
                findings,
                "warning",
                "placeholder",
                f"Placeholder remains: {match.group(0)}",
                document,
                match.start(),
            )
    return findings


def check_alignment_tabs(document: TexDocument) -> list[Finding]:
    findings: list[Finding] = []
    math_or_table_envs = {
        "align",
        "align*",
        "array",
        "tabular",
        "tabularx",
        "matrix",
        "pmatrix",
        "bmatrix",
        "cases",
        "split",
    }
    stack: list[str] = []
    offset = 0
    for line in document.text.splitlines():
        for match in re.finditer(r"\\(begin|end)\{([^{}]+)\}", line):
            if match.group(1) == "begin":
                stack.append(match.group(2))
            elif stack:
                stack.pop()
        if "&" in line and r"\&" not in line:
            if not set(stack).intersection(math_or_table_envs):
                add(
                    findings,
                    "warning",
                    "special-char",
                    "Unescaped `&` may break LaTeX outside tables/math.",
                    document,
                    offset,
                )
        offset += len(line) + 1
    return findings


def run_checks(
    tex_path: Path,
    bib_paths: list[Path],
) -> tuple[TexDocument, list[Finding]]:
    document = load_document(tex_path)
    all_bib_paths = [path.resolve() for path in bib_paths]
    if not all_bib_paths:
        all_bib_paths = discover_bib_paths(document)

    findings: list[Finding] = []
    findings.extend(check_missing_inputs(document))
    findings.extend(check_document_markers(document))
    findings.extend(check_merge_markers(document))
    findings.extend(check_braces(document))
    findings.extend(check_environments(document))
    findings.extend(check_labels_and_refs(document))
    findings.extend(check_citations(document, all_bib_paths))
    findings.extend(check_graphics(document))
    findings.extend(check_placeholders(document))
    findings.extend(check_alignment_tabs(document))
    return document, findings


def render_markdown(
    document: TexDocument,
    bib_paths: list[Path],
    findings: list[Finding],
) -> str:
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    lines = [
        "# LaTeX Guard Report",
        "",
        f"- TeX root: `{document.root}`",
        f"- TeX files scanned: {len([p for p in document.files if p.exists()])}",
        f"- BibTeX files: {len(bib_paths)}",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
    ]
    if findings:
        lines.extend(
            [
                "| Severity | Check | File | Line | Message |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for item in findings:
            line = "" if item.line is None else str(item.line)
            file_value = "" if item.file is None else item.file
            message = item.message.replace("|", "\\|")
            lines.append(
                f"| {item.severity} | {item.check} | {file_value} | "
                f"{line} | {message} |"
            )
    else:
        lines.append("No guard issues found.")
    lines.append("")
    return "\n".join(lines)


def write_outputs(
    json_path: Path | None,
    markdown_path: Path | None,
    markdown_report: str,
    findings: list[Finding],
) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps([asdict(item) for item in findings], indent=2),
            encoding="utf-8",
        )
    if markdown_path:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown_report, encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run structural guard checks for a LaTeX manuscript."
    )
    parser.add_argument("tex", type=Path, help="Main or wrapper .tex file.")
    parser.add_argument("--bib", type=Path, action="append", default=[])
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.tex.exists():
        print(f"TeX file not found: {args.tex}", file=sys.stderr)
        return 2
    missing_bib = [path for path in args.bib if not path.exists()]
    if missing_bib:
        print(f"BibTeX file not found: {missing_bib[0]}", file=sys.stderr)
        return 2

    document, findings = run_checks(args.tex.resolve(), args.bib)
    bib_paths = [path.resolve() for path in args.bib] or discover_bib_paths(document)
    markdown_report = render_markdown(document, bib_paths, findings)
    write_outputs(args.output_json, args.output_md, markdown_report, findings)

    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(markdown_report, end="")
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
