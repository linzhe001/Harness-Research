#!/usr/bin/env python3
"""Migrate legacy numbered context docs into dynamic-context-v2 docs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any

CONTEXT_MODEL_VERSION = "dynamic-context-v2"

GROUPS = {
    "contracts": [
        "docs/10_contract/Project_Contract.md",
        "docs/10_contract/Evaluation_Contract.md",
        "docs/10_contract/Baseline_Contract.md",
        "docs/10_contract/Claim_Boundary.md",
    ],
    "facts": [
        "docs/20_facts/Project_Facts.md",
        "docs/20_facts/Codebase_Map.md",
        "docs/20_facts/Project_Glossary.md",
        "docs/20_facts/Execution_Contract.md",
    ],
    "evidence": [
        "docs/30_evidence/Evidence_Index.md",
        "docs/30_evidence/Paper_Table.md",
        "docs/30_evidence/Repo_Table.md",
        "docs/30_evidence/Dataset_Table.md",
        "docs/30_evidence/Baseline_Table.md",
        "docs/30_evidence/Validation_Table.md",
        "docs/30_evidence/Metric_Table.md",
        "docs/30_evidence/Open_Questions.md",
        "docs/30_evidence/Experiment_Evidence_Index.md",
    ],
    "protocol": [
        "docs/35_protocol/Research_Protocol.md",
        "docs/35_protocol/Protocol_Assumptions.md",
        "docs/35_protocol/Protocol_Changelog.md",
        "docs/35_protocol/Protocol_Review.md",
    ],
    "experiments": [
        "docs/40_iterations/Experiment_Queue.md",
        "docs/40_iterations/latest.md",
        "docs/45_discoveries/Discovery_Ledger.md",
        "docs/45_discoveries/Research_Wiki.md",
    ],
    "memory": [
        "docs/50_memory/Decision_Log.md",
        "docs/50_memory/Lessons.md",
        "docs/50_memory/Negative_Results.md",
        "MEMORY.md",
    ],
}

ARCHIVE_PATHS = [
    "docs/10_contract",
    "docs/20_facts",
    "docs/30_evidence",
    "docs/35_protocol",
    "docs/40_iterations",
    "docs/45_discoveries",
    "docs/50_memory",
    "MEMORY.md",
]


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def status_from_text(text: str, default: str = "current") -> str:
    for line in text.splitlines()[:32]:
        if line.lower().startswith("status:"):
            value = line.split(":", 1)[1].strip().lower()
            if value in {"missing", "draft", "approved", "superseded", "current"}:
                return value
    return default


def section_for_source(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return ""
    return f"\n## Source: `{relative}`\n\n{text}\n"


def build_context_doc(root: Path, name: str, sources: list[str]) -> str:
    existing = [relative for relative in sources if (root / relative).is_file()]
    generated_at = utc_now()
    status = "draft" if name in {"contracts", "protocol"} else "current"
    if name == "contracts":
        statuses = {
            "Project Contract status": "missing",
            "Project Contract human approved": "no",
            "Evaluation Contract status": "missing",
            "Evaluation Contract human approved": "no",
            "Baseline Contract status": "missing",
            "Baseline Contract human approved": "no",
            "Claim Boundary status": "missing",
            "Claim Boundary human approved": "no",
        }
        for relative in existing:
            text = (root / relative).read_text(encoding="utf-8", errors="replace")
            value = status_from_text(text, default="draft")
            stem = Path(relative).stem.replace("_", " ")
            statuses[f"{stem} status"] = value
            human = "yes" if "human approved: yes" in text.lower() else "no"
            statuses[f"{stem} human approved"] = human
        header = "\n".join(f"{key}: {value}" for key, value in statuses.items())
    else:
        header = ""

    lines = [
        f"# {name.replace('_', ' ').title()}",
        "",
        f"Context doc: {name}",
        f"Context model: {CONTEXT_MODEL_VERSION}",
        f"Status: {status}",
        f"Migrated at: {generated_at}",
        "Evidence chain: N/A",
        "Evidence audit: N/A",
        "Audit result: N/A",
    ]
    if header:
        lines.extend(["", header])
    lines.extend(
        [
            "",
            "## Migration Sources",
            "",
        ]
    )
    if existing:
        lines.extend(f"- `{relative}`" for relative in existing)
    else:
        lines.append("- None found.")
    body = "\n".join(lines) + "\n"
    for relative in existing:
        body += section_for_source(root, relative)
    return body


def update_project_state(root: Path, *, dry_run: bool) -> dict[str, Any] | None:
    state_path = root / "PROJECT_STATE.json"
    if not state_path.is_file():
        return None
    state = read_json(state_path)
    state["context_model_version"] = CONTEXT_MODEL_VERSION
    state.setdefault("workflow_mode", "dynamic_context")
    contracts = state.setdefault("contracts", {})
    if not isinstance(contracts, dict):
        raise ValueError("PROJECT_STATE.json contracts must be an object")
    for key in (
        "project_contract",
        "evaluation_contract",
        "baseline_contract",
        "claim_boundary",
    ):
        entry = contracts.setdefault(key, {})
        if not isinstance(entry, dict):
            raise ValueError(f"PROJECT_STATE.json contracts.{key} must be an object")
        entry["path"] = "docs/context/contracts.md"
        entry.setdefault("status", "draft")
    if not dry_run:
        atomic_write_json(state_path, state)
    return state


def archive_old_paths(root: Path, *, dry_run: bool) -> list[dict[str, str]]:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_root = root / "docs" / "90_legacy" / f"context_v1_{stamp}"
    actions: list[dict[str, str]] = []
    for relative in ARCHIVE_PATHS:
        source = root / relative
        if not source.exists():
            continue
        destination = archive_root / relative
        actions.append(
            {
                "action": "archive",
                "source": relative,
                "destination": relpath(destination, root),
            }
        )
        if dry_run:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
    return actions


def migrate_context_v2(
    workspace_root: Path,
    *,
    overwrite: bool = False,
    archive_old: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = workspace_root.resolve()
    actions: list[dict[str, str]] = []
    context_root = root / "docs" / "context"
    if not dry_run:
        context_root.mkdir(parents=True, exist_ok=True)

    for name, sources in GROUPS.items():
        destination = context_root / f"{name}.md"
        if destination.exists() and not overwrite:
            actions.append({"action": "skip_exists", "path": relpath(destination, root)})
            continue
        content = build_context_doc(root, name, sources)
        actions.append({"action": "write", "path": relpath(destination, root)})
        if not dry_run:
            atomic_write_text(destination, content)

    state = update_project_state(root, dry_run=dry_run)
    if state is not None:
        actions.append({"action": "update_project_state", "path": "PROJECT_STATE.json"})
    if archive_old:
        actions.extend(archive_old_paths(root, dry_run=dry_run))
    return {
        "ok": True,
        "context_model_version": CONTEXT_MODEL_VERSION,
        "dry_run": dry_run,
        "archive_old": archive_old,
        "actions": actions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--archive-old", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = migrate_context_v2(
            args.workspace_root,
            overwrite=args.overwrite,
            archive_old=args.archive_old,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        writes = sum(1 for item in summary["actions"] if item["action"] == "write")
        archives = sum(
            1 for item in summary["actions"] if item["action"] == "archive"
        )
        print(f"migrated context v2: writes={writes}, archives={archives}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
