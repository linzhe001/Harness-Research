#!/usr/bin/env python3
"""Check auto-paper artifacts for existence and shallow contract failures."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

PHASES = (
    "intake",
    "research",
    "argument",
    "citation",
    "layout",
    "patch",
    "harden",
)
PHASE_INDEX = {phase: index for index, phase in enumerate(PHASES)}
REQUIRED_BY_PHASE = {
    "intake": (
        "config.yaml",
        "source_index.md",
        "tex_inventory.json",
        "intake_report.md",
    ),
    "research": (
        "research_dossier.md",
        "exemplar_learning_dossier.md",
        "style_profile.md",
        "sota_gap_map.md",
    ),
    "argument": (
        "confirmed_motivation.md",
        "claim_register.md",
        "claims_to_avoid.md",
        "motivation_surface_map.md",
    ),
    "citation": (
        "citation_support_bank.md",
        "claim_citation_map.md",
    ),
    "layout": (
        "original_logic_map.md",
        "section_blueprints.md",
        "writing_rationale_matrix.md",
        "citation_plan.md",
        "latex_patch_plan.md",
    ),
    "patch": ("patch_ledger.md",),
    "harden": (
        "audit_report.md",
        "compile_report.md",
        "citation_audit_report.md",
        "revision_audit_report.md",
        "logic_transfer_audit.md",
        "final_gate_ledger.md",
    ),
}
MATRIX_COLUMNS = {
    "unit_id",
    "source_location",
    "current_text_role",
    "problem_type",
    "reader_question",
    "target_role",
    "evidence_ids",
    "citation_ids",
    "rewrite_action",
    "latex_constraints",
    "overclaim_risk",
    "done_definition",
}
CLAIM_COLUMNS = {
    "claim_id",
    "location",
    "claim_text",
    "evidence_source",
    "citation_need",
    "verb_strength",
    "scope_limit",
    "reviewer_risk",
}
CITATION_COLUMNS = {
    "claim_id",
    "claim_text",
    "claim_type",
    "support_grade",
    "source_key",
    "source_type",
    "evidence_sentence",
    "venue_year",
    "recency_bucket",
    "risk_note",
    "allowed_use",
    "needs_user_confirmation",
}
SUPPORT_GRADES = {
    "strong",
    "partial",
    "background",
    "limiting",
    "metadata_only",
    "unsupported",
}
SHALLOW_PHRASES = {
    "make clearer",
    "improve clarity",
    "improve flow",
    "add citation",
    "shorten",
    "polish language",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    check: str
    path: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check auto-paper artifacts.")
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--phase", choices=(*PHASES, "all"), default="all")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def split_table_line(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells if cell)


def first_markdown_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    lines = read_text(path).splitlines()
    for index, line in enumerate(lines):
        if "|" not in line:
            continue
        header = split_table_line(line)
        if index + 1 >= len(lines):
            continue
        separator = split_table_line(lines[index + 1])
        if not is_separator(separator):
            continue
        rows: list[dict[str, str]] = []
        for row_line in lines[index + 2 :]:
            if "|" not in row_line:
                break
            cells = split_table_line(row_line)
            row = {
                header[cell_index].strip().lower(): cell
                for cell_index, cell in enumerate(cells)
                if cell_index < len(header)
            }
            rows.append(row)
        return [cell.strip().lower() for cell in header], rows
    return [], []


def required_for_phase(phase: str) -> list[str]:
    result: list[str] = []
    for phase_name in phases_through(phase):
        result.extend(REQUIRED_BY_PHASE[phase_name])
    return result


def phases_through(phase: str) -> tuple[str, ...]:
    if phase == "all":
        return PHASES
    return PHASES[: PHASE_INDEX[phase] + 1]


def phase_reached(selected: str, target: str) -> bool:
    return target in phases_through(selected)


def check_required_files(artifact_dir: Path, phase: str) -> list[Finding]:
    findings: list[Finding] = []
    for relative in required_for_phase(phase):
        path = artifact_dir / relative
        if not path.exists():
            findings.append(Finding("error", "required", relative, "Missing artifact."))
            continue
        if path.is_file() and path.stat().st_size == 0:
            findings.append(
                Finding("error", "required", relative, "Artifact is empty.")
            )
    return findings


def check_table_columns(
    artifact_dir: Path,
    relative: str,
    required: set[str],
) -> list[Finding]:
    path = artifact_dir / relative
    if not path.exists():
        return []
    header, _ = first_markdown_table(path)
    missing = sorted(required - set(header))
    if missing:
        return [
            Finding(
                "error",
                "table-schema",
                relative,
                f"Missing required columns: {', '.join(missing)}.",
            )
        ]
    return []


def check_matrix_depth(artifact_dir: Path) -> list[Finding]:
    path = artifact_dir / "writing_rationale_matrix.md"
    if not path.exists():
        return []
    _, rows = first_markdown_table(path)
    findings: list[Finding] = []
    if not rows:
        findings.append(Finding("error", "matrix", path.name, "No matrix rows found."))
        return findings
    for row in rows:
        unit_id = row.get("unit_id", "<unknown>")
        combined = " ".join(row.values()).strip().lower()
        if combined in SHALLOW_PHRASES or any(
            phrase == combined for phrase in SHALLOW_PHRASES
        ):
            findings.append(
                Finding(
                    "error",
                    "matrix-depth",
                    path.name,
                    f"{unit_id} has a shallow rationale: {combined}.",
                )
            )
        for key in ("reader_question", "evidence_ids", "done_definition"):
            if not row.get(key, "").strip():
                findings.append(
                    Finding(
                        "warning",
                        "matrix-depth",
                        path.name,
                        f"{unit_id} is missing `{key}`.",
                    )
                )
    return findings


def table_values(artifact_dir: Path, relative: str, key: str) -> set[str]:
    _, rows = first_markdown_table(artifact_dir / relative)
    return {row[key].strip() for row in rows if row.get(key, "").strip()}


def check_cross_refs(artifact_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    claim_ids = table_values(artifact_dir, "claim_register.md", "claim_id")
    matrix_claims = table_values(
        artifact_dir,
        "writing_rationale_matrix.md",
        "evidence_ids",
    )
    citation_claims = table_values(artifact_dir, "citation_support_bank.md", "claim_id")
    if claim_ids and citation_claims:
        missing_citations = sorted(claim_ids - citation_claims)
        if missing_citations:
            findings.append(
                Finding(
                    "warning",
                    "cross-reference",
                    "citation_support_bank.md",
                    "Claim IDs missing citation rows: "
                    + ", ".join(missing_citations[:12]),
                )
            )
    if claim_ids and matrix_claims:
        mentioned = {
            item
            for cell in matrix_claims
            for item in re.split(r"[,;\s]+", cell)
            if item.startswith("claim_")
        }
        unused = sorted(claim_ids - mentioned)
        if unused:
            findings.append(
                Finding(
                    "warning",
                    "cross-reference",
                    "writing_rationale_matrix.md",
                    "Claim IDs not mentioned by matrix evidence_ids: "
                    + ", ".join(unused[:12]),
                )
            )
    return findings


def check_citation_grades(artifact_dir: Path) -> list[Finding]:
    path = artifact_dir / "citation_support_bank.md"
    if not path.exists():
        return []
    _, rows = first_markdown_table(path)
    findings: list[Finding] = []
    for row in rows:
        grade = row.get("support_grade", "").strip().lower()
        claim_id = row.get("claim_id", "<unknown>")
        if grade and grade not in SUPPORT_GRADES:
            findings.append(
                Finding(
                    "error",
                    "citation-grade",
                    path.name,
                    f"{claim_id} has unknown support_grade `{grade}`.",
                )
            )
        if grade == "metadata_only":
            allowed = row.get("allowed_use", "").strip().lower()
            if "support" in allowed:
                findings.append(
                    Finding(
                        "error",
                        "citation-grade",
                        path.name,
                        f"{claim_id} uses metadata_only as support.",
                    )
                )
    return findings


def run_checks(artifact_dir: Path, phase: str) -> list[Finding]:
    findings = check_required_files(artifact_dir, phase)
    if phase_reached(phase, "argument"):
        findings.extend(
            check_table_columns(artifact_dir, "claim_register.md", CLAIM_COLUMNS)
        )
    if phase_reached(phase, "citation"):
        findings.extend(
            check_table_columns(
                artifact_dir,
                "citation_support_bank.md",
                CITATION_COLUMNS,
            )
        )
        findings.extend(check_citation_grades(artifact_dir))
    if phase_reached(phase, "layout"):
        findings.extend(
            check_table_columns(
                artifact_dir,
                "writing_rationale_matrix.md",
                MATRIX_COLUMNS,
            )
        )
        findings.extend(check_matrix_depth(artifact_dir))
        findings.extend(check_cross_refs(artifact_dir))
    return findings


def render_markdown(artifact_dir: Path, phase: str, findings: list[Finding]) -> str:
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    lines = [
        "# Auto-Paper Artifact Check",
        "",
        f"- Artifact dir: `{artifact_dir}`",
        f"- Phase: `{phase}`",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
    ]
    if findings:
        lines.extend(
            ["| Severity | Check | Path | Message |", "| --- | --- | --- | --- |"]
        )
        for item in findings:
            message = item.message.replace("|", "\\|")
            lines.append(
                f"| {item.severity} | {item.check} | {item.path} | {message} |"
            )
    else:
        lines.append("No artifact issues found.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    findings = run_checks(args.artifact_dir, args.phase)
    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(render_markdown(args.artifact_dir, args.phase, findings), end="")
    if args.write:
        output = args.artifact_dir / "artifact_check.md"
        output.write_text(
            render_markdown(args.artifact_dir, args.phase, findings),
            encoding="utf-8",
        )
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
