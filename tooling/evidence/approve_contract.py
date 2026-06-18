#!/usr/bin/env python3
"""Record explicit human approval for a Harness dynamic-context contract."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

CONTRACT_PATHS = {
    "project_contract": "docs/10_contract/Project_Contract.md",
    "evaluation_contract": "docs/10_contract/Evaluation_Contract.md",
    "baseline_contract": "docs/10_contract/Baseline_Contract.md",
    "claim_boundary": "docs/10_contract/Claim_Boundary.md",
}
CONTRACT_LABELS = {
    "project_contract": "Project Contract",
    "evaluation_contract": "Evaluation Contract",
    "baseline_contract": "Baseline Contract",
    "claim_boundary": "Claim Boundary",
}
APPROVAL_HEADERS = {
    "Status": "approved",
    "Human approved": "yes",
}


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def utc_now() -> str:
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


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError("PROJECT_STATE.json is required before approving a contract")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("PROJECT_STATE.json must contain a JSON object")
    return data


def header_line(label: str, value: str) -> str:
    return f"{label}: {value}"


def upsert_markdown_headers(text: str, headers: dict[str, str]) -> str:
    lines = text.splitlines()
    if not lines:
        lines = ["# Contract"]

    top_end = len(lines)
    for index, line in enumerate(lines[1:], start=1):
        if line.startswith("## "):
            top_end = index
            break

    replaced: set[str] = set()
    for index in range(top_end):
        for label, value in headers.items():
            if lines[index].lower().startswith(f"{label.lower()}:"):
                lines[index] = header_line(label, value)
                replaced.add(label)
                break

    missing = [(label, value) for label, value in headers.items() if label not in replaced]
    if missing:
        insert_at = 1 if lines and lines[0].startswith("#") else 0
        for index in range(top_end - 1, -1, -1):
            if ":" in lines[index] and not lines[index].startswith("#"):
                insert_at = index + 1
                break
        lines[insert_at:insert_at] = [header_line(label, value) for label, value in missing]

    return "\n".join(lines) + "\n"


def contract_path_for(state: dict[str, Any], contract: str) -> str:
    contracts = state.get("contracts")
    if isinstance(contracts, dict):
        entry = contracts.get(contract)
        if isinstance(entry, dict) and isinstance(entry.get("path"), str) and entry["path"]:
            return entry["path"]
    if state.get("context_model_version") == "dynamic-context-v2":
        return "docs/context/contracts.md"
    return CONTRACT_PATHS[contract]


def approval_headers_for_contract(
    contract: str,
    contract_path: str,
    *,
    approval_time: str,
    approved_by: str,
    approval_source: str,
    approval_note: str | None,
) -> dict[str, str]:
    if contract_path == "docs/context/contracts.md":
        label = CONTRACT_LABELS[contract]
        headers = {
            f"{label} status": "approved",
            f"{label} human approved": "yes",
            f"{label} approved at": approval_time,
            f"{label} approved by": approved_by,
            f"{label} approval source": approval_source,
        }
        if approval_note:
            headers[f"{label} approval note"] = approval_note
        return headers
    headers = {
        **APPROVAL_HEADERS,
        "Approved at": approval_time,
        "Approved by": approved_by,
        "Approval source": approval_source,
    }
    if approval_note:
        headers["Approval note"] = approval_note
    return headers


def approve_contract(
    workspace_root: Path,
    contract: str,
    *,
    approved_by: str,
    approval_source: str,
    approved_at: str | None = None,
    approval_note: str | None = None,
) -> dict[str, Any]:
    if contract not in CONTRACT_PATHS:
        raise ValueError(f"contract must be one of {sorted(CONTRACT_PATHS)}")
    if not approved_by.strip():
        raise ValueError("approved_by is required")
    if not approval_source.strip():
        raise ValueError("approval_source is required")

    workspace = workspace_root.resolve()
    state_path = workspace / "PROJECT_STATE.json"
    state = load_state(state_path)
    relative_contract_path = contract_path_for(state, contract)
    contract_path = workspace / relative_contract_path
    if not contract_path.exists():
        raise FileNotFoundError(f"contract document not found: {relative_contract_path}")

    approval_time = approved_at or utc_now()
    headers = approval_headers_for_contract(
        contract,
        relative_contract_path,
        approval_time=approval_time,
        approved_by=approved_by,
        approval_source=approval_source,
        approval_note=approval_note,
    )
    updated_markdown = upsert_markdown_headers(
        contract_path.read_text(encoding="utf-8", errors="replace"),
        headers,
    )
    atomic_write_text(contract_path, updated_markdown)

    contracts = state.setdefault("contracts", {})
    if not isinstance(contracts, dict):
        raise ValueError("PROJECT_STATE.json contracts must be an object when present")
    entry = contracts.setdefault(contract, {})
    if not isinstance(entry, dict):
        raise ValueError(f"PROJECT_STATE.json contracts.{contract} must be an object")
    entry.update(
        {
            "path": relative_contract_path,
            "status": "approved",
            "approved_at": approval_time,
            "approved_by": approved_by,
            "approval_source": approval_source,
        }
    )
    if approval_note:
        entry["approval_note"] = approval_note
    state["contracts"] = contracts
    atomic_write_json(state_path, state)

    return {
        "ok": True,
        "contract": contract,
        "contract_path": relative_contract_path,
        "project_state_path": relpath(state_path, workspace),
        "approved_at": approval_time,
        "approved_by": approved_by,
        "approval_source": approval_source,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record explicit human approval for a Harness contract.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--contract", choices=sorted(CONTRACT_PATHS), required=True)
    parser.add_argument("--approved-by", required=True, help="Human reviewer or operator identity.")
    parser.add_argument("--approval-source", required=True, help="Review packet path, issue/PR, or current conversation reference.")
    parser.add_argument("--approved-at", help="Approval timestamp; defaults to current UTC time.")
    parser.add_argument("--approval-note", help="Optional short approval note.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        summary = approve_contract(
            args.workspace_root,
            args.contract,
            approved_by=args.approved_by,
            approval_source=args.approval_source,
            approved_at=args.approved_at,
            approval_note=args.approval_note,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"approved {summary['contract']} at {summary['contract_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
