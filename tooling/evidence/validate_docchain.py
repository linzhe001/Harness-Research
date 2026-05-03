#!/usr/bin/env python3
"""Lightweight validator for evidence-compiled documentation artifacts.

This intentionally avoids third-party dependencies. It checks the required
structure used by the Harness doc-compiler contract; full JSON Schema
validation can be added later without changing the file layout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def require_keys(label: str, data: dict[str, Any], keys: list[str]) -> list[str]:
    return [f"{label}: missing {key}" for key in keys if key not in data]


def validate_evidence_chain(path: Path) -> list[str]:
    data = load_json(path)
    errors = require_keys(
        "evidence_chain",
        data,
        ["schema_version", "chain_id", "doc", "git", "facts", "evidence", "unresolved", "doc_links"],
    )
    doc = data.get("doc", {})
    git = data.get("git", {})
    links = data.get("doc_links", {})
    if not isinstance(doc, dict):
        errors.append("evidence_chain.doc must be an object")
    else:
        errors.extend(require_keys("evidence_chain.doc", doc, ["path", "doc_id", "compiled_at", "compiled_by"]))
    if not isinstance(git, dict):
        errors.append("evidence_chain.git must be an object")
    else:
        errors.extend(require_keys("evidence_chain.git", git, ["commit", "branch", "is_dirty"]))
        if "is_dirty" in git and not isinstance(git["is_dirty"], bool):
            errors.append("evidence_chain.git.is_dirty must be boolean")
    if not isinstance(data.get("facts"), list):
        errors.append("evidence_chain.facts must be a list")
    if not isinstance(data.get("evidence"), list):
        errors.append("evidence_chain.evidence must be a list")
    if not isinstance(links, dict):
        errors.append("evidence_chain.doc_links must be an object")
    else:
        errors.extend(require_keys("evidence_chain.doc_links", links, ["markdown_path", "audit_path", "source_manifest_path"]))
    return errors


def validate_source_manifest(path: Path) -> list[str]:
    data = load_json(path)
    errors = require_keys("source_manifest", data, ["schema_version", "chain_id", "read_set"])
    if not isinstance(data.get("read_set"), list):
        errors.append("source_manifest.read_set must be a list")
    return errors


def validate_doc_audit(path: Path) -> list[str]:
    data = load_json(path)
    errors = require_keys("doc_audit", data, ["schema_version", "doc_path", "evidence_chain_path", "audit_result", "checks"])
    if data.get("audit_result") not in {"PASS", "FAIL", "DRAFT_ONLY"}:
        errors.append("doc_audit.audit_result must be PASS, FAIL, or DRAFT_ONLY")
    if not isinstance(data.get("checks"), list):
        errors.append("doc_audit.checks must be a list")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Harness evidence docchain artifacts.")
    parser.add_argument("chain_dir", type=Path, help="Directory containing evidence_chain.json, source_manifest.json, and doc_audit.json")
    args = parser.parse_args(argv)

    chain_dir = args.chain_dir
    errors: list[str] = []
    try:
        errors.extend(validate_evidence_chain(chain_dir / "evidence_chain.json"))
        errors.extend(validate_source_manifest(chain_dir / "source_manifest.json"))
        errors.extend(validate_doc_audit(chain_dir / "doc_audit.json"))
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"PASS {chain_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
