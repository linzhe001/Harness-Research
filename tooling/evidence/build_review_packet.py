#!/usr/bin/env python3
"""Build a concise human review packet for dynamic-context gates."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_context_gates  # noqa: E402
import check_docchain_gates  # noqa: E402
import check_protocol_drift  # noqa: E402
import check_workflow_state  # noqa: E402

STAGE_TO_CONTEXT_STAGE = {
    "status": "status",
    "wf5": "wf5-eval-contract",
    "wf10": "wf10-auto",
    "wf11": "wf11",
    "wf12": "wf12",
}
STAGE_TO_PROTOCOL_STAGE = {
    "status": "status",
    "wf5": "wf5",
    "wf10": "wf10",
    "wf11": "wf11",
    "wf12": "wf12",
}
CANONICAL_STAGES = {"status", "wf5", "wf10", "wf11", "wf12"}


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def build_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def generated_at() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def run_git(workspace_root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace_root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def git_context(workspace_root: Path) -> dict[str, Any]:
    status = run_git(workspace_root, ["status", "--short"])
    return {
        "commit": run_git(workspace_root, ["rev-parse", "HEAD"]),
        "branch": run_git(workspace_root, ["branch", "--show-current"]),
        "is_dirty": bool(status),
        "status_summary": status or "",
    }


def collect_failed_checks(result: dict[str, Any], gate: str) -> list[dict[str, str]]:
    failed = []
    for check in result.get("checks", []):
        severity = str(check.get("severity", "info"))
        ok = bool(check.get("ok", False))
        if severity == "info" and ok:
            continue
        if ok and severity != "warn":
            continue
        failed.append(
            {
                "gate": gate,
                "name": str(check.get("name", "unknown")),
                "severity": severity,
                "detail": str(check.get("detail", "")),
                "path": str(check.get("path") or check.get("doc_path") or ""),
            }
        )
    return failed


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", " ") for cell in row) + " |")
    return lines


def open_questions(workspace_root: Path) -> list[dict[str, str]]:
    path = workspace_root / "docs" / "30_evidence" / "Open_Questions.md"
    if not path.exists():
        return []
    rows = check_protocol_drift.parse_markdown_tables(path.read_text(encoding="utf-8", errors="replace"))
    result = []
    for row in rows:
        question_id = row.get("id", "").strip()
        question = row.get("question", "").strip()
        next_evidence = row.get("next_evidence", "").strip()
        if not (check_protocol_drift.is_meaningful(question_id) and (check_protocol_drift.is_meaningful(question) or check_protocol_drift.is_meaningful(next_evidence))):
            continue
        result.append(
            {
                "id": question_id,
                "question": question,
                "blocking_stage": row.get("blocking_stage", "").strip(),
                "next_evidence": next_evidence,
            }
        )
    return result


def protocol_changelog_rows(workspace_root: Path) -> list[dict[str, str]]:
    path = workspace_root / "docs" / "35_protocol" / "Protocol_Changelog.md"
    if not path.exists():
        return []
    rows = check_protocol_drift.parse_markdown_tables(path.read_text(encoding="utf-8", errors="replace"))
    return rows[-5:]


def evidence_sources(workspace_root: Path) -> list[list[str]]:
    candidates = [
        ("docs/context/contracts.md", "Dynamic-context-v2 contracts"),
        ("docs/context/facts.md", "Dynamic-context-v2 current facts"),
        ("docs/context/evidence.md", "Dynamic-context-v2 evidence index"),
        ("docs/context/protocol.md", "Dynamic-context-v2 protocol draft"),
        ("docs/context/experiments.md", "Dynamic-context-v2 experiment queue and research wiki"),
        ("docs/context/memory.md", "Dynamic-context-v2 decisions and lesson candidates"),
        ("docs/30_evidence/Evidence_Index.md", "Evidence index and table inventory"),
        ("docs/30_evidence/Metric_Table.md", "Metric candidates and known issues"),
        ("docs/30_evidence/Baseline_Table.md", "Baseline candidates and reproduction status"),
        ("docs/30_evidence/Open_Questions.md", "Unresolved evidence blockers"),
        ("docs/35_protocol/Research_Protocol.md", "Current dynamic protocol draft"),
        ("docs/35_protocol/Protocol_Review.md", "Protocol review verdict and checks"),
        ("docs/10_contract/Project_Contract.md", "Project execution boundary"),
        ("docs/10_contract/Evaluation_Contract.md", "Evaluation approval surface"),
        ("docs/10_contract/Baseline_Contract.md", "Baseline reproduction and skip boundary"),
        ("docs/10_contract/Claim_Boundary.md", "Release claim boundary"),
    ]
    rows = []
    for relative, why in candidates:
        exists = (workspace_root / relative).exists()
        rows.append([relative, why, "yes" if exists else "missing"])
    return rows


def contract_rows(context_result: dict[str, Any]) -> list[list[str]]:
    rows = []
    contracts = context_result.get("contracts", {})
    if not isinstance(contracts, dict):
        return rows
    for key in ["project_contract", "evaluation_contract", "baseline_contract", "claim_boundary"]:
        info = contracts.get(key, {})
        if not isinstance(info, dict):
            continue
        rows.append(
            [
                key,
                str(info.get("status", "missing")),
                "yes" if info.get("exists") else "no",
                str(info.get("path", "")),
                "yes" if info.get("operator_accepted_draft") else "no",
            ]
        )
    return rows


def packet_title(stage: str) -> str:
    labels = {
        "status": "Dynamic Context Status",
        "wf5": "WF5 Evaluation Contract",
        "wf10": "WF10 Auto-Iteration Readiness",
        "wf11": "WF11 Final Experiment Readiness",
        "wf12": "WF12 Release Claim Readiness",
    }
    return labels.get(stage, stage)


def review_applicability(
    context: dict[str, Any],
    drift: dict[str, Any],
    docchain: dict[str, Any],
) -> str:
    if context.get("dynamic_context") or drift.get("dynamic_protocol") or docchain.get("dynamic_docchain"):
        return "dynamic_context"
    return "not_applicable_legacy_or_empty"


def render_packet(packet: dict[str, Any]) -> str:
    stage = packet["stage"]
    ready = "yes" if packet["ready_for_human_approval"] else "no"
    applicable = packet.get("review_applicability", "dynamic_context")
    if applicable == "dynamic_context":
        decision_text = "Approve, approve with edits, or reject the current contract/protocol readiness."
    else:
        decision_text = "No dynamic-context approval decision is active; use this packet as a status note only."
    lines = [
        f"# Review Packet - {packet_title(stage)}",
        "",
        f"Generated: {packet['generated_at']}",
        f"Stage: {stage}",
        f"Review applicability: {applicable}",
        f"Ready for human approval: {ready}",
        "",
        "## Decision Needed",
        "",
        decision_text,
        "",
        "## Approval Recording",
        "",
        "If a human explicitly approves a specific contract, record it with `tooling/evidence/approve_contract.py` and then rerun this gate. Do not approve from this packet alone.",
        "",
        "```bash",
        "python tooling/evidence/approve_contract.py --workspace-root . \\",
        "  --contract <project_contract|evaluation_contract|baseline_contract|claim_boundary> \\",
        "  --approved-by \"<human reviewer>\" \\",
        f"  --approval-source \"{packet['paths']['markdown']}\"",
        f"python tooling/evidence/check_dynamic_context.py --workspace-root . --stage {stage} --review-packet",
        "```",
        "",
        "## Gate Summary",
        "",
        *markdown_table(
            ["Gate", "Result", "Errors", "Warnings"],
            [
                ["context", "PASS" if packet["gates"]["context"]["ok"] else "FAIL", str(packet["gates"]["context"]["error_count"]), str(packet["gates"]["context"]["warning_count"])],
                ["protocol_drift", "PASS" if packet["gates"]["protocol_drift"]["ok"] else "FAIL", str(packet["gates"]["protocol_drift"]["error_count"]), str(packet["gates"]["protocol_drift"]["warning_count"])],
                ["docchain", "PASS" if packet["gates"]["docchain"]["ok"] else "FAIL", str(packet["gates"]["docchain"]["error_count"]), str(packet["gates"]["docchain"]["warning_count"])],
                ["workflow_state", "PASS" if packet["gates"]["workflow_state"]["ok"] else "FAIL", str(packet["gates"]["workflow_state"]["error_count"]), str(packet["gates"]["workflow_state"]["warning_count"])],
            ],
        ),
        "",
        "## Proposed Contract Surface",
        "",
        *markdown_table(["Contract", "Status", "Exists", "Path", "Draft Accepted"], packet["contract_rows"] or [["N/A", "missing", "no", "", "no"]]),
        "",
        "## Evidence Used",
        "",
        *markdown_table(["Source", "Why It Matters", "Exists"], packet["evidence_sources"]),
        "",
        "## Blocking Items",
        "",
    ]
    if packet["blocking_items"]:
        for item in packet["blocking_items"]:
            path = f" ({item['path']})" if item.get("path") else ""
            lines.append(f"- [{item['gate']}:{item['severity']}] {item['name']}{path}: {item['detail']}")
    else:
        lines.append("- None recorded by gates.")

    lines.extend(["", "## Open Questions", ""])
    if packet["open_questions"]:
        for item in packet["open_questions"]:
            lines.append(f"- {item['id']}: {item['question']} Blocking: {item['blocking_stage'] or 'unspecified'}. Next evidence: {item['next_evidence'] or 'N/A'}.")
    else:
        lines.append("- None recorded in docs/30_evidence/Open_Questions.md.")

    lines.extend(["", "## What Changed Since Last Review", ""])
    if packet["changelog_rows"]:
        rows = [
            [
                row.get("date", ""),
                row.get("change", ""),
                row.get("reason", ""),
                row.get("evidence", ""),
                row.get("reviewer", ""),
            ]
            for row in packet["changelog_rows"]
        ]
        lines.extend(markdown_table(["Date", "Change", "Reason", "Evidence", "Reviewer"], rows))
    else:
        lines.append("- No protocol changelog rows found.")

    lines.extend(
        [
            "",
            "## Human Action",
            "",
            "- Reviewer:",
            "- Decision:",
            "- Contract to record:",
            "- Approval note:",
            "",
            "- [ ] Approve",
            "- [ ] Approve with edits",
            "- [ ] Reject and return to protocol/evidence",
            "",
            "Approval must be explicit in the current conversation before any contract is marked approved.",
            "",
        ]
    )
    return "\n".join(lines)


def build_review_packet(
    workspace_root: Path,
    *,
    stage: str = "status",
    build_id_override: str | None = None,
    dry_run: bool = False,
    context_result: dict[str, Any] | None = None,
    drift_result: dict[str, Any] | None = None,
    docchain_result: dict[str, Any] | None = None,
    workflow_state_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    if stage not in STAGE_TO_CONTEXT_STAGE:
        raise ValueError(f"unsupported review packet stage: {stage}")
    current_build_id = build_id_override or build_id()
    output_dir = workspace / ".evidence" / "review_packets" / stage / current_build_id

    context = context_result or check_context_gates.gate_result(workspace, stage=STAGE_TO_CONTEXT_STAGE[stage])
    drift = drift_result or check_protocol_drift.gate_result(workspace, stage=STAGE_TO_PROTOCOL_STAGE[stage])
    docchain = docchain_result or check_docchain_gates.gate_result(workspace)
    workflow_state = workflow_state_result or check_workflow_state.gate_result(workspace)
    applicability = review_applicability(context, drift, docchain)

    blocking_items = (
        collect_failed_checks(context, "context")
        + collect_failed_checks(drift, "protocol_drift")
        + collect_failed_checks(docchain, "docchain")
        + collect_failed_checks(workflow_state, "workflow_state")
    )
    packet = {
        "schema_version": "0.1",
        "stage": stage,
        "generated_at": generated_at(),
        "build_id": current_build_id,
        "git": git_context(workspace),
        "review_applicability": applicability,
        "ready_for_human_approval": applicability == "dynamic_context" and context["ok"] and drift["ok"] and docchain["ok"] and workflow_state["ok"],
        "gates": {
            "context": context,
            "protocol_drift": drift,
            "docchain": docchain,
            "workflow_state": workflow_state,
        },
        "contract_rows": contract_rows(context),
        "evidence_sources": evidence_sources(workspace),
        "blocking_items": blocking_items,
        "open_questions": open_questions(workspace),
        "changelog_rows": protocol_changelog_rows(workspace),
        "paths": {
            "markdown": relpath(output_dir / "review_packet.md", workspace),
            "json": relpath(output_dir / "review_packet.json", workspace),
        },
    }
    markdown = render_packet(packet)

    if not dry_run:
        atomic_write_text(output_dir / "review_packet.md", markdown)
        atomic_write_json(output_dir / "review_packet.json", packet)

    return {
        "ok": True,
        "ready_for_human_approval": packet["ready_for_human_approval"],
        "stage": stage,
        "build_id": current_build_id,
        "output_dir": relpath(output_dir, workspace),
        "markdown_path": packet["paths"]["markdown"],
        "json_path": packet["paths"]["json"],
        "blocking_count": len(blocking_items),
        "open_question_count": len(packet["open_questions"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a concise Harness human review packet.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=sorted(CANONICAL_STAGES), default="status")
    parser.add_argument("--build-id", dest="build_id_override")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        summary = build_review_packet(
            args.workspace_root,
            stage=args.stage,
            build_id_override=args.build_id_override,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        ready = "ready" if summary["ready_for_human_approval"] else "needs_review"
        print(f"Built review packet: {ready} {summary['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
