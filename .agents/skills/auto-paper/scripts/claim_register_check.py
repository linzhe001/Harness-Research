#!/usr/bin/env python3
"""Validate auto-paper claim register support and boundaries."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from artifact_check import CLAIM_COLUMNS, first_markdown_table

DIRECT_SUPPORT_GRADES = {"strong", "partial"}
EMPTY_VALUES = {"", "unknown", "tbd", "todo", "none", "n/a", "na"}
YES_VALUES = {"yes", "y", "true", "required", "needed", "must", "citation"}
NO_VALUES = {"no", "n", "false", "not_needed", "optional"}
HIGH_STRENGTH_VALUES = {"high", "strong", "sota", "novel", "first", "clinical"}
OVERSTRONG_RE = re.compile(
    r"\b("
    r"prove|proves|proved|guarantee|guarantees|state-of-the-art|sota|"
    r"significant|significantly|clinical|clinically|first|novel|"
    r"generalize|generalizes|outperform|outperforms|best"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    severity: str
    check: str
    claim_id: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check auto-paper claim register boundaries and support."
    )
    parser.add_argument("claim_register", type=Path)
    parser.add_argument("--citation-bank", type=Path)
    parser.add_argument("--matrix", type=Path)
    parser.add_argument("--output", type=Path, help="Write Markdown report.")
    parser.add_argument("--json-output", type=Path, help="Write JSON findings.")
    parser.add_argument("--json", action="store_true", help="Print JSON findings.")
    return parser.parse_args()


def normalized(value: str) -> str:
    return value.strip().lower()


def is_blank(value: str) -> bool:
    return normalized(value) in EMPTY_VALUES


def split_ids(value: str) -> set[str]:
    return {item for item in re.split(r"[,;\s]+", value.strip()) if item}


def claim_id(row: dict[str, str], index: int) -> str:
    return row.get("claim_id", "").strip() or f"row_{index:03d}"


def citation_needed(value: str) -> bool:
    lowered = normalized(value).replace(" ", "_")
    if lowered in NO_VALUES:
        return False
    if lowered in YES_VALUES:
        return True
    return bool(lowered)


def strong_language(row: dict[str, str]) -> bool:
    verb_strength = normalized(row.get("verb_strength", ""))
    claim_text = row.get("claim_text", "")
    return verb_strength in HIGH_STRENGTH_VALUES or bool(
        OVERSTRONG_RE.search(claim_text)
    )


def support_by_claim(citation_bank: Path | None) -> tuple[dict[str, set[str]], bool]:
    if not citation_bank or not citation_bank.exists():
        return {}, False
    _, rows = first_markdown_table(citation_bank)
    support: dict[str, set[str]] = {}
    for row in rows:
        row_claim = row.get("claim_id", "").strip()
        grade = normalized(row.get("support_grade", ""))
        if not row_claim:
            continue
        support.setdefault(row_claim, set()).add(grade)
    return support, True


def matrix_claim_ids(matrix: Path | None) -> set[str]:
    if not matrix or not matrix.exists():
        return set()
    _, rows = first_markdown_table(matrix)
    ids: set[str] = set()
    for row in rows:
        ids.update(
            item
            for item in split_ids(row.get("evidence_ids", ""))
            if item.startswith("claim_")
        )
    return ids


def check_schema(headers: list[str], rows: list[dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    missing = sorted(CLAIM_COLUMNS - set(headers))
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
        findings.append(Finding("error", "schema", "-", "No claim rows found."))
    return findings


def check_claim_rows(
    rows: list[dict[str, str]],
    support: dict[str, set[str]],
    citation_support_available: bool,
    matrix_ids: set[str],
) -> list[Finding]:
    findings: list[Finding] = []
    for index, row in enumerate(rows, start=1):
        row_claim = claim_id(row, index)
        evidence_source = row.get("evidence_source", "")
        citation_need = row.get("citation_need", "")
        scope_limit = row.get("scope_limit", "")
        row_support = support.get(row_claim, set())
        has_direct_support = bool(row_support & DIRECT_SUPPORT_GRADES)

        if is_blank(evidence_source):
            findings.append(
                Finding(
                    "error",
                    "evidence-source",
                    row_claim,
                    "Claim is missing source-backed author evidence.",
                )
            )
        if is_blank(scope_limit):
            findings.append(
                Finding(
                    "error",
                    "scope-limit",
                    row_claim,
                    "Claim is missing a boundary or scope limit.",
                )
            )
        if (
            citation_support_available
            and citation_needed(citation_need)
            and not has_direct_support
        ):
            findings.append(
                Finding(
                    "error",
                    "citation-support",
                    row_claim,
                    "Citation-needed claim has no strong or partial support row.",
                )
            )
        if (
            citation_support_available
            and strong_language(row)
            and not has_direct_support
        ):
            findings.append(
                Finding(
                    "error",
                    "overclaim",
                    row_claim,
                    "Over-strong claim language lacks direct citation support.",
                )
            )
        if not citation_support_available and strong_language(row):
            findings.append(
                Finding(
                    "warning",
                    "overclaim",
                    row_claim,
                    "Over-strong claim language requires citation support check.",
                )
            )
        if matrix_ids and row_claim not in matrix_ids:
            findings.append(
                Finding(
                    "warning",
                    "layout-coverage",
                    row_claim,
                    "Claim is not referenced by writing_rationale_matrix.md.",
                )
            )
    return findings


def render_markdown(path: Path, findings: list[Finding]) -> str:
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    lines = [
        "# Claim Register Check",
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
        lines.append("No claim register issues found.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    headers, rows = first_markdown_table(args.claim_register)
    support, citation_support_available = support_by_claim(args.citation_bank)
    findings = check_schema(headers, rows)
    findings.extend(
        check_claim_rows(
            rows,
            support,
            citation_support_available,
            matrix_claim_ids(args.matrix),
        )
    )

    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(render_markdown(args.claim_register, findings), end="")
    if args.output:
        args.output.write_text(
            render_markdown(args.claim_register, findings),
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
