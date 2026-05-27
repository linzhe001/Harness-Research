#!/usr/bin/env python3
"""Run a phase-aware auto-paper artifact integrity audit."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from artifact_check import PHASES, REQUIRED_BY_PHASE, first_markdown_table, run_checks

AUDIT_COLUMNS = {
    "finding_id",
    "severity",
    "location",
    "root_cause",
    "owning_phase",
    "required_artifact",
    "fix_action",
    "downstream_risk",
}
ROUTABLE_PHASES = {"research", "argument", "citation", "layout", "patch", "harden"}


@dataclass(frozen=True)
class IntegrityFinding:
    finding_id: str
    severity: str
    location: str
    root_cause: str
    owning_phase: str
    required_artifact: str
    fix_action: str
    downstream_risk: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit auto-paper artifact chain.")
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--phase", choices=(*PHASES, "all"), default="all")
    parser.add_argument("--output", type=Path, help="Write Markdown audit report.")
    parser.add_argument("--json-output", type=Path, help="Write JSON findings.")
    parser.add_argument("--json", action="store_true", help="Print JSON findings.")
    return parser.parse_args()


def phase_for_artifact(relative: str) -> str:
    for phase, files in REQUIRED_BY_PHASE.items():
        if relative in files:
            return "research" if phase == "intake" else phase
    return "harden"


def fix_action(check: str, path: str, owning_phase: str) -> str:
    if check == "required":
        return f"Recreate `{path}` before rerunning {owning_phase}."
    if check == "table-schema":
        return f"Rewrite `{path}` with the required artifact table schema."
    if check == "matrix-depth":
        return "Rework layout rationale with concrete reader question and evidence."
    if check == "citation-grade":
        return "Rework citation support grade and allowed-use mapping."
    if check == "cross-reference":
        return "Repair artifact identifiers so downstream phases can route claims."
    return f"Rework {owning_phase} artifact content."


def downstream_risk(check: str) -> str:
    risks = {
        "required": "Later phases may operate from chat memory or stale state.",
        "table-schema": "Controller and audit scripts may be unable to parse gates.",
        "matrix": "Patch phase has no accountable rewrite units.",
        "matrix-depth": "Patch phase may produce shallow prose-only edits.",
        "citation-grade": "Unsupported claims may be patched into the manuscript.",
        "cross-reference": "Claim, citation, and patch traceability may break.",
    }
    return risks.get(check, "Reviewer-facing readiness cannot be established.")


def from_artifact_findings(artifact_dir: Path, phase: str) -> list[IntegrityFinding]:
    findings: list[IntegrityFinding] = []
    for index, item in enumerate(run_checks(artifact_dir, phase), start=1):
        owning_phase = phase_for_artifact(item.path)
        findings.append(
            IntegrityFinding(
                finding_id=f"finding_{index:03d}",
                severity=item.severity,
                location=item.path,
                root_cause=f"{item.check}: {item.message}",
                owning_phase=owning_phase,
                required_artifact=item.path,
                fix_action=fix_action(item.check, item.path, owning_phase),
                downstream_risk=downstream_risk(item.check),
            )
        )
    return findings


def audit_report_schema_findings(
    artifact_dir: Path,
    start_index: int,
) -> list[IntegrityFinding]:
    path = artifact_dir / "audit_report.md"
    if not path.exists():
        return []
    headers, rows = first_markdown_table(path)
    findings: list[IntegrityFinding] = []
    missing = sorted(AUDIT_COLUMNS - set(headers))
    if missing:
        findings.append(
            IntegrityFinding(
                finding_id=f"finding_{start_index:03d}",
                severity="error",
                location="audit_report.md",
                root_cause="audit_report schema missing: " + ", ".join(missing),
                owning_phase="harden",
                required_artifact="audit_report.md",
                fix_action="Rewrite audit_report.md with the required columns.",
                downstream_risk="Controller cannot route harden findings reliably.",
            )
        )
        start_index += 1
    for row in rows:
        owning_phase = row.get("owning_phase", "").strip()
        if owning_phase and owning_phase not in ROUTABLE_PHASES:
            findings.append(
                IntegrityFinding(
                    finding_id=f"finding_{start_index:03d}",
                    severity="error",
                    location="audit_report.md",
                    root_cause=f"Invalid owning_phase `{owning_phase}`.",
                    owning_phase="harden",
                    required_artifact="audit_report.md",
                    fix_action="Use a routable owning_phase for each finding.",
                    downstream_risk="Failure routing may target a nonexistent phase.",
                )
            )
            start_index += 1
    return findings


def render_markdown(artifact_dir: Path, findings: list[IntegrityFinding]) -> str:
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    lines = [
        "# Audit Report",
        "",
        f"- Artifact dir: `{artifact_dir}`",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
        "| finding_id | severity | location | root_cause | owning_phase | "
        "required_artifact | fix_action | downstream_risk |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in findings:
        values = [
            item.finding_id,
            item.severity,
            item.location,
            item.root_cause,
            item.owning_phase,
            item.required_artifact,
            item.fix_action,
            item.downstream_risk,
        ]
        escaped = [value.replace("|", "\\|") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    if not findings:
        lines.append(
            "| finding_000 | pass | all | no integrity issues found | harden | "
            "audit_report.md | none | none |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    findings = from_artifact_findings(args.artifact_dir, args.phase)
    findings.extend(audit_report_schema_findings(args.artifact_dir, len(findings) + 1))

    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(render_markdown(args.artifact_dir, findings), end="")
    if args.output:
        args.output.write_text(
            render_markdown(args.artifact_dir, findings),
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
