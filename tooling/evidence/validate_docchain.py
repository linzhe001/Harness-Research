#!/usr/bin/env python3
"""Validator for evidence-compiled documentation artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


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


@lru_cache(maxsize=None)
def load_schema(schema_name: str) -> dict[str, Any]:
    return load_json(SCHEMA_DIR / schema_name)


def schema_error_location(label: str, path: Any) -> str:
    location = label
    for part in path:
        if isinstance(part, int):
            location += f"[{part}]"
        else:
            location += f".{part}"
    return location


def validate_json_schema(
    label: str,
    data: dict[str, Any],
    schema_name: str,
) -> list[str]:
    validator = Draft7Validator(load_schema(schema_name))
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    return [
        f"{schema_error_location(label, error.path)}: {error.message}"
        for error in errors
    ]


def require_keys(label: str, data: dict[str, Any], keys: list[str]) -> list[str]:
    return [f"{label}: missing {key}" for key in keys if key not in data]


def require_string(label: str, data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        return [f"{label}.{key} must be a non-empty string"]
    return []


def require_list(label: str, data: dict[str, Any], key: str) -> list[str]:
    if not isinstance(data.get(key), list):
        return [f"{label}.{key} must be a list"]
    return []


def validate_fact_items(facts: Any) -> list[str]:
    if not isinstance(facts, list):
        return ["evidence_chain.facts must be a list"]
    errors: list[str] = []
    allowed_statuses = {"FACT", "INFERENCE", "DECISION", "LESSON"}
    for index, item in enumerate(facts):
        label = f"evidence_chain.facts[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        errors.extend(
            require_keys(
                label,
                item,
                ["fact_id", "claim", "epistemic_status", "evidence_refs"],
            )
        )
        errors.extend(require_string(label, item, "fact_id"))
        errors.extend(require_string(label, item, "claim"))
        status = item.get("epistemic_status")
        if status not in allowed_statuses:
            errors.append(
                f"{label}.epistemic_status must be one of: "
                + ", ".join(sorted(allowed_statuses))
            )
        errors.extend(require_list(label, item, "evidence_refs"))
    return errors


def validate_evidence_items(evidence: Any) -> list[str]:
    if not isinstance(evidence, list):
        return ["evidence_chain.evidence must be a list"]
    errors: list[str] = []
    allowed_relations = {
        "contradicts",
        "context_only",
        "partially_supports",
        "supports",
    }
    for index, item in enumerate(evidence):
        label = f"evidence_chain.evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        errors.extend(
            require_keys(label, item, ["evidence_id", "kind", "path", "supports"])
        )
        errors.extend(require_string(label, item, "evidence_id"))
        errors.extend(require_string(label, item, "kind"))
        errors.extend(require_string(label, item, "path"))
        errors.extend(require_list(label, item, "supports"))
        relation = item.get("support_relation")
        if relation is not None and relation not in allowed_relations:
            errors.append(
                f"{label}.support_relation must be one of: "
                + ", ".join(sorted(allowed_relations))
            )
    return errors


def validate_evidence_chain(path: Path) -> list[str]:
    data = load_json(path)
    errors = validate_json_schema("evidence_chain", data, "evidence_chain.schema.json")
    errors.extend(
        require_keys(
            "evidence_chain",
            data,
            [
                "schema_version",
                "chain_id",
                "doc",
                "git",
                "facts",
                "evidence",
                "unresolved",
                "doc_links",
            ],
        )
    )
    doc = data.get("doc", {})
    git = data.get("git", {})
    links = data.get("doc_links", {})
    if not isinstance(doc, dict):
        errors.append("evidence_chain.doc must be an object")
    else:
        errors.extend(
            require_keys(
                "evidence_chain.doc",
                doc,
                ["path", "doc_id", "compiled_at", "compiled_by"],
            )
        )
    if not isinstance(git, dict):
        errors.append("evidence_chain.git must be an object")
    else:
        errors.extend(
            require_keys("evidence_chain.git", git, ["commit", "branch", "is_dirty"])
        )
        if "is_dirty" in git and not isinstance(git["is_dirty"], bool):
            errors.append("evidence_chain.git.is_dirty must be boolean")
    errors.extend(validate_fact_items(data.get("facts")))
    errors.extend(validate_evidence_items(data.get("evidence")))
    if not isinstance(links, dict):
        errors.append("evidence_chain.doc_links must be an object")
    else:
        errors.extend(
            require_keys(
                "evidence_chain.doc_links",
                links,
                ["markdown_path", "audit_path", "source_manifest_path"],
            )
        )
    return errors


def validate_source_manifest(path: Path) -> list[str]:
    data = load_json(path)
    errors = validate_json_schema(
        "source_manifest", data, "source_manifest.schema.json"
    )
    errors.extend(
        require_keys(
            "source_manifest", data, ["schema_version", "chain_id", "read_set"]
        )
    )
    read_set = data.get("read_set")
    if not isinstance(read_set, list):
        errors.append("source_manifest.read_set must be a list")
        return errors
    for index, item in enumerate(read_set):
        label = f"source_manifest.read_set[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        errors.extend(require_keys(label, item, ["path", "kind", "reason", "hash"]))
        errors.extend(require_string(label, item, "path"))
        errors.extend(require_string(label, item, "kind"))
        errors.extend(require_string(label, item, "reason"))
        if "hash" in item and item["hash"] is not None:
            errors.extend(require_string(label, item, "hash"))
    return errors


def validate_doc_audit(path: Path) -> list[str]:
    data = load_json(path)
    errors = validate_json_schema("doc_audit", data, "doc_audit.schema.json")
    errors.extend(
        require_keys(
            "doc_audit",
            data,
            [
                "schema_version",
                "doc_path",
                "evidence_chain_path",
                "audit_result",
                "checks",
            ],
        )
    )
    if data.get("audit_result") not in {"PASS", "FAIL", "DRAFT_ONLY"}:
        errors.append("doc_audit.audit_result must be PASS, FAIL, or DRAFT_ONLY")
    checks = data.get("checks")
    if not isinstance(checks, list):
        errors.append("doc_audit.checks must be a list")
        return errors
    allowed_results = {"FAIL", "PASS", "WARN"}
    for index, item in enumerate(checks):
        label = f"doc_audit.checks[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        errors.extend(require_keys(label, item, ["check", "result"]))
        errors.extend(require_string(label, item, "check"))
        if item.get("result") not in allowed_results:
            errors.append(
                f"{label}.result must be one of: " + ", ".join(sorted(allowed_results))
            )
    return errors


def validate_evidence_index(path: Path) -> list[str]:
    data = load_json(path)
    return validate_json_schema("evidence_index", data, "evidence_index.schema.json")


def validate_review_packet(path: Path) -> list[str]:
    data = load_json(path)
    return validate_json_schema("review_packet", data, "review_packet.schema.json")


def validate_approval_record_data(
    data: dict[str, Any],
    *,
    label: str = "approval_record",
) -> list[str]:
    return validate_json_schema(label, data, "approval_record.schema.json")


def validate_approval_record(path: Path) -> list[str]:
    data = load_json(path)
    return validate_approval_record_data(data)


def validate_evidence_preview_index(path: Path) -> list[str]:
    data = load_json(path)
    return validate_json_schema(
        "evidence_preview_index",
        data,
        "evidence_preview_index.schema.json",
    )


def validate_docs_site_manifest(path: Path) -> list[str]:
    data = load_json(path)
    return validate_json_schema(
        "docs_site_manifest",
        data,
        "docs_site_manifest.schema.json",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Harness evidence docchain artifacts."
    )
    parser.add_argument(
        "chain_dir",
        type=Path,
        help=(
            "Directory containing evidence_chain.json, source_manifest.json, "
            "and doc_audit.json"
        ),
    )
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
