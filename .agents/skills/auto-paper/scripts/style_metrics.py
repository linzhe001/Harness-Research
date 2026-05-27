#!/usr/bin/env python3
"""Measure manuscript style risks without AI-detection claims."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from latex_guard import strip_comments

COMMON_ACRONYMS = {
    "AI",
    "API",
    "AUC",
    "CNN",
    "CPU",
    "CT",
    "DOI",
    "GPU",
    "JSON",
    "MRI",
    "PDF",
    "ROC",
    "URL",
}
OVERSTRONG_RE = re.compile(
    r"\b("
    r"prove|proves|proved|guarantee|guarantees|state-of-the-art|sota|"
    r"significant|significantly|clinical|clinically|first|novel|best"
    r")\b",
    re.IGNORECASE,
)
CITE_RE = re.compile(r"\\cite\w*\*?(?:\[[^\]]*\]){0,2}\{[^{}]+\}|\[[0-9,\-\s]+\]")


@dataclass(frozen=True)
class StyleFinding:
    severity: str
    check: str
    location: str
    value: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure auto-paper style risks.")
    parser.add_argument("manuscript", type=Path)
    parser.add_argument("--max-paragraph-words", type=int, default=180)
    parser.add_argument("--max-sentence-words", type=int, default=45)
    parser.add_argument("--citation-paragraph-words", type=int, default=100)
    parser.add_argument("--allow-acronym", action="append", default=[])
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--output", type=Path, help="Write Markdown report.")
    parser.add_argument("--json-output", type=Path, help="Write JSON findings.")
    parser.add_argument("--json", action="store_true", help="Print JSON findings.")
    return parser.parse_args()


def strip_latex_commands(text: str) -> str:
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r"\1", text)
    text = re.sub(r"[{}$]", " ", text)
    return text


def paragraphs(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]


def sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_+-]+", text)


def check_paragraphs(
    raw_paragraphs: list[str],
    clean_paragraphs: list[str],
    max_paragraph_words: int,
    citation_paragraph_words: int,
) -> list[StyleFinding]:
    findings: list[StyleFinding] = []
    for index, paragraph in enumerate(clean_paragraphs, start=1):
        count = len(words(paragraph))
        if count > max_paragraph_words:
            findings.append(
                StyleFinding(
                    "warning",
                    "paragraph-length",
                    f"paragraph_{index:03d}",
                    str(count),
                    "Paragraph is longer than the configured word limit.",
                )
            )
        raw = (
            raw_paragraphs[index - 1]
            if index - 1 < len(raw_paragraphs)
            else paragraph
        )
        if count >= citation_paragraph_words and not CITE_RE.search(raw):
            findings.append(
                StyleFinding(
                    "warning",
                    "citation-density",
                    f"paragraph_{index:03d}",
                    str(count),
                    "Long paragraph has no citation command or numeric citation.",
                )
            )
    return findings


def check_sentences(clean_text: str, max_sentence_words: int) -> list[StyleFinding]:
    findings: list[StyleFinding] = []
    for index, sentence in enumerate(sentences(clean_text), start=1):
        count = len(words(sentence))
        if count > max_sentence_words:
            findings.append(
                StyleFinding(
                    "warning",
                    "sentence-length",
                    f"sentence_{index:03d}",
                    str(count),
                    "Sentence is longer than the configured word limit.",
                )
            )
    return findings


def check_overstrong(clean_text: str) -> list[StyleFinding]:
    findings: list[StyleFinding] = []
    for index, match in enumerate(OVERSTRONG_RE.finditer(clean_text), start=1):
        findings.append(
            StyleFinding(
                "warning",
                "overstrong-word",
                f"match_{index:03d}",
                match.group(0),
                "High-strength wording should be backed by claim support.",
            )
        )
    return findings


def check_acronyms(clean_text: str, allowed: set[str]) -> list[StyleFinding]:
    explained = set(re.findall(r"\(([A-Z]{2,})\)", clean_text))
    findings: list[StyleFinding] = []
    seen: set[str] = set()
    for acronym in re.findall(r"\b[A-Z]{2,}\b", clean_text):
        if acronym in seen or acronym in allowed or acronym in explained:
            continue
        seen.add(acronym)
        findings.append(
            StyleFinding(
                "warning",
                "acronym",
                acronym,
                acronym,
                "Acronym appears without a local parenthetical definition.",
            )
        )
    return findings


def render_markdown(path: Path, findings: list[StyleFinding]) -> str:
    lines = [
        "# Style Metrics",
        "",
        f"- Source: `{path}`",
        f"- Warnings: {len(findings)}",
        "",
    ]
    if findings:
        lines.extend(
            [
                "| Severity | Check | Location | Value | Message |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in findings:
            values = [
                item.severity,
                item.check,
                item.location,
                item.value,
                item.message,
            ]
            escaped = [value.replace("|", "\\|") for value in values]
            lines.append("| " + " | ".join(escaped) + " |")
    else:
        lines.append("No style metric issues found.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    raw_text = strip_comments(
        args.manuscript.read_text(encoding="utf-8", errors="ignore")
    )
    clean_text = strip_latex_commands(raw_text)
    raw_paragraphs = paragraphs(raw_text)
    clean_paragraphs = paragraphs(clean_text)
    allowed = COMMON_ACRONYMS | {item.upper() for item in args.allow_acronym}
    findings: list[StyleFinding] = []
    findings.extend(
        check_paragraphs(
            raw_paragraphs,
            clean_paragraphs,
            args.max_paragraph_words,
            args.citation_paragraph_words,
        )
    )
    findings.extend(check_sentences(clean_text, args.max_sentence_words))
    findings.extend(check_overstrong(clean_text))
    findings.extend(check_acronyms(clean_text, allowed))

    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(render_markdown(args.manuscript, findings), end="")
    if args.output:
        args.output.write_text(
            render_markdown(args.manuscript, findings),
            encoding="utf-8",
        )
    if args.json_output:
        args.json_output.write_text(
            json.dumps([asdict(item) for item in findings], indent=2) + "\n",
            encoding="utf-8",
        )
    if args.fail_on_warning and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
