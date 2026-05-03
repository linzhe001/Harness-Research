#!/usr/bin/env python3
"""Run the dynamic-context gate suite from one stable entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_review_packet  # noqa: E402
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


def gate_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "error_count": int(result.get("error_count", 0)),
        "warning_count": int(result.get("warning_count", 0)),
    }


def check_dynamic_context(
    workspace_root: Path,
    *,
    stage: str = "status",
    allow_draft: bool = False,
    allow_review_required: bool = False,
    allow_unreviewed_negative: bool = False,
    allow_missing_draft_docchain: bool = False,
    allow_draft_audit: bool = False,
    write_review_packet: bool = False,
    build_id_override: str | None = None,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    if stage not in STAGE_TO_CONTEXT_STAGE:
        raise ValueError(f"unsupported dynamic context stage: {stage}")

    context = check_context_gates.gate_result(
        workspace,
        stage=STAGE_TO_CONTEXT_STAGE[stage],
        allow_draft=allow_draft,
    )
    drift = check_protocol_drift.gate_result(
        workspace,
        stage=STAGE_TO_PROTOCOL_STAGE[stage],
        allow_review_required=allow_review_required,
        allow_unreviewed_negative=allow_unreviewed_negative,
    )
    docchain = check_docchain_gates.gate_result(
        workspace,
        allow_missing_draft=allow_missing_draft_docchain,
        allow_draft_audit=allow_draft_audit,
    )
    workflow_state = check_workflow_state.gate_result(workspace)

    gates = {
        "context": context,
        "protocol_drift": drift,
        "docchain": docchain,
        "workflow_state": workflow_state,
    }
    ok = all(result["ok"] for result in gates.values())
    review_packet_summary: dict[str, Any] | None = None
    if write_review_packet:
        review_packet_summary = build_review_packet.build_review_packet(
            workspace,
            stage=stage,
            build_id_override=build_id_override,
            context_result=context,
            drift_result=drift,
            docchain_result=docchain,
            workflow_state_result=workflow_state,
        )

    return {
        "ok": ok,
        "stage": stage,
        "gates": gates,
        "summary": {name: gate_summary(result) for name, result in gates.items()},
        "error_count": sum(int(result.get("error_count", 0)) for result in gates.values()),
        "warning_count": sum(int(result.get("warning_count", 0)) for result in gates.values()),
        "review_packet": review_packet_summary,
    }


def print_text(result: dict[str, Any]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print(f"{status} dynamic context gates for {result['stage']}")
    for name, summary in result["summary"].items():
        gate_status = "PASS" if summary["ok"] else "FAIL"
        print(f"- {name}: {gate_status} errors={summary['error_count']} warnings={summary['warning_count']}")
    packet = result.get("review_packet")
    if packet:
        print(f"- review_packet: {packet['markdown_path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Harness dynamic context gates from one command.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=sorted(CANONICAL_STAGES), default="status")
    parser.add_argument("--allow-draft", action="store_true", help="Accept draft Evaluation Contract for the current run.")
    parser.add_argument("--allow-review-required", action="store_true", help="Warn instead of fail when protocol review is still required.")
    parser.add_argument("--allow-unreviewed-negative", action="store_true", help="Warn instead of fail when negative results lack protocol review.")
    parser.add_argument("--allow-missing-draft-docchain", action="store_true", help="Warn instead of fail when draft docs still have Evidence chain: N/A.")
    parser.add_argument("--allow-draft-audit", action="store_true", help="Allow DRAFT_ONLY doc audits for draft docs.")
    parser.add_argument("--review-packet", action="store_true", help="Write a human review packet using the same gate results.")
    parser.add_argument("--build-id", dest="build_id_override")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = check_dynamic_context(
            args.workspace_root,
            stage=args.stage,
            allow_draft=args.allow_draft,
            allow_review_required=args.allow_review_required,
            allow_unreviewed_negative=args.allow_unreviewed_negative,
            allow_missing_draft_docchain=args.allow_missing_draft_docchain,
            allow_draft_audit=args.allow_draft_audit,
            write_review_packet=args.review_packet,
            build_id_override=args.build_id_override,
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
