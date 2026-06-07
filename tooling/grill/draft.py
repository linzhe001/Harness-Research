#!/usr/bin/env python3
"""Initialize and update draft-only Grill Markdown artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from questions import (
    EXIT_OPTIONS,
    maturity_gap_template,
    question_round,
    render_markdown,
)
from readiness import empty_readiness, validate_readiness
from state import (
    atomic_write_json,
    atomic_write_text,
    load_json,
    read_text_if_exists,
    repo_root,
    resolve_path,
    utc_now,
)

RESEARCH_INTENT = Path("docs/Research_Intent_Draft.md")
ROUND_LOG = Path("docs/Grill_Round_Log.md")
READINESS_PACKET = Path("docs/Execution_Readiness_Packet.md")
READINESS_JSON = Path(".workflow_supervisor/readiness.json")
ROUND_TABLE_MARKER = "| --- | --- | --- | --- | --- | --- |"
LEGACY_ROUND_TABLE_MARKER = "| --- | --- | --- | --- |"
HUMAN_EXIT_PENDING = "pending"
HUMAN_EXIT_OPTIONS = [HUMAN_EXIT_PENDING, *EXIT_OPTIONS]
EXECUTION_INTENT_KEYS = {
    "hf_access_policy",
    "non_hf_registration_policy",
    "external_download_policy",
    "allow_external_downloads",
    "baseline_clone_policy",
    "baseline_clone_scope",
    "dataset_acquisition_scope",
}


def markdown_escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def write_if_allowed(path: Path, text: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    atomic_write_text(path, text)
    return True


def render_maturity_checklist() -> str:
    rows = [
        "| Gap | Status | Blocking Question |",
        "| --- | --- | --- |",
    ]
    for item in maturity_gap_template():
        rows.append(
            "| {key} | {status} | {question} |".format(
                key=markdown_escape_table(item["key"]),
                status=markdown_escape_table(item["status"]),
                question=markdown_escape_table(item["blocking_question"]),
            )
        )
    return "\n".join(rows)


def first_question_for_lens(lens: str) -> str:
    payload = question_round(lens, max_questions=1)
    questions = payload.get("questions", [])
    if not questions:
        raise ValueError(f"Grill lens {lens!r} did not produce a question")
    question = questions[0].get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Grill lens {lens!r} produced an empty question")
    return question.strip()


def replace_markdown_section(text: str, heading: str, body: str) -> str:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line == heading), None)
    body_lines = ["", *body.rstrip().splitlines(), ""]
    if start is None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend([heading, *body_lines])
        return "\n".join(lines).rstrip() + "\n"

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    updated = [*lines[: start + 1], *body_lines, *lines[end:]]
    return "\n".join(updated).rstrip() + "\n"


def render_current_gap_check(
    *,
    gap_check: str,
    next_question: str,
    exit_recommendation: str,
) -> str:
    return "\n".join(
        [
            f"- latest_gap: {gap_check}",
            f"- next_question: {next_question}",
            f"- exit_recommendation: `{exit_recommendation}`",
        ]
    )


def render_human_exit_decision(decision: str) -> str:
    lines = [
        f"`{decision}`",
        "",
        "Valid decisions:",
        "",
    ]
    for option in HUMAN_EXIT_OPTIONS:
        if option == HUMAN_EXIT_PENDING:
            continue
        lines.append(f"- `{option}`")
    return "\n".join(lines)


def append_table_row(text: str, marker: str, row: str) -> str:
    lines = text.splitlines()
    try:
        marker_index = lines.index(marker)
    except ValueError as exc:
        raise ValueError("Grill rounds table marker is missing") from exc
    insert_at = marker_index + 1
    while insert_at < len(lines) and lines[insert_at].startswith("|"):
        insert_at += 1
    lines.insert(insert_at, row)
    return "\n".join(lines).rstrip() + "\n"


def render_intent(seed: str, lens: str) -> str:
    questions = render_markdown(question_round(lens)).replace("## ", "### ")
    seed_summary = markdown_escape_table(seed or "Pending Grill intake.")
    fallback_intent = (
        "Record the current research direction, candidate hypothesis, expected "
        "evaluation surface, constraints, and reasons to continue, pivot, or "
        "abandon."
    )
    return f"""# Research Intent Draft

Status: draft
Updated: {utc_now()}

## Evidence Sources

| Source | Why It Was Read | Key Facts Used |
| --- | --- | --- |
| operator input | Seed idea and constraints | {seed_summary} |

## Verified Facts

- None yet. Add only facts grounded in current Source Artifacts.

## Inferences

- None yet.

## Problem

Pending. Grill should make the concrete problem explicit before execution.

## Operator Observation

{seed or "Pending operator answer."}

## Candidate Claim

Pending. Do not promote a claim until the operator has bounded it.

## Minimal Hypothesis

Pending. State the smallest hypothesis that can be tested.

## Why This Is Worth Testing

Pending. Record why this is worth spending data, compute, and review effort.

## Target Metric / Evaluation Signal

Pending.

## Baselines And Negative Controls

Pending.

## Dataset And Compute Assumptions

Pending.

## Forbidden Directions

Pending.

## Pivot / Abort Conditions

Pending.

## Human Exit Decision

Pending operator decision. Valid decisions:

- `continue_grill`
- `grill_draft_ready`
- `bridge_wf1_wf3`
- `pivot`
- `abandon`

## Grill Maturity Checklist

{render_maturity_checklist()}

## Open Questions

- What observation motivates this project?
- What claim should this project avoid until evidence exists?

## Draft Intent

{seed or fallback_intent}

## Grill Questions

{questions}
## Boundary Notes

This draft is not an Approved Contract and does not complete WF1-WF3 by itself.
"""


def render_round_log(seed: str, lens: str) -> str:
    focus = lens
    summary = seed or "pending"
    next_question = first_question_for_lens(lens)
    round_header = (
        "| Round | Lens | Operator Answer Summary | Gap Check | Next Question | "
        "Exit Recommendation |"
    )
    first_round = (
        f"| 1 | {markdown_escape_table(focus)} | "
        f"{markdown_escape_table(summary)} | pending | "
        f"{markdown_escape_table(next_question)} | `continue_grill` |"
    )
    return f"""# Grill Round Log

Status: draft
Updated: {utc_now()}

## Round Contract

Each round must leave:

- operator answer summary
- skeptic / methodologist / implementation or claim-boundary gap
- next blocking question
- exit recommendation
- human exit decision status

## Rounds

{round_header}
| --- | --- | --- | --- | --- | --- |
{first_round}

## Current Gap Check

- latest_gap: pending
- next_question: {next_question}
- exit_recommendation: `continue_grill`

## Human Exit Decision

`pending`

Valid decisions:

- `continue_grill`
- `grill_draft_ready`
- `bridge_wf1_wf3`
- `pivot`
- `abandon`

## Gate Ledger

- command: tooling/grill/draft.py init
- result: PASS
- reason: initialized draft-only Grill artifacts
- artifacts: docs/Research_Intent_Draft.md; docs/Grill_Round_Log.md;
  docs/Execution_Readiness_Packet.md
"""


def redacted_value(item: dict[str, Any]) -> str:
    value = item.get("redacted_value")
    if value is None:
        value = "redacted" if item.get("value") not in (None, "") else "pending"
    return str(value)


def redacted_command(item: dict[str, Any]) -> str:
    command = str(item.get("verification_command") or "not run")
    raw_value = item.get("value")
    if raw_value in (None, ""):
        return command
    raw_text = str(raw_value)
    if raw_text not in command:
        return command
    replacement = redacted_value(item)
    if replacement in {"pending", "redacted"}:
        replacement = "<redacted>"
    return command.replace(raw_text, replacement)


def is_execution_intent_input(item: dict[str, Any]) -> bool:
    key = str(item.get("key", ""))
    kind = str(item.get("kind", ""))
    return key in EXECUTION_INTENT_KEYS or kind in {"policy", "approval_source"}


def render_execution_intent_rows(readiness: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for item in readiness.get("inputs", []):
        if not isinstance(item, dict) or not is_execution_intent_input(item):
            continue
        rows.append(
            "| {key} | {value} | {status} | {source} | {notes} |".format(
                key=markdown_escape_table(str(item.get("key", "unknown"))),
                value=markdown_escape_table(redacted_value(item)),
                status=markdown_escape_table(
                    str(item.get("verification_status", "candidate"))
                ),
                source=markdown_escape_table(redacted_command(item)),
                notes=markdown_escape_table(str(item.get("notes", ""))),
            )
        )
    if not rows:
        rows.append("| pending | pending | candidate | not run | pending |")
    return rows


def render_readiness_packet(readiness: dict[str, Any]) -> str:
    rows = []
    for item in readiness.get("inputs", []):
        if not isinstance(item, dict):
            continue
        rows.append(
            "| {key} | {value} | {status} | {command} |".format(
                key=markdown_escape_table(str(item.get("key", "unknown"))),
                value=markdown_escape_table(redacted_value(item)),
                status=markdown_escape_table(
                    str(item.get("verification_status", "candidate"))
                ),
                command=markdown_escape_table(redacted_command(item)),
            )
        )
    if not rows:
        rows.append("| pending | pending | candidate | not run |")
    return "\n".join(
        [
            "# Execution Readiness Packet",
            "",
            "Status: draft",
            f"Updated: {utc_now()}",
            "",
            "## Purpose",
            "",
            "Summarize candidate execution inputs gathered during Grill. Keep exact",
            "local/private values in `.workflow_supervisor/readiness.json`; redact",
            "sensitive values here.",
            "",
            "## Candidate Inputs",
            "",
            "| Input | Redacted Value | Verification Status | Verification Command |",
            "| --- | --- | --- | --- |",
            *rows,
            "",
            "## Execution Intent Ledger",
            "",
            "Use this table when Grill records operator intent that controls",
            "whether `prepare` may acquire data, clone baselines, or skip gated",
            "sources. These rows are candidate readiness policy, not Approval",
            "Evidence and not Approved Contracts.",
            "",
            (
                "| Intent Key | Redacted Policy Or Scope | Status | Source / "
                "Verification | Notes |"
            ),
            "| --- | --- | --- | --- | --- |",
            *render_execution_intent_rows(readiness),
            "",
            "Expected keys include `hf_access_policy`,",
            "`non_hf_registration_policy`, `baseline_clone_policy`,",
            "`baseline_clone_scope`, and `external_download_policy` only when a",
            "global external-download policy is intentionally approved. Do not",
            "record Hugging Face credentials or tokens.",
            "",
            "## Dataset Access Ledger",
            "",
            "Use this table when dataset sources are discussed during Grill. Prefer",
            "non-destructive probes such as official pages, repository trees,",
            "dataset APIs, HTTP HEAD checks, or file listings. Do not download",
            "large assets, private data, or non-approved gated datasets during",
            "Grill. Active executable datasets need a direct acquisition source",
            "such as a Hugging Face dataset id, official dataset API,",
            "repository/release/archive URL, Zenodo record, or private exact",
            "local path stored in readiness JSON. Paper or project pages are",
            "contextual only unless they expose that source.",
            "",
            (
                "| Dataset ID | Source | Access Verdict | Download Probe | "
                "Execution Decision | Notes |"
            ),
            "| --- | --- | --- | --- | --- | --- |",
            "| pending | pending | pending | not run | deferred | pending |",
            "",
            "Execution Decision must be one of: `candidate`, `rejected`,",
            "`requires_approval`, or `deferred`.",
            "",
            "## Baseline Source Ledger",
            "",
            "Use this table when baseline or negative-control sources are",
            "discussed during Grill. Executable baselines need a concrete",
            "code repository URL, official code entrypoint, or private exact local",
            "path stored in readiness JSON. Method names, paper URLs, project",
            "pages without code, and reported-method baselines are contextual",
            "only; record them as deferred or as `baseline_repo_missing` until",
            "the cloneable source is found.",
            "",
            (
                "| Baseline ID | Role | Code Repository Or Entrypoint | "
                "Repo Probe | Execution Decision | Notes |"
            ),
            "| --- | --- | --- | --- | --- | --- |",
            (
                "| pending | pending | pending | not run | "
                "baseline_repo_missing | pending |"
            ),
            "",
            "Execution Decision must be one of: `candidate`, `rejected`,",
            "`requires_approval`, `deferred`, or `baseline_repo_missing`.",
            "",
            "## Verified Facts",
            "",
            "- None yet. Candidate inputs are not verified until readiness",
            "  preflight runs.",
            "",
            "## Open Questions",
            "",
            "- Which local paths must be verified before `prepare`?",
            "- Which approvals are required before unattended WF10?",
            "",
            "## Boundary Notes",
            "",
            "This packet is not a Review Packet and not Approval Evidence.",
            "Supervisor readiness preflight must verify candidate inputs",
            "before using them.",
            "",
        ]
    )


def append_round(
    root: Path,
    *,
    lens: str,
    answer_summary: str,
    risk: str,
    gap_check: str,
    next_question: str,
    exit_recommendation: str,
    human_exit_decision: str,
) -> Path:
    path = root / ROUND_LOG
    existing = read_text_if_exists(path)
    if existing is None:
        existing = render_round_log("", lens)
    round_number = 0
    for line in existing.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0].isdigit():
            round_number = max(round_number, int(cells[0]))
    if exit_recommendation not in EXIT_OPTIONS:
        known = ", ".join(EXIT_OPTIONS)
        raise ValueError(
            f"unknown exit recommendation {exit_recommendation!r}; expected {known}"
        )
    if human_exit_decision not in HUMAN_EXIT_OPTIONS:
        known = ", ".join(HUMAN_EXIT_OPTIONS)
        raise ValueError(
            f"unknown human exit decision {human_exit_decision!r}; expected {known}"
        )
    gap_text = gap_check or risk or "pending"
    question_text = next_question or first_question_for_lens(lens)
    if ROUND_TABLE_MARKER in existing:
        row = (
            f"| {round_number + 1} | {markdown_escape_table(lens)} | "
            f"{markdown_escape_table(answer_summary)} | "
            f"{markdown_escape_table(gap_text)} | "
            f"{markdown_escape_table(question_text)} | "
            f"`{markdown_escape_table(exit_recommendation)}` |"
        )
        updated = append_table_row(existing, ROUND_TABLE_MARKER, row)
    elif LEGACY_ROUND_TABLE_MARKER in existing:
        row = (
            f"| {round_number + 1} | {markdown_escape_table(lens)} | "
            f"{markdown_escape_table(answer_summary)} | "
            f"{markdown_escape_table(gap_text)} |"
        )
        updated = append_table_row(existing, LEGACY_ROUND_TABLE_MARKER, row)
    else:
        raise ValueError(f"{path} is missing Grill rounds table")
    updated = replace_markdown_section(
        updated,
        "## Current Gap Check",
        render_current_gap_check(
            gap_check=gap_text,
            next_question=question_text,
            exit_recommendation=exit_recommendation,
        ),
    )
    updated = replace_markdown_section(
        updated,
        "## Human Exit Decision",
        render_human_exit_decision(human_exit_decision),
    )
    atomic_write_text(path, updated)
    return path


def command_init(args: argparse.Namespace) -> int:
    root = repo_root(args.workspace_root)
    readiness = (
        load_json(resolve_path(root, args.readiness_json))
        if args.readiness_json
        else empty_readiness("grill")
    )
    errors = validate_readiness(root, readiness)
    if errors:
        raise ValueError("; ".join(errors))

    writes = {
        root / RESEARCH_INTENT: render_intent(args.seed or "", args.lens),
        root / ROUND_LOG: render_round_log(args.seed or "", args.lens),
        root / READINESS_PACKET: render_readiness_packet(readiness),
    }
    written: list[str] = []
    skipped: list[str] = []
    for path, text in writes.items():
        if write_if_allowed(path, text, force=args.force):
            written.append(path.relative_to(root).as_posix())
        else:
            skipped.append(path.relative_to(root).as_posix())
    if args.write_readiness:
        readiness_path = root / READINESS_JSON
        atomic_write_json(readiness_path, readiness)
        written.append(readiness_path.relative_to(root).as_posix())
    emit_result(args, written=written, skipped=skipped)
    return 0


def command_round(args: argparse.Namespace) -> int:
    root = repo_root(args.workspace_root)
    path = append_round(
        root,
        lens=args.lens,
        answer_summary=args.answer_summary,
        risk=args.risk,
        gap_check=args.gap_check or args.risk,
        next_question=args.next_question,
        exit_recommendation=args.exit_recommendation,
        human_exit_decision=args.human_exit_decision,
    )
    emit_result(args, written=[path.relative_to(root).as_posix()], skipped=[])
    return 0


def command_packet(args: argparse.Namespace) -> int:
    root = repo_root(args.workspace_root)
    readiness = load_json(resolve_path(root, args.readiness_json))
    errors = validate_readiness(root, readiness)
    if errors:
        raise ValueError("; ".join(errors))
    output = root / READINESS_PACKET
    atomic_write_text(output, render_readiness_packet(readiness))
    emit_result(args, written=[output.relative_to(root).as_posix()], skipped=[])
    return 0


def emit_result(
    args: argparse.Namespace,
    *,
    written: list[str],
    skipped: list[str],
) -> None:
    payload = {"ok": True, "written": written, "skipped": skipped}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or update draft-only Grill artifacts."
    )
    parser.add_argument("--workspace-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--seed", default="")
    init.add_argument("--lens", default="intake")
    init.add_argument("--readiness-json")
    init.add_argument("--write-readiness", action="store_true")
    init.add_argument("--force", action="store_true")
    init.add_argument("--json", action="store_true")
    init.set_defaults(func=command_init)

    round_cmd = subparsers.add_parser("round")
    round_cmd.add_argument("--lens", required=True)
    round_cmd.add_argument("--answer-summary", required=True)
    round_cmd.add_argument("--risk", default="pending")
    round_cmd.add_argument("--gap-check", default="")
    round_cmd.add_argument("--next-question", default="")
    round_cmd.add_argument(
        "--exit-recommendation",
        default="continue_grill",
        choices=sorted(EXIT_OPTIONS),
    )
    round_cmd.add_argument(
        "--human-exit-decision",
        default=HUMAN_EXIT_PENDING,
        choices=sorted(HUMAN_EXIT_OPTIONS),
    )
    round_cmd.add_argument("--json", action="store_true")
    round_cmd.set_defaults(func=command_round)

    packet = subparsers.add_parser("packet")
    packet.add_argument(
        "--readiness-json",
        default=".workflow_supervisor/readiness.json",
    )
    packet.add_argument("--json", action="store_true")
    packet.set_defaults(func=command_packet)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        else:
            print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
