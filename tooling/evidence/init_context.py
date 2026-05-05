#!/usr/bin/env python3
"""Initialize the dynamic context layout in a research workspace.

The tool copies framework-owned templates into project-owned docs without
overwriting existing files by default. It can optionally mark
``PROJECT_STATE.json`` with ``context_model_version=dynamic-protocol-v1``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


CONTEXT_MODEL_VERSION = "dynamic-protocol-v1"

REQUIRED_DIRS = [
    "docs",
    "docs/10_contract",
    "docs/20_facts",
    "docs/30_evidence",
    "docs/35_protocol",
    "docs/40_iterations",
    "docs/40_iterations/auto",
    "docs/50_memory",
    ".evidence",
    ".evidence/chains",
    ".evidence/schemas",
]


def repo_root_from_tool() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp.replace(path)


def iter_files(root: Path) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(f"template source not found: {root}")
    return sorted(path for path in root.rglob("*") if path.is_file())


def copy_tree_no_overwrite(
    source_root: Path,
    destination_root: Path,
    *,
    overwrite: bool,
    dry_run: bool,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for source in iter_files(source_root):
        relative = source.relative_to(source_root)
        destination = destination_root / relative
        if destination.exists() and not overwrite:
            actions.append({"action": "skip_exists", "path": str(destination)})
            continue
        actions.append({"action": "copy", "path": str(destination), "source": str(source)})
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    return actions


def ensure_dirs(workspace_root: Path, *, dry_run: bool) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for relative in REQUIRED_DIRS:
        path = workspace_root / relative
        if path.exists():
            actions.append({"action": "dir_exists", "path": str(path)})
            continue
        actions.append({"action": "mkdir", "path": str(path)})
        if not dry_run:
            path.mkdir(parents=True, exist_ok=True)
    return actions


def contract_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[:12]:
            if line.lower().startswith("status:"):
                status = line.split(":", 1)[1].strip().lower()
                if status in {"missing", "draft", "approved", "superseded"}:
                    return status
    except UnicodeDecodeError:
        return "draft"
    return "draft"


def update_project_state(workspace_root: Path, *, dry_run: bool) -> list[dict[str, str]]:
    state_path = workspace_root / "PROJECT_STATE.json"
    if not state_path.exists():
        return [{"action": "skip_missing_state", "path": str(state_path)}]

    state = load_json(state_path)
    state.setdefault("workflow_mode", "dynamic_context")
    state.setdefault("context_model_version", CONTEXT_MODEL_VERSION)
    contracts = state.setdefault("contracts", {})

    contract_files = {
        "project_contract": "docs/10_contract/Project_Contract.md",
        "evaluation_contract": "docs/10_contract/Evaluation_Contract.md",
        "baseline_contract": "docs/10_contract/Baseline_Contract.md",
        "claim_boundary": "docs/10_contract/Claim_Boundary.md",
    }
    for key, relative in contract_files.items():
        path = workspace_root / relative
        entry = contracts.setdefault(key, {})
        entry.setdefault("path", relative)
        entry["status"] = contract_status(path)

    if not dry_run:
        atomic_write_json(state_path, state)
    return [{"action": "update_project_state", "path": str(state_path)}]


def initialize_context(
    workspace_root: Path,
    *,
    framework_root: Path | None = None,
    overwrite: bool = False,
    set_state: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    framework = framework_root or repo_root_from_tool()
    workspace = workspace_root.resolve()
    actions: list[dict[str, str]] = []

    actions.extend(ensure_dirs(workspace, dry_run=dry_run))
    actions.extend(
        copy_tree_no_overwrite(
            framework / "templates" / "docs",
            workspace / "docs",
            overwrite=overwrite,
            dry_run=dry_run,
        )
    )
    actions.extend(
        copy_tree_no_overwrite(
            framework / "schemas",
            workspace / ".evidence" / "schemas",
            overwrite=overwrite,
            dry_run=dry_run,
        )
    )
    if set_state:
        actions.extend(update_project_state(workspace, dry_run=dry_run))

    return {
        "ok": True,
        "workspace_root": str(workspace),
        "context_model_version": CONTEXT_MODEL_VERSION if set_state else None,
        "actions": actions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize Harness dynamic context docs in a workspace.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--framework-root", type=Path, default=repo_root_from_tool())
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing copied template/schema files.")
    parser.add_argument("--set-state", action="store_true", help="Set PROJECT_STATE.json context_model_version and contract paths when PROJECT_STATE.json exists.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print the full action summary as JSON.")
    args = parser.parse_args(argv)

    try:
        summary = initialize_context(
            args.workspace_root,
            framework_root=args.framework_root,
            overwrite=args.overwrite,
            set_state=args.set_state,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        copied = sum(1 for action in summary["actions"] if action["action"] == "copy")
        skipped = sum(1 for action in summary["actions"] if action["action"] == "skip_exists")
        made_dirs = sum(1 for action in summary["actions"] if action["action"] == "mkdir")
        print(f"Initialized dynamic context layout: dirs={made_dirs}, copied={copied}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
