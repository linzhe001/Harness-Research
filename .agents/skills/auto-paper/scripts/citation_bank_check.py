#!/usr/bin/env python3
"""Validate an auto-paper citation support bank."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from artifact_check import CITATION_COLUMNS, SUPPORT_GRADES, first_markdown_table

SUPPORT_AS_EVIDENCE = {"strong", "partial"}
CORE_CLAIM_MARKERS = {"core", "main", "contribution", "result", "novelty"}
INTRO_CLAIM_MARKERS = {"intro", "background", "context", "motivation"}
SUPPORT_WORDS = {"support", "supports", "supported", "evidence", "back"}


@dataclass(frozen=True)
class Finding:
    severity: str
    check: str
    claim_id: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check auto-paper citation support bank quality."
    )
    parser.add_argument("citation_support_bank", type=Path)
    parser.add_argument("--output", type=Path, help="Write Markdown report.")
    parser.add_argument("--json-output", type=Path, help="Write JSON findings.")
    parser.add_argument("--json", action="store_true", help="Print JSON findings.")
    parser.add_argument("--min-strong-per-core-claim", type=int, default=1)
    parser.add_argument("--allow-background-for-intro", action="store_true")
    parser.add_argument("--recent-window-years", type=int, default=0)
    parser.add_argument("--venue-field", default="venue_year")
    return parser.parse_args()


def words(value: str) -> set[str]:
    return {item for item in re.split(r"[^a-z0-9_+-]+", value.lower()) if item}


def has_any(value: str, markers: set[str]) -> bool:
    return bool(words(value) & markers)


def row_claim_id(row: dict[str, str], index: int) -> str:
    return row.get("claim_id", "").strip() or f"row_{index:03d}"


def is_core_claim(rows: list[dict[str, str]]) -> bool:
    combined = " ".join(
        row.get(field, "")
        for row in rows
        for field in ("claim_type", "allowed_use", "risk_note")
    )
    return has_any(combined, CORE_CLAIM_MARKERS)


def is_intro_claim(rows: list[dict[str, str]]) -> bool:
    combined = " ".join(
        row.get(field, "")
        for row in rows
        for field in ("claim_type", "allowed_use")
    )
    return has_any(combined, INTRO_CLAIM_MARKERS)


def parse_year(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", value)
    if not match:
        return None
    return int(match.group(0))


def grouped_by_claim(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for index, row in enumerate(rows, start=1):
        grouped.setdefault(row_claim_id(row, index), []).append(row)
    return grouped


def check_schema(headers: list[str], rows: list[dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    missing = sorted(CITATION_COLUMNS - set(headers))
    if missing:
        findings.append(
            Finding(
                "error",
                "schema",
                "-",
                "Missing required columns: " + ", ".join(missing) + ".",
            )
        )
    if not rows:
        findings.append(Finding("error", "schema", "-", "No citation rows found."))
    return findings


def check_rows(
    rows: list[dict[str, str]],
    recent_window_years: int,
    venue_field: str,
) -> list[Finding]:
    findings: list[Finding] = []
    current_year = date.today().year
    cutoff_year = current_year - recent_window_years if recent_window_years else None

    for index, row in enumerate(rows, start=1):
        claim_id = row_claim_id(row, index)
        grade = row.get("support_grade", "").strip().lower()
        allowed_use = row.get("allowed_use", "").strip().lower()
        source_key = row.get("source_key", "").strip()

        if not grade:
            findings.append(
                Finding("error", "support-grade", claim_id, "Missing support_grade.")
            )
            continue
        if grade not in SUPPORT_GRADES:
            findings.append(
                Finding(
                    "error",
                    "support-grade",
                    claim_id,
                    f"Unknown support_grade `{grade}`.",
                )
            )
            continue

        if grade == "metadata_only" and words(allowed_use) & SUPPORT_WORDS:
            findings.append(
                Finding(
                    "error",
                    "metadata-only",
                    claim_id,
                    "metadata_only row is marked as claim support.",
                )
            )
        if grade == "unsupported" and words(allowed_use) & SUPPORT_WORDS:
            findings.append(
                Finding(
                    "error",
                    "unsupported-use",
                    claim_id,
                    "unsupported row is marked as claim support.",
                )
            )
        if grade in SUPPORT_AS_EVIDENCE and not source_key:
            findings.append(
                Finding(
                    "error",
                    "source-key",
                    claim_id,
                    f"{grade} support is missing source_key.",
                )
            )

        if cutoff_year is not None and grade in SUPPORT_AS_EVIDENCE:
            year = parse_year(row.get(venue_field, ""))
            if year is None:
                findings.append(
                    Finding(
                        "warning",
                        "recency",
                        claim_id,
                        f"No parseable year in `{venue_field}`.",
                    )
                )
            elif year < cutoff_year:
                findings.append(
                    Finding(
                        "warning",
                        "recency",
                        claim_id,
                        (
                            f"Source year {year} is older than recency cutoff "
                            f"{cutoff_year}."
                        ),
                    )
                )
    return findings


def check_claim_groups(
    rows: list[dict[str, str]],
    min_strong_per_core_claim: int,
    allow_background_for_intro: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    for claim_id, claim_rows in grouped_by_claim(rows).items():
        grades = [row.get("support_grade", "").strip().lower() for row in claim_rows]
        strong_count = grades.count("strong")
        direct_count = sum(1 for grade in grades if grade in SUPPORT_AS_EVIDENCE)
        if is_core_claim(claim_rows) and strong_count < min_strong_per_core_claim:
            findings.append(
                Finding(
                    "error",
                    "core-support",
                    claim_id,
                    "Core claim has fewer strong support rows than required.",
                )
            )
        if direct_count == 0 and grades:
            if allow_background_for_intro and is_intro_claim(claim_rows):
                continue
            findings.append(
                Finding(
                    "warning",
                    "direct-support",
                    claim_id,
                    "Claim has no strong or partial support rows.",
                )
            )
    return findings


def render_markdown(path: Path, findings: list[Finding]) -> str:
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    lines = [
        "# Citation Bank Check",
        "",
        f"- Source: `{path}`",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
    ]
    if findings:
        lines.extend(
            ["| Severity | Check | Claim ID | Message |", "| --- | --- | --- | --- |"]
        )
        for item in findings:
            message = item.message.replace("|", "\\|")
            lines.append(
                f"| {item.severity} | {item.check} | {item.claim_id} | {message} |"
            )
    else:
        lines.append("No citation bank issues found.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    headers, rows = first_markdown_table(args.citation_support_bank)
    findings = check_schema(headers, rows)
    findings.extend(
        check_rows(rows, args.recent_window_years, args.venue_field.lower())
    )
    findings.extend(
        check_claim_groups(
            rows,
            args.min_strong_per_core_claim,
            args.allow_background_for_intro,
        )
    )

    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(render_markdown(args.citation_support_bank, findings), end="")
    if args.output:
        args.output.write_text(
            render_markdown(args.citation_support_bank, findings),
            encoding="utf-8",
        )
    if args.json_output:
        args.json_output.write_text(
            json.dumps([asdict(item) for item in findings], indent=2) + "\n",
            encoding="utf-8",
        )
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
