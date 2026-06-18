#!/usr/bin/env python3
"""Compile a draft dynamic protocol from evidence tables."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

CONTEXT_EVIDENCE_PATH = Path("docs/context/evidence.md")
CONTEXT_PROTOCOL_PATH = Path("docs/context/protocol.md")
LEGACY_EVIDENCE_DIR = Path("docs/30_evidence")
PLACEHOLDER_VALUES = {
    "",
    "n/a",
    "na",
    "none",
    "null",
    "-",
    "candidate",
    "unknown",
    "low/medium/high",
    "maximize/minimize",
    "train/val/test/reference",
    "wf2/wf5/wf10/wf12",
    "paper/repo/dataset/benchmark/metric",
}


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def build_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def split_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    columns = [cell.strip() for cell in stripped.strip("|").split("|")]
    if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in columns):
        return None
    return columns


def normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.lower()).strip("_")


def parse_markdown_tables(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        if not line.strip():
            header = None
            continue
        columns = split_table_row(line)
        if columns is None:
            continue
        if header is None:
            header = [normalize_header(column) for column in columns]
            continue
        if len(columns) != len(header):
            continue
        rows.append(dict(zip(header, columns)))
    return rows


def is_meaningful(value: str | None) -> bool:
    if value is None:
        return False
    cleaned = value.strip()
    if cleaned.lower() in PLACEHOLDER_VALUES:
        return False
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return False
    return True


def row_has_content(row: dict[str, str], keys: list[str]) -> bool:
    return any(is_meaningful(row.get(key)) for key in keys)


def load_table(workspace_root: Path, relative: str, content_keys: list[str]) -> list[dict[str, str]]:
    path = workspace_root / relative
    if not path.exists():
        return []
    rows = parse_markdown_tables(path.read_text(encoding="utf-8", errors="replace"))
    result: list[dict[str, str]] = []
    for row in rows:
        if row_has_content(row, content_keys):
            row["_source_path"] = relative
            result.append(row)
    return result


def value(row: dict[str, str], key: str, default: str = "TBD") -> str:
    item = row.get(key, "").strip()
    return item if is_meaningful(item) else default


def evidence_ref(row: dict[str, str]) -> str:
    source = row.get("_source_path", "")
    identifier = row.get("id", "").strip()
    if is_meaningful(identifier):
        return f"{source}#{identifier}"
    return source or "TBD"


def pipe_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def table_row(values: list[str]) -> str:
    return "| " + " | ".join(pipe_escape(item) for item in values) + " |"


def open_question_bullets(rows: list[dict[str, str]]) -> list[str]:
    bullets = []
    for row in rows:
        identifier = value(row, "id", "open")
        question = value(row, "question", "Unspecified question")
        blocking = value(row, "blocking_stage", "review")
        bullets.append(f"- [U:{identifier}] {question} Blocking stage: {blocking}.")
    return bullets or ["- [U:protocol.open] No explicit open question rows found; human review still required before contract approval."]


def confidence_from_text(*parts: str) -> str:
    lowered = " ".join(parts).lower()
    if "high" in lowered or "verified" in lowered or "reproduced" in lowered:
        return "high"
    if "medium" in lowered or "partial" in lowered:
        return "medium"
    return "low"


def protocol_docs(tables: dict[str, list[dict[str, str]]], *, generated_date: str) -> dict[str, str]:
    baselines = tables["baselines"]
    metrics = tables["metrics"]
    datasets = tables["datasets"]
    papers = tables["papers"]
    questions = tables["questions"]

    baseline_rows = [
        table_row(
            [
                value(row, "baseline", value(row, "source", "TBD")),
                value(row, "why_relevant", value(row, "notes", "Needs review")),
                evidence_ref(row),
                value(row, "repro_status", "candidate"),
            ]
        )
        for row in baselines
    ] or [table_row(["TBD", "No baseline evidence rows found", "docs/context/evidence.md", "candidate"])]

    metric_rows = [
        table_row(
            [
                value(row, "metric", "TBD"),
                value(row, "direction", "TBD"),
                value(row, "measures", "Needs review"),
                value(row, "known_issues", "None recorded"),
                evidence_ref(row),
            ]
        )
        for row in metrics
    ] or [table_row(["TBD", "TBD", "No metric evidence rows found", "Needs review", "docs/context/evidence.md"])]

    dataset_rows = [
        table_row(
            [
                value(row, "dataset", "TBD"),
                value(row, "role", "TBD"),
                value(row, "split_eval_notes", "Needs review"),
                value(row, "license_risk", "Needs review"),
                evidence_ref(row),
            ]
        )
        for row in datasets
    ] or [table_row(["TBD", "TBD", "No dataset evidence rows found", "Needs review", "docs/context/evidence.md"])]

    failure_rows: list[str] = []
    for row in papers:
        limitations = value(row, "limitations", "")
        if is_meaningful(limitations):
            failure_rows.append(table_row([limitations, "Review against project setting", evidence_ref(row), "Record mitigation before contract approval"]))
    for row in metrics:
        known_issues = value(row, "known_issues", "")
        if is_meaningful(known_issues):
            failure_rows.append(table_row([known_issues, f"Monitor metric {value(row, 'metric', 'TBD')}", evidence_ref(row), "Do not over-claim metric meaning"]))
    for row in questions:
        failure_rows.append(table_row([value(row, "question", "Open question"), value(row, "blocking_stage", "review"), evidence_ref(row), value(row, "next_evidence", "Collect more evidence")]))
    if not failure_rows:
        failure_rows = [table_row(["No explicit failure evidence rows found", "Human review", "docs/context/evidence.md", "Keep as open risk until reviewed"])]

    high = sum(1 for row in papers + baselines if confidence_from_text(*row.values()) == "high")
    medium = sum(1 for row in papers + baselines + metrics if confidence_from_text(*row.values()) == "medium")
    low = max(0, len(papers + baselines + metrics + datasets + questions) - high - medium)

    research_protocol = "\n".join(
        [
            "# Research Protocol",
            "",
            "Status: draft",
            "Context doc: protocol",
            "Context model: dynamic-context-v2",
            "Evidence base: `docs/context/evidence.md` plus legacy `docs/30_evidence/**` when present",
            "Evidence chain: N/A",
            "Evidence audit: N/A",
            "Audit result: N/A",
            "Review required: yes",
            "Generated by: `tooling/evidence/compile_protocol.py`",
            "",
            "## Current Answer",
            "",
            "This is an AI-generated protocol draft compiled from evidence tables. Treat all",
            "items as project-local candidates until protocol review and human-approved",
            "contracts settle execution authority.",
            "",
            "## Task Formulation",
            "",
            "- Input: TBD from project facts and evidence.",
            "- Output: TBD from project facts and evidence.",
            "- Unit of evaluation: TBD from metric and dataset evidence.",
            "- Target use case: TBD from project contract review.",
            "",
            "## Candidate Datasets",
            "",
            "| Dataset | Role | Split/Eval Notes | License/Risk | Evidence |",
            "|---|---|---|---|---|",
            *dataset_rows,
            "",
            "## Candidate Baselines",
            "",
            "| Baseline | Why Relevant | Evidence | Status |",
            "|---|---|---|---|",
            *baseline_rows,
            "",
            "## Candidate Metrics",
            "",
            "| Metric | Direction | What It Measures | Known Issues | Evidence |",
            "|---|---|---|---|---|",
            *metric_rows,
            "",
            "## Failure Modes",
            "",
            "| Failure Mode | Detection | Evidence | Mitigation |",
            "|---|---|---|---|",
            *failure_rows,
            "",
            "## Confidence",
            "",
            f"- High: {high} evidence rows",
            f"- Medium: {medium} evidence rows",
            f"- Low: {low} evidence rows or unresolved questions",
            "",
            "## Open Questions",
            "",
            *open_question_bullets(questions),
            "",
        ]
    )

    assumption_rows: list[str] = []
    for row in baselines:
        assumption_rows.append(
            table_row(
                [
                    f"Baseline {value(row, 'baseline', value(row, 'source', 'TBD'))} is relevant enough to consider.",
                    confidence_from_text(value(row, "repro_status", ""), value(row, "notes", "")),
                    evidence_ref(row),
                    "before WF5",
                ]
            )
        )
    for row in metrics:
        assumption_rows.append(
            table_row(
                [
                    f"Metric {value(row, 'metric', 'TBD')} can be tracked with direction {value(row, 'direction', 'TBD')}.",
                    confidence_from_text(value(row, "known_issues", ""), value(row, "evidence", "")),
                    evidence_ref(row),
                    "before WF5",
                ]
            )
        )
    for row in datasets:
        assumption_rows.append(
            table_row(
                [
                    f"Dataset {value(row, 'dataset', 'TBD')} can serve role {value(row, 'role', 'TBD')}.",
                    confidence_from_text(value(row, "license_risk", ""), value(row, "split_eval_notes", "")),
                    evidence_ref(row),
                    "before WF4",
                ]
            )
        )
    for row in questions:
        assumption_rows.append(
            table_row(
                [
                    f"Open question {value(row, 'id', 'unknown')} must be resolved or accepted.",
                    "low",
                    evidence_ref(row),
                    value(row, "blocking_stage", "before WF5"),
                ]
            )
        )
    if not assumption_rows:
        assumption_rows = [table_row(["No evidence-backed protocol assumptions generated yet", "low", "docs/context/evidence.md", "before WF5"])]

    assumptions = "\n".join(
        [
            "# Protocol Assumptions",
            "",
            "Status: draft",
            "Evidence chain: N/A",
            "Evidence audit: N/A",
            "Audit result: N/A",
            "Generated by: `tooling/evidence/compile_protocol.py`",
            "",
            "| Assumption | Confidence | Evidence | Review Trigger |",
            "|---|---|---|---|",
            *assumption_rows,
            "",
        ]
    )

    required_changes = "Review generated candidates, resolve blocking questions, then compile approved contract drafts."
    if questions:
        required_changes = "Resolve or explicitly accept blocking open questions before contract approval."
    review = "\n".join(
        [
            "# Protocol Review",
            "",
            "Status: draft",
            "Evidence chain: N/A",
            "Evidence audit: N/A",
            "Audit result: N/A",
            "Generated by: `tooling/evidence/compile_protocol.py`",
            "",
            "## Review Summary",
            "",
            "- Verdict: pending",
            f"- Main risk: {len(questions)} open question(s), {low} low-confidence row(s)",
            f"- Required changes: {required_changes}",
            "",
            "Use `accepted`, `approved`, `pass`, `current`, or `no_drift` only after",
            "blocking evidence questions, due assumptions, negative results, and pivot/abort",
            "iteration signals have been reviewed.",
            "",
            "## Checks",
            "",
            "| Check | Result | Evidence | Notes |",
            "|---|---|---|---|",
            table_row(["Evidence coverage", "pending", "docs/context/evidence.md", f"{len(papers) + len(baselines) + len(metrics) + len(datasets)} evidence table row(s) compiled"]),
            table_row(["Metric suitability", "pending", "docs/context/evidence.md", f"{len(metrics)} metric candidate(s)"]),
            table_row(["Baseline coverage", "pending", "docs/context/evidence.md", f"{len(baselines)} baseline candidate(s)"]),
            table_row(["Claim boundary", "pending", "docs/context/contracts.md", "Must be reviewed before release claims"]),
            table_row(["Protocol drift", "pending", "tooling/evidence/check_protocol_drift.py", "Run drift gate before WF5/WF10/WF11/WF12"]),
            "",
        ]
    )

    changelog = "\n".join(
        [
            "# Protocol Changelog",
            "",
            "Status: draft",
            "Evidence chain: N/A",
            "Evidence audit: N/A",
            "Audit result: N/A",
            "Generated by: `tooling/evidence/compile_protocol.py`",
            "",
            "| Date | Change | Reason | Evidence | Reviewer |",
            "|---|---|---|---|---|",
            table_row([generated_date, "Generated dynamic protocol draft", "Compiled from current evidence tables", "docs/context/evidence.md", "AI draft; human review required"]),
            "",
        ]
    )

    context_protocol = "\n\n".join(
        [
            "# Protocol",
            "Context doc: protocol\nContext model: dynamic-context-v2\nStatus: draft\nReview required: yes\nReview verdict: pending\nGenerated by: `tooling/evidence/compile_protocol.py`",
            research_protocol.replace("# Research Protocol", "## Research Protocol", 1),
            assumptions.replace("# Protocol Assumptions", "## Protocol Assumptions", 1),
            review.replace("# Protocol Review", "## Protocol Review", 1),
            changelog.replace("# Protocol Changelog", "## Protocol Changelog", 1),
        ]
    )

    return {
        "protocol.md": context_protocol,
    }


def load_evidence_tables(workspace_root: Path) -> dict[str, list[dict[str, str]]]:
    context_evidence = CONTEXT_EVIDENCE_PATH.as_posix()
    return {
        "papers": load_table(workspace_root, "docs/30_evidence/Paper_Table.md", ["paper", "claim_used", "limitations"]),
        "repos": load_table(workspace_root, "docs/30_evidence/Repo_Table.md", ["repo", "role", "notes"]),
        "datasets": load_table(workspace_root, "docs/30_evidence/Dataset_Table.md", ["dataset", "role", "split_eval_notes", "license_risk", "evidence"]),
        "baselines": load_table(workspace_root, "docs/30_evidence/Baseline_Table.md", ["baseline", "source", "why_relevant", "notes"]),
        "metrics": load_table(workspace_root, "docs/30_evidence/Metric_Table.md", ["metric", "measures", "known_issues", "evidence"]),
        "questions": load_table(workspace_root, context_evidence, ["question", "why_it_matters", "next_evidence"])
        + load_table(workspace_root, "docs/30_evidence/Open_Questions.md", ["question", "why_it_matters", "next_evidence"]),
    }


def destination_root(workspace_root: Path, *, apply: bool, current_build_id: str) -> Path:
    if apply:
        return workspace_root / CONTEXT_PROTOCOL_PATH.parent
    return workspace_root / ".evidence" / "protocol_compiler" / current_build_id / CONTEXT_PROTOCOL_PATH.parent


def compile_protocol(
    workspace_root: Path,
    *,
    apply: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
    build_id_override: str | None = None,
    generated_date: str | None = None,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    current_build_id = build_id_override or build_id()
    current_date = generated_date or today()
    tables = load_evidence_tables(workspace)
    docs = protocol_docs(tables, generated_date=current_date)
    root = destination_root(workspace, apply=apply, current_build_id=current_build_id)

    actions: list[dict[str, str]] = []
    for name, text in docs.items():
        destination = root / name
        if destination.exists() and not overwrite:
            actions.append({"action": "skip_exists", "path": relpath(destination, workspace)})
            continue
        actions.append({"action": "write", "path": relpath(destination, workspace)})
        if not dry_run:
            atomic_write(destination, text)

    summary = {
        "ok": True,
        "mode": "apply" if apply else "draft",
        "build_id": current_build_id,
        "output_root": relpath(root, workspace),
        "table_counts": {key: len(rows) for key, rows in tables.items()},
        "actions": actions,
    }
    if not apply:
        summary["next_step"] = "Review generated draft, then rerun with --apply --overwrite if it should replace docs/context/protocol.md."
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile draft dynamic-context-v2 protocol docs from Harness evidence tables.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="Write to docs/context/protocol.md instead of .evidence/protocol_compiler.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--build-id", dest="build_id_override")
    parser.add_argument("--date", dest="generated_date")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        summary = compile_protocol(
            args.workspace_root,
            apply=args.apply,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            build_id_override=args.build_id_override,
            generated_date=args.generated_date,
        )
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        writes = sum(1 for action in summary["actions"] if action["action"] == "write")
        skips = sum(1 for action in summary["actions"] if action["action"] == "skip_exists")
        print(f"Compiled protocol {summary['mode']}: writes={writes}, skipped={skips}, output={summary['output_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
