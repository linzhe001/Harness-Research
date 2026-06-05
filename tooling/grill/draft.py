#!/usr/bin/env python3
"""Initialize and update draft-only Grill Markdown artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from questions import question_round, render_markdown
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


def markdown_escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def write_if_allowed(path: Path, text: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    atomic_write_text(path, text)
    return True


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
    focus = f"{lens} intake"
    summary = seed or "pending"
    return f"""# Grill Round Log

Status: draft
Updated: {utc_now()}

## Rounds

| Round | Question Focus | Operator Answer Summary | Updated Risk Or Open Question |
| --- | --- | --- | --- |
| 1 | {markdown_escape_table(focus)} | {markdown_escape_table(summary)} | pending |

## Exit Decision

Record one of:

- `more_grill`
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


def append_round(root: Path, *, lens: str, answer_summary: str, risk: str) -> Path:
    path = root / ROUND_LOG
    existing = read_text_if_exists(path)
    if existing is None:
        existing = render_round_log("", lens)
    marker = "| --- | --- | --- | --- |"
    round_number = 0
    for line in existing.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0].isdigit():
            round_number = max(round_number, int(cells[0]))
    row = (
        f"| {round_number + 1} | {markdown_escape_table(lens)} | "
        f"{markdown_escape_table(answer_summary)} | {markdown_escape_table(risk)} |"
    )
    if marker not in existing:
        raise ValueError(f"{path} is missing Grill rounds table")
    updated = existing.replace(marker, marker + "\n" + row, 1)
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
