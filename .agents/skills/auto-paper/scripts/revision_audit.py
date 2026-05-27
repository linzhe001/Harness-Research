#!/usr/bin/env python3
"""Audit auto-paper revision depth and patch ledger coverage."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from artifact_check import first_markdown_table

PASS_VALUES = {"pass", "passed", "ok", "not_run", "not-run", "not run"}
EMPTY_VALUES = {"", "unknown", "tbd", "todo", "none", "n/a", "na"}


@dataclass(frozen=True)
class RevisionFinding:
    severity: str
    unit_id: str
    check: str
    result: str
    issue: str
    action: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit auto-paper revision quality.")
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--patch-ledger", type=Path)
    parser.add_argument("--latex-patch-plan", type=Path)
    parser.add_argument("--before", type=Path, help="Original text or TeX snippet.")
    parser.add_argument("--after", type=Path, help="Revised text or TeX snippet.")
    parser.add_argument("--similarity-threshold", type=float, default=0.97)
    parser.add_argument("--addition-ratio-threshold", type=float, default=0.65)
    parser.add_argument("--output", type=Path, help="Write Markdown report.")
    parser.add_argument("--json-output", type=Path, help="Write JSON findings.")
    parser.add_argument("--json", action="store_true", help="Print JSON findings.")
    return parser.parse_args()


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_+-]+", text.lower())


def is_blank(value: str) -> bool:
    return value.strip().lower() in EMPTY_VALUES


def default_path(artifact_dir: Path | None, name: str) -> Path | None:
    return artifact_dir / name if artifact_dir else None


def planned_units(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    _, rows = first_markdown_table(path)
    return {
        row.get("unit_id", "").strip()
        for row in rows
        if row.get("unit_id", "").strip()
    }


def ledger_rows(path: Path | None) -> list[dict[str, str]]:
    if not path or not path.exists():
        return []
    _, rows = first_markdown_table(path)
    return rows


def compare_texts(
    before: Path,
    after: Path,
    similarity_threshold: float,
    addition_ratio_threshold: float,
) -> list[RevisionFinding]:
    before_words = normalized_words(before.read_text(encoding="utf-8", errors="ignore"))
    after_words = normalized_words(after.read_text(encoding="utf-8", errors="ignore"))
    findings: list[RevisionFinding] = []
    if not before_words or not after_words:
        findings.append(
            RevisionFinding(
                "error",
                "file_pair",
                "text-compare",
                "FAIL",
                "Before or after text has no parseable words.",
                "Provide non-empty before and after snippets.",
            )
        )
        return findings

    similarity = difflib.SequenceMatcher(None, before_words, after_words).ratio()
    if similarity >= similarity_threshold:
        findings.append(
            RevisionFinding(
                "error",
                "file_pair",
                "near-identical",
                "FAIL",
                (
                    f"Similarity {similarity:.3f} exceeds threshold "
                    f"{similarity_threshold:.3f}."
                ),
                "Rework the unit or mark it as intentionally unchanged.",
            )
        )

    addition_ratio = max(0, len(after_words) - len(before_words)) / max(
        len(before_words),
        1,
    )
    if addition_ratio > addition_ratio_threshold:
        findings.append(
            RevisionFinding(
                "warning",
                "file_pair",
                "addition-heavy",
                "WARN",
                (
                    f"Addition ratio {addition_ratio:.3f} exceeds threshold "
                    f"{addition_ratio_threshold:.3f}."
                ),
                "Check whether the revision adds unsupported exposition.",
            )
        )
    return findings


def check_ledger(
    patch_ledger: Path | None,
    latex_patch_plan: Path | None,
) -> list[RevisionFinding]:
    if patch_ledger and not patch_ledger.exists():
        return [
            RevisionFinding(
                "error",
                "-",
                "patch-ledger",
                "FAIL",
                f"Patch ledger not found: {patch_ledger}.",
                "Run patch phase or provide the correct patch_ledger.md path.",
            )
        ]
    rows = ledger_rows(patch_ledger)
    plan_units = planned_units(latex_patch_plan)
    findings: list[RevisionFinding] = []
    if patch_ledger and patch_ledger.exists() and not rows:
        findings.append(
            RevisionFinding(
                "error",
                "-",
                "patch-ledger",
                "FAIL",
                "patch_ledger.md has no rows.",
                "Record each patched unit before harden.",
            )
        )
    if plan_units:
        ledger_units = {row.get("unit_id", "").strip() for row in rows}
        missing = sorted(plan_units - ledger_units)
        extra = sorted(unit for unit in ledger_units - plan_units if unit)
        for unit_id in missing:
            findings.append(
                RevisionFinding(
                    "error",
                    unit_id,
                    "plan-coverage",
                    "FAIL",
                    "Planned unit has no patch ledger row.",
                    "Patch the unit or revise latex_patch_plan.md.",
                )
            )
        for unit_id in extra:
            findings.append(
                RevisionFinding(
                    "warning",
                    unit_id,
                    "plan-coverage",
                    "WARN",
                    "Patch ledger unit is not present in latex_patch_plan.md.",
                    "Confirm the extra patch unit is intentional.",
                )
            )
    for index, row in enumerate(rows, start=1):
        unit_id = row.get("unit_id", "").strip() or f"row_{index:03d}"
        if is_blank(row.get("patch_artifact", "")):
            findings.append(
                RevisionFinding(
                    "error",
                    unit_id,
                    "patch-artifact",
                    "FAIL",
                    "Patch row is missing patch_artifact.",
                    "Link the generated diff artifact for this unit.",
                )
            )
        guard_result = row.get("guard_result", "").strip().lower()
        if guard_result and guard_result not in PASS_VALUES:
            findings.append(
                RevisionFinding(
                    "error",
                    unit_id,
                    "guard-result",
                    "FAIL",
                    f"guard_result is `{guard_result}`.",
                    "Re-run latex_guard or route back to patch.",
                )
            )
        if is_blank(row.get("reviewer_risk_delta", "")):
            findings.append(
                RevisionFinding(
                    "warning",
                    unit_id,
                    "risk-delta",
                    "WARN",
                    "reviewer_risk_delta is missing.",
                    "Record whether this edit raises or lowers reviewer risk.",
                )
            )
        before_role = row.get("before_role", "").strip().lower()
        after_role = row.get("after_role", "").strip().lower()
        if before_role and before_role == after_role:
            findings.append(
                RevisionFinding(
                    "warning",
                    unit_id,
                    "role-change",
                    "WARN",
                    "before_role and after_role are identical.",
                    "Confirm this was not a shallow wording-only edit.",
                )
            )
    return findings


def render_markdown(findings: list[RevisionFinding]) -> str:
    lines = [
        "# Revision Audit Report",
        "",
        "| unit_id | check | result | issue | action |",
        "| --- | --- | --- | --- | --- |",
    ]
    if findings:
        for item in findings:
            values = [item.unit_id, item.check, item.result, item.issue, item.action]
            escaped = [value.replace("|", "\\|") for value in values]
            lines.append("| " + " | ".join(escaped) + " |")
    else:
        lines.append(
            "| all | revision-audit | PASS | no revision issues found | none |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    patch_ledger = args.patch_ledger or default_path(
        args.artifact_dir,
        "patch_ledger.md",
    )
    latex_patch_plan = args.latex_patch_plan or default_path(
        args.artifact_dir,
        "latex_patch_plan.md",
    )
    findings: list[RevisionFinding] = []
    if args.before and args.after:
        findings.extend(
            compare_texts(
                args.before,
                args.after,
                args.similarity_threshold,
                args.addition_ratio_threshold,
            )
        )
    findings.extend(check_ledger(patch_ledger, latex_patch_plan))
    has_revision_input = bool(args.before and args.after) or bool(
        patch_ledger and patch_ledger.exists()
    )
    if not findings and not has_revision_input:
        findings.append(
            RevisionFinding(
                "error",
                "-",
                "inputs",
                "FAIL",
                "No before/after pair or patch ledger was provided.",
                "Provide comparison files or an artifact directory.",
            )
        )

    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(render_markdown(findings), end="")
    if args.output:
        args.output.write_text(render_markdown(findings), encoding="utf-8")
    if args.json_output:
        args.json_output.write_text(
            json.dumps([asdict(item) for item in findings], indent=2) + "\n",
            encoding="utf-8",
        )
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
