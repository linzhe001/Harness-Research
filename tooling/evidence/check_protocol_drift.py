#!/usr/bin/env python3
"""Check whether dynamic research protocol docs need review."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dynamic_context import is_dynamic_context_workspace  # noqa: E402

STAGE_ORDER = {
    "status": 0.0,
    "wf1": 1.0,
    "wf2": 2.0,
    "wf3": 3.0,
    "wf4": 4.0,
    "wf5": 5.0,
    "wf6": 6.0,
    "wf7": 7.0,
    "wf8": 8.0,
    "wf9": 9.0,
    "wf10": 10.0,
    "wf11": 11.0,
    "wf12": 12.0,
}
EMPTY_VALUES = {"", "n/a", "na", "none", "null", "-", "pending"}
APPROVED_VERDICTS = {
    "accepted",
    "approved",
    "pass",
    "passed",
    "current",
    "no_drift",
    "up_to_date",
}
BAD_VERDICTS = {
    "pending",
    "needs_revision",
    "revision_required",
    "stale",
    "drift",
    "rejected",
    "reject",
}


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def is_meaningful(value: str | None) -> bool:
    if value is None:
        return False
    value = value.strip()
    if value.lower() in EMPTY_VALUES:
        return False
    if value.startswith("{") and value.endswith("}"):
        return False
    return True


def header_value(text: str, label: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", re.IGNORECASE)
    for line in text.splitlines()[:64]:
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return None


def bullet_value(text: str, label: str) -> str | None:
    pattern = re.compile(
        rf"^\s*-\s*{re.escape(label)}\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def stage_tokens(text: str) -> list[str]:
    tokens = []
    for match in re.finditer(r"\bWF(12|11|10|[1-9])\b", text, flags=re.IGNORECASE):
        token = f"wf{match.group(1)}".lower()
        if token not in tokens:
            tokens.append(token)
    return tokens


def trigger_reached(trigger: str, stage: str) -> bool:
    if stage == "status":
        return False
    target = STAGE_ORDER[stage]
    tokens = stage_tokens(trigger)
    if not tokens:
        lowered = trigger.lower()
        return any(
            word in lowered
            for word in ["now", "immediate", "before next", "next run", "all", "any"]
        )
    return any(STAGE_ORDER[token] <= target for token in tokens if token in STAGE_ORDER)


def stage_severity(stage: str, *, allow: bool = False) -> str:
    if allow or stage == "status":
        return "warn"
    return "error"


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


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    severity: str,
    detail: str,
    path: str | None = None,
) -> None:
    checks.append(
        {"name": name, "ok": ok, "severity": severity, "detail": detail, "path": path}
    )


def detect_dynamic_mode(workspace_root: Path, state: dict[str, Any]) -> bool:
    return is_dynamic_context_workspace(workspace_root, state)


def check_protocol_review(
    workspace_root: Path,
    stage: str,
    checks: list[dict[str, Any]],
    *,
    allow_review_required: bool,
) -> tuple[str, str]:
    protocol_path = workspace_root / "docs" / "35_protocol" / "Research_Protocol.md"
    review_path = workspace_root / "docs" / "35_protocol" / "Protocol_Review.md"
    protocol_text = read_text_if_exists(protocol_path)
    review_text = read_text_if_exists(review_path)

    if not protocol_path.exists():
        severity = stage_severity(stage)
        add_check(
            checks,
            "research_protocol_exists",
            severity != "error",
            severity,
            "Missing docs/35_protocol/Research_Protocol.md.",
            relpath(protocol_path, workspace_root),
        )
        return protocol_text, review_text
    add_check(
        checks,
        "research_protocol_exists",
        True,
        "info",
        "Research Protocol exists.",
        relpath(protocol_path, workspace_root),
    )

    review_required = (
        (header_value(protocol_text, "Review required") or "").strip().lower()
    )
    if review_required in {"yes", "true", "required"}:
        severity = stage_severity(stage, allow=allow_review_required)
        add_check(
            checks,
            "protocol_review_required",
            severity != "error",
            severity,
            "Research_Protocol.md says review is required.",
            relpath(protocol_path, workspace_root),
        )
    elif review_required in {"no", "false", "not required", "done"}:
        add_check(
            checks,
            "protocol_review_required",
            True,
            "info",
            "Research_Protocol.md does not require review.",
            relpath(protocol_path, workspace_root),
        )
    else:
        add_check(
            checks,
            "protocol_review_required",
            True,
            "warn",
            "Research_Protocol.md has no clear Review required header.",
            relpath(protocol_path, workspace_root),
        )

    if not review_path.exists():
        severity = stage_severity(stage)
        add_check(
            checks,
            "protocol_review_exists",
            severity != "error",
            severity,
            "Missing docs/35_protocol/Protocol_Review.md.",
            relpath(review_path, workspace_root),
        )
        return protocol_text, review_text

    verdict = (
        (
            bullet_value(review_text, "Verdict")
            or header_value(review_text, "Verdict")
            or ""
        )
        .strip()
        .lower()
        .replace(" ", "_")
    )
    if verdict in APPROVED_VERDICTS:
        add_check(
            checks,
            "protocol_review_verdict",
            True,
            "info",
            f"Protocol review verdict is {verdict}.",
            relpath(review_path, workspace_root),
        )
    elif verdict in BAD_VERDICTS or not is_meaningful(verdict):
        severity = stage_severity(stage)
        add_check(
            checks,
            "protocol_review_verdict",
            severity != "error",
            severity,
            f"Protocol review verdict is {verdict or 'missing'!r}.",
            relpath(review_path, workspace_root),
        )
    else:
        severity = stage_severity(stage)
        add_check(
            checks,
            "protocol_review_verdict",
            severity != "error",
            severity,
            f"Protocol review verdict is unrecognized: {verdict!r}.",
            relpath(review_path, workspace_root),
        )

    return protocol_text, review_text


def check_open_questions(
    workspace_root: Path, stage: str, checks: list[dict[str, Any]]
) -> None:
    path = workspace_root / "docs" / "30_evidence" / "Open_Questions.md"
    if not path.exists():
        add_check(
            checks,
            "open_questions_file",
            True,
            "warn",
            "Missing docs/30_evidence/Open_Questions.md; "
            "cannot check evidence blockers.",
            relpath(path, workspace_root),
        )
        return
    rows = parse_markdown_tables(read_text_if_exists(path))
    blockers: list[str] = []
    active_unstaged: list[str] = []
    for row in rows:
        question_id = row.get("id", "")
        question = row.get("question", "")
        next_evidence = row.get("next_evidence", "")
        blocking_stage = row.get("blocking_stage", "")
        if not (
            is_meaningful(question_id)
            and (is_meaningful(question) or is_meaningful(next_evidence))
        ):
            continue
        if trigger_reached(blocking_stage, stage):
            blockers.append(question_id)
        elif not stage_tokens(blocking_stage):
            active_unstaged.append(question_id)
    if blockers:
        severity = stage_severity(stage)
        add_check(
            checks,
            "blocking_open_questions",
            severity != "error",
            severity,
            f"Open questions block {stage}: {', '.join(blockers)}.",
            relpath(path, workspace_root),
        )
    else:
        add_check(
            checks,
            "blocking_open_questions",
            True,
            "info",
            f"No open questions block {stage}.",
            relpath(path, workspace_root),
        )
    if active_unstaged:
        add_check(
            checks,
            "unstaged_open_questions",
            True,
            "warn",
            f"Open questions have no blocking stage: {', '.join(active_unstaged)}.",
            relpath(path, workspace_root),
        )


def check_assumptions(
    workspace_root: Path, stage: str, checks: list[dict[str, Any]]
) -> None:
    path = workspace_root / "docs" / "35_protocol" / "Protocol_Assumptions.md"
    if not path.exists():
        add_check(
            checks,
            "protocol_assumptions_file",
            True,
            "warn",
            "Missing docs/35_protocol/Protocol_Assumptions.md; "
            "cannot check assumption review triggers.",
            relpath(path, workspace_root),
        )
        return
    rows = parse_markdown_tables(read_text_if_exists(path))
    overdue_low: list[str] = []
    overdue_medium: list[str] = []
    for index, row in enumerate(rows, start=1):
        assumption = row.get("assumption", "")
        confidence = row.get("confidence", "").lower()
        trigger = row.get("review_trigger", "")
        if not is_meaningful(assumption):
            continue
        if not trigger_reached(trigger, stage):
            continue
        label = assumption if len(assumption) <= 80 else assumption[:77] + "..."
        if "low" in confidence or not is_meaningful(confidence):
            overdue_low.append(label or f"row {index}")
        elif "medium" in confidence:
            overdue_medium.append(label or f"row {index}")
    if overdue_low:
        severity = stage_severity(stage)
        add_check(
            checks,
            "low_confidence_assumptions_due",
            severity != "error",
            severity,
            "Low-confidence assumptions need review: " + "; ".join(overdue_low),
            relpath(path, workspace_root),
        )
    else:
        add_check(
            checks,
            "low_confidence_assumptions_due",
            True,
            "info",
            f"No low-confidence assumptions are due by {stage}.",
            relpath(path, workspace_root),
        )
    if overdue_medium:
        add_check(
            checks,
            "medium_confidence_assumptions_due",
            True,
            "warn",
            "Medium-confidence assumptions are due for review: "
            + "; ".join(overdue_medium),
            relpath(path, workspace_root),
        )


def negative_result_ids(text: str) -> list[str]:
    ids = [
        match.group(1).strip()
        for match in re.finditer(
            r"^\s*-\s*ID:\s*(.+?)\s*$", text, flags=re.IGNORECASE | re.MULTILINE
        )
        if is_meaningful(match.group(1))
    ]
    if ids:
        return ids
    hypotheses = [
        match.group(1).strip()
        for match in re.finditer(
            r"^\s*-\s*Hypothesis:\s*(.+?)\s*$", text, flags=re.IGNORECASE | re.MULTILINE
        )
        if is_meaningful(match.group(1))
    ]
    return [f"anonymous:{index}" for index, _ in enumerate(hypotheses, start=1)]


def check_negative_results(
    workspace_root: Path,
    stage: str,
    checks: list[dict[str, Any]],
    review_text: str,
    *,
    allow_unreviewed_negative: bool,
) -> None:
    path = workspace_root / "docs" / "50_memory" / "Negative_Results.md"
    if not path.exists():
        add_check(
            checks,
            "negative_results_file",
            True,
            "info",
            "No Negative_Results.md file found.",
            relpath(path, workspace_root),
        )
        return
    negative_text = read_text_if_exists(path)
    ids = negative_result_ids(negative_text)
    if not ids:
        add_check(
            checks,
            "unreviewed_negative_results",
            True,
            "info",
            "No concrete negative results recorded.",
            relpath(path, workspace_root),
        )
        return
    changelog_text = read_text_if_exists(
        workspace_root / "docs" / "35_protocol" / "Protocol_Changelog.md"
    )
    review_surface = f"{review_text}\n{changelog_text}"
    missing = [
        item
        for item in ids
        if item.startswith("anonymous:") or item not in review_surface
    ]
    if missing:
        severity = stage_severity(stage, allow=allow_unreviewed_negative)
        add_check(
            checks,
            "unreviewed_negative_results",
            severity != "error",
            severity,
            "Negative results are not referenced in Protocol_Review or "
            "Protocol_Changelog: "
            + ", ".join(missing),
            relpath(path, workspace_root),
        )
    else:
        add_check(
            checks,
            "unreviewed_negative_results",
            True,
            "info",
            "All negative result IDs are referenced by protocol review/changelog.",
            relpath(path, workspace_root),
        )


def latest_iteration_signal(
    iteration_log: dict[str, Any],
) -> tuple[str | None, str | None]:
    iterations = iteration_log.get("iterations")
    if not isinstance(iterations, list) or not iterations:
        return None, None
    latest = iterations[-1]
    if not isinstance(latest, dict):
        return None, None
    iteration_id = latest.get("id")
    decision = latest.get("decision")
    return (
        str(iteration_id) if iteration_id is not None else None,
        str(decision) if decision is not None else None,
    )


def check_iteration_decision(
    workspace_root: Path, stage: str, checks: list[dict[str, Any]], review_text: str
) -> None:
    path = workspace_root / "iteration_log.json"
    iteration_log = load_json_if_exists(path)
    if not iteration_log:
        add_check(
            checks,
            "iteration_decision_protocol_drift",
            True,
            "info",
            "No iteration_log.json found.",
            relpath(path, workspace_root),
        )
        return
    iteration_id, decision = latest_iteration_signal(iteration_log)
    if decision not in {"PIVOT", "ABORT"}:
        detail = (
            "Latest iteration decision does not force protocol review: "
            f"{decision or 'none'}."
        )
        add_check(
            checks,
            "iteration_decision_protocol_drift",
            True,
            "info",
            detail,
            relpath(path, workspace_root),
        )
        return
    changelog_text = read_text_if_exists(
        workspace_root / "docs" / "35_protocol" / "Protocol_Changelog.md"
    )
    review_surface = f"{review_text}\n{changelog_text}"
    token = iteration_id or decision
    if token and token in review_surface:
        add_check(
            checks,
            "iteration_decision_protocol_drift",
            True,
            "info",
            f"{decision} decision is referenced by protocol review/changelog.",
            relpath(path, workspace_root),
        )
    else:
        severity = stage_severity(stage)
        add_check(
            checks,
            "iteration_decision_protocol_drift",
            severity != "error",
            severity,
            f"Latest iteration decision {decision} should trigger protocol review.",
            relpath(path, workspace_root),
        )


def gate_result(
    workspace_root: Path,
    *,
    stage: str = "status",
    allow_review_required: bool = False,
    allow_unreviewed_negative: bool = False,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    stage = stage.lower()
    if stage not in STAGE_ORDER:
        raise ValueError(f"unknown stage: {stage}")
    state = load_json_if_exists(workspace / "PROJECT_STATE.json")
    dynamic = detect_dynamic_mode(workspace, state)
    checks: list[dict[str, Any]] = []

    if not dynamic:
        add_check(
            checks,
            "legacy_or_no_dynamic_protocol",
            True,
            "info",
            "Dynamic protocol docs are not active; protocol drift gate is not active.",
        )
    else:
        _, review_text = check_protocol_review(
            workspace,
            stage,
            checks,
            allow_review_required=allow_review_required,
        )
        check_open_questions(workspace, stage, checks)
        check_assumptions(workspace, stage, checks)
        check_negative_results(
            workspace,
            stage,
            checks,
            review_text,
            allow_unreviewed_negative=allow_unreviewed_negative,
        )
        check_iteration_decision(workspace, stage, checks, review_text)

    errors = [
        check for check in checks if check["severity"] == "error" and not check["ok"]
    ]
    warnings = [check for check in checks if check["severity"] == "warn"]
    return {
        "ok": not errors,
        "stage": stage,
        "dynamic_protocol": dynamic,
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def print_text(result: dict[str, Any]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print(
        f"{status} protocol drift gates for {result['stage']} "
        f"(dynamic={result['dynamic_protocol']})"
    )
    for check in result["checks"]:
        marker = "OK" if check["ok"] else "NO"
        path = f" {check['path']}" if check.get("path") else ""
        print(
            f"- [{marker}] {check['severity']}: {check['name']}{path} - "
            f"{check['detail']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Harness dynamic protocol drift signals."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=sorted(STAGE_ORDER), default="status")
    parser.add_argument(
        "--allow-review-required",
        action="store_true",
        help="Warn instead of fail when Research_Protocol.md says review is required.",
    )
    parser.add_argument(
        "--allow-unreviewed-negative",
        action="store_true",
        help=(
            "Warn instead of fail when negative results are not referenced by "
            "protocol review/changelog."
        ),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = gate_result(
            args.workspace_root,
            stage=args.stage,
            allow_review_required=args.allow_review_required,
            allow_unreviewed_negative=args.allow_unreviewed_negative,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_text(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
