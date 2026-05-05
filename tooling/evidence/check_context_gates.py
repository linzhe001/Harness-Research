#!/usr/bin/env python3
"""Check dynamic-context gates before iteration, final experiments, or release."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dynamic_context import is_dynamic_context_workspace  # noqa: E402

VALID_STATUSES = {"missing", "draft", "approved", "superseded"}
TRUE_VALUES = {"yes", "true", "approved", "y", "1"}
CANONICAL_STAGES = {"status", "wf5-eval-contract", "wf10-auto", "wf11", "wf12"}
STAGE_ALIASES = {
    "wf5": "wf5-eval-contract",
}


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def read_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:16]:
        if line.lower().startswith("status:"):
            status = line.split(":", 1)[1].strip().lower()
            return status if status in VALID_STATUSES else "draft"
    return "draft"


def read_header(path: Path, label: str) -> str | None:
    if not path.exists():
        return None
    prefix = f"{label.lower()}:"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:24]:
        if line.lower().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def read_bool_header(path: Path, label: str) -> bool | None:
    value = read_header(path, label)
    if value is None:
        return None
    return value.strip().lower() in TRUE_VALUES


def state_contract_status(state: dict[str, Any], key: str) -> str | None:
    contracts = state.get("contracts")
    if not isinstance(contracts, dict):
        return None
    entry = contracts.get(key)
    if not isinstance(entry, dict):
        return None
    status = entry.get("status")
    return status if isinstance(status, str) else None


def state_contract_entry(state: dict[str, Any], key: str) -> dict[str, Any]:
    contracts = state.get("contracts")
    if not isinstance(contracts, dict):
        return {}
    entry = contracts.get(key)
    return entry if isinstance(entry, dict) else {}


def state_has_approval_metadata(state: dict[str, Any], key: str) -> bool:
    entry = state_contract_entry(state, key)
    return all(bool(entry.get(field)) for field in ("approved_at", "approved_by", "approval_source"))


def state_accepts_draft(state: dict[str, Any], key: str) -> bool:
    entry = state_contract_entry(state, key)
    return bool(
        entry.get("operator_accepted_draft")
        or entry.get("draft_accepted_for_auto_iterate")
        or entry.get("accepted_for_current_run")
    )


def contract_info(workspace_root: Path, state: dict[str, Any], key: str, relative: str) -> dict[str, Any]:
    path = workspace_root / relative
    markdown_status = read_status(path)
    human_approved = read_bool_header(path, "Human approved")
    state_status = state_contract_status(state, key)
    status = state_status or markdown_status
    if status not in VALID_STATUSES:
        status = "draft"
    approval_metadata = state_has_approval_metadata(state, key)
    status_consistent = state_status is None or state_status == markdown_status
    return {
        "key": key,
        "path": relative,
        "exists": path.exists(),
        "status": status,
        "markdown_status": markdown_status,
        "state_status": state_status,
        "human_approved": human_approved,
        "state_approval_metadata": approval_metadata,
        "status_consistent": status_consistent,
        "approval_confirmed": status == "approved" and markdown_status == "approved" and human_approved is True and approval_metadata and status_consistent,
        "operator_accepted_draft": state_accepts_draft(state, key),
    }


def detect_dynamic_mode(workspace_root: Path, state: dict[str, Any]) -> bool:
    return is_dynamic_context_workspace(workspace_root, state)


def normalize_stage(stage: str) -> str:
    normalized = stage.lower()
    normalized = STAGE_ALIASES.get(normalized, normalized)
    if normalized not in CANONICAL_STAGES:
        raise ValueError(f"unknown stage: {stage}")
    return normalized


def add_check(checks: list[dict[str, Any]], name: str, ok: bool, severity: str, detail: str) -> None:
    checks.append({"name": name, "ok": ok, "severity": severity, "detail": detail})


def gate_result(workspace_root: Path, *, stage: str, allow_draft: bool = False) -> dict[str, Any]:
    stage = normalize_stage(stage)
    state_path = workspace_root / "PROJECT_STATE.json"
    state = load_json_if_exists(state_path)
    dynamic = detect_dynamic_mode(workspace_root, state)
    checks: list[dict[str, Any]] = []

    contracts = {
        "project_contract": contract_info(workspace_root, state, "project_contract", "docs/10_contract/Project_Contract.md"),
        "evaluation_contract": contract_info(workspace_root, state, "evaluation_contract", "docs/10_contract/Evaluation_Contract.md"),
        "baseline_contract": contract_info(workspace_root, state, "baseline_contract", "docs/10_contract/Baseline_Contract.md"),
        "claim_boundary": contract_info(workspace_root, state, "claim_boundary", "docs/10_contract/Claim_Boundary.md"),
    }

    if not dynamic:
        legacy_eval = bool(state.get("evaluation_protocol"))
        if stage == "wf10-auto" and not legacy_eval:
            add_check(checks, "legacy_evaluation_protocol", False, "error", "Legacy mode requires PROJECT_STATE.json.evaluation_protocol before WF10 auto-iterate.")
        else:
            add_check(checks, "legacy_mode", True, "info", "Dynamic context is not enabled; using legacy workflow gates.")
        return finalize(stage, dynamic, contracts, checks)

    eval_contract = contracts["evaluation_contract"]
    for key, info in contracts.items():
        if info["exists"] and not info["status_consistent"]:
            add_check(
                checks,
                f"{key}_status_consistency",
                False,
                "error",
                f"{info['path']} status {info['markdown_status']!r} does not match PROJECT_STATE.json contracts.{key}.status {info['state_status']!r}.",
            )

    if stage in {"wf5-eval-contract", "wf10-auto", "wf11", "wf12"}:
        approved = eval_contract["status"] == "approved"
        draft_ok = allow_draft or eval_contract["operator_accepted_draft"]
        if not eval_contract["exists"]:
            add_check(checks, "evaluation_contract_exists", False, "error", "Missing docs/10_contract/Evaluation_Contract.md.")
        elif approved and eval_contract["approval_confirmed"]:
            add_check(checks, "evaluation_contract_approved", True, "info", "Evaluation Contract is approved.")
        elif approved:
            add_check(
                checks,
                "evaluation_contract_approval_unconfirmed",
                False,
                "error",
                "Evaluation Contract has Status: approved but needs both Human approved: yes in Markdown and PROJECT_STATE approval metadata (approved_at, approved_by, approval_source).",
            )
        elif draft_ok:
            add_check(checks, "evaluation_contract_draft_accepted", True, "warn", "Evaluation Contract is draft but explicitly accepted for this run.")
        else:
            add_check(checks, "evaluation_contract_not_approved", False, "error", f"Evaluation Contract status is {eval_contract['status']!r}.")

    if stage == "wf5-eval-contract":
        baseline_contract = contracts["baseline_contract"]
        if not baseline_contract["exists"]:
            add_check(
                checks,
                "baseline_contract_exists",
                False,
                "error",
                "Missing docs/10_contract/Baseline_Contract.md; WF5 should draft or approve baseline requirements before later stages depend on reproduced baselines.",
            )
        elif baseline_contract["status"] == "approved" and baseline_contract["approval_confirmed"]:
            add_check(checks, "baseline_contract_approved", True, "info", "Baseline Contract is approved.")
        elif baseline_contract["status"] == "approved":
            add_check(
                checks,
                "baseline_contract_approval_unconfirmed",
                False,
                "error",
                "Baseline Contract has Status: approved but needs both Human approved: yes in Markdown and PROJECT_STATE approval metadata (approved_at, approved_by, approval_source).",
            )
        else:
            add_check(
                checks,
                "baseline_contract_draft",
                True,
                "warn",
                f"Baseline Contract exists but status is {baseline_contract['status']!r}; human approval is needed before relying on baseline exclusions or required baseline choices.",
            )

    if stage in {"wf11", "wf12"}:
        for key, label in [("project_contract", "Project Contract"), ("claim_boundary", "Claim Boundary")]:
            info = contracts[key]
            if not info["exists"]:
                add_check(checks, f"{key}_exists", False, "error", f"Missing {label}: {info['path']}.")
            elif info["status"] == "approved" and info["approval_confirmed"]:
                add_check(checks, f"{key}_approved", True, "info", f"{label} is approved.")
            elif info["status"] == "approved":
                add_check(
                    checks,
                    f"{key}_approval_unconfirmed",
                    False,
                    "error",
                    f"{label} has Status: approved but needs both Human approved: yes in Markdown and PROJECT_STATE approval metadata (approved_at, approved_by, approval_source).",
                )
            else:
                add_check(checks, f"{key}_not_approved", False, "error", f"{label} exists but status is {info['status']!r}.")

    if stage == "wf12":
        claim = contracts["claim_boundary"]
        if claim["exists"] and claim["status"] != "approved":
            add_check(checks, "release_claim_boundary", False, "error", "Release claims require an approved Claim Boundary.")

    if stage == "status":
        for key, info in contracts.items():
            add_check(checks, f"{key}_status", info["exists"], "info" if info["exists"] else "warn", f"{info['path']}: {info['status']}")

    return finalize(stage, dynamic, contracts, checks)


def finalize(stage: str, dynamic: bool, contracts: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [check for check in checks if check["severity"] == "error" and not check["ok"]]
    warnings = [check for check in checks if check["severity"] == "warn"]
    return {
        "ok": not errors,
        "stage": stage,
        "dynamic_context": dynamic,
        "contracts": contracts,
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def print_text(result: dict[str, Any]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print(f"{status} context gates for {result['stage']} (dynamic={result['dynamic_context']})")
    for check in result["checks"]:
        marker = "OK" if check["ok"] else "NO"
        print(f"- [{marker}] {check['severity']}: {check['name']} - {check['detail']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Harness dynamic-context gates.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=sorted(CANONICAL_STAGES), default="status")
    parser.add_argument("--allow-draft", action="store_true", help="Accept draft Evaluation Contract for the current run.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = gate_result(args.workspace_root.resolve(), stage=args.stage, allow_draft=args.allow_draft)
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
