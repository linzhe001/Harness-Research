#!/usr/bin/env python3
"""Create or validate Grill execution-readiness candidate inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from state import (
    atomic_write_json,
    load_json,
    repo_root,
    resolve_path,
    utc_now,
)

READINESS_DEFAULTS: dict[str, Any] = {
    "external_download_policy": "unset",
    "approved_datasets": [],
    "approved_baselines": [],
    "target_paths": {},
    "unknowns": [],
    "operator_approved_at": None,
}


def approval_args_present(args: argparse.Namespace) -> bool:
    return bool(
        args.approve_dataset
        or args.approve_baseline
        or args.target_path
        or args.unknown
        or args.external_download_policy
        or args.operator_approved_at
    )


def empty_readiness(source: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": utc_now(),
        "source": source,
        **READINESS_DEFAULTS,
        "inputs": [],
    }


def normalize_readiness(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for key, value in READINESS_DEFAULTS.items():
        if key not in normalized:
            normalized[key] = value.copy() if isinstance(value, (dict, list)) else value
    return normalized


def parse_key_value_spec(spec: str, *, required: set[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"expected key=value in {spec!r}")
        key, value = chunk.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"empty key in {spec!r}")
        result[key] = value
    missing = sorted(key for key in required if not result.get(key))
    if missing:
        raise ValueError(f"{spec!r} missing required keys: {', '.join(missing)}")
    return result


def parse_target_path(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise ValueError(f"target path must use key=value: {spec!r}")
    key, value = spec.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key or not value:
        raise ValueError(f"target path must use non-empty key=value: {spec!r}")
    return key, value


def normalize_dataset_spec(spec: str, source_ref: str) -> dict[str, Any]:
    item = parse_key_value_spec(spec, required={"source"})
    if "target_path" not in item and "target" in item:
        item["target_path"] = item["target"]
    if "max_size_gb" in item:
        if str(item["max_size_gb"]).strip():
            try:
                item["max_size_gb"] = float(item["max_size_gb"])
            except ValueError as exc:
                raise ValueError(f"max_size_gb must be numeric in {spec!r}") from exc
        else:
            item["max_size_gb"] = None
    item.setdefault("id", item["source"].rstrip("/").split("/")[-1] or "dataset")
    item.setdefault("target_path", None)
    item.setdefault("license", None)
    item.setdefault("max_size_gb", None)
    item["access_status"] = "approved"
    item["source_ref"] = source_ref
    item.setdefault("notes", "approved during Grill")
    return {
        key: item[key]
        for key in (
            "id",
            "source",
            "target_path",
            "license",
            "max_size_gb",
            "access_status",
            "source_ref",
            "notes",
        )
        if key in item
    }


def normalize_baseline_spec(spec: str, source_ref: str) -> dict[str, Any]:
    item = parse_key_value_spec(spec, required=set())
    source = item.get("source") or item.get("repo")
    if not source:
        raise ValueError(f"{spec!r} missing required source or repo")
    item["repo"] = source
    if "target_path" not in item and "target" in item:
        item["target_path"] = item["target"]
    item.setdefault("id", str(source).rstrip("/").split("/")[-1] or "baseline")
    item.setdefault("ref", None)
    item.setdefault("target_path", None)
    item.setdefault("role", item["id"])
    item["access_status"] = "approved"
    item["source_ref"] = source_ref
    item.setdefault("notes", "approved during Grill")
    return {
        key: item[key]
        for key in (
            "id",
            "repo",
            "ref",
            "target_path",
            "role",
            "access_status",
            "source_ref",
            "notes",
        )
        if key in item
    }


def upsert_readiness_item(
    items: list[Any],
    item: dict[str, Any],
    *,
    identity_keys: tuple[str, ...],
) -> list[Any]:
    kept: list[Any] = []
    replaced = False
    item_identity = tuple(item.get(key) for key in identity_keys)
    for existing in items:
        if not isinstance(existing, dict):
            kept.append(existing)
            continue
        existing_identity = tuple(existing.get(key) for key in identity_keys)
        if existing_identity == item_identity:
            kept.append(item)
            replaced = True
        else:
            kept.append(existing)
    if not replaced:
        kept.append(item)
    return kept


def apply_cli_approvals(
    data: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    readiness = normalize_readiness(data)
    source_ref = args.source_ref or "operator confirmed in Grill"
    for spec in args.approve_dataset:
        item = normalize_dataset_spec(spec, source_ref)
        readiness["approved_datasets"] = upsert_readiness_item(
            list(readiness.get("approved_datasets", [])),
            item,
            identity_keys=("id", "source"),
        )
        target = item.get("target_path") or item.get("target")
        if target:
            readiness.setdefault("target_paths", {})["dataset_root"] = str(target)
    for spec in args.approve_baseline:
        item = normalize_baseline_spec(spec, source_ref)
        readiness["approved_baselines"] = upsert_readiness_item(
            list(readiness.get("approved_baselines", [])),
            item,
            identity_keys=("id", "repo"),
        )
        target = item.get("target_path") or item.get("target")
        if target:
            readiness.setdefault("target_paths", {})["baseline_cache"] = str(target)
    for spec in args.target_path:
        key, value = parse_target_path(spec)
        readiness.setdefault("target_paths", {})[key] = value
    for value in args.unknown:
        value = value.strip()
        if value:
            readiness.setdefault("unknowns", []).append(value)
    if args.external_download_policy:
        readiness["external_download_policy"] = args.external_download_policy
    elif args.approve_dataset or args.approve_baseline:
        current = readiness.get("external_download_policy")
        if current in {None, "", "unset"}:
            readiness["external_download_policy"] = "allow_if_approved"
    if args.operator_approved_at:
        readiness["operator_approved_at"] = args.operator_approved_at
    elif args.approve_dataset or args.approve_baseline:
        readiness["operator_approved_at"] = utc_now()
    readiness["updated_at"] = utc_now()
    readiness["source"] = args.source
    if args.approve_dataset or args.approve_baseline:
        summary = (
            f"approved_datasets={len(readiness.get('approved_datasets', []))}; "
            f"approved_baselines={len(readiness.get('approved_baselines', []))}"
        )
        readiness.setdefault("inputs", []).append(
            {
                "key": "grill_approved_execution_sources",
                "kind": "approval_source",
                "value": summary,
                "redacted_value": summary,
                "verification_status": "candidate",
                "verified_at": None,
                "verification_command": source_ref,
                "notes": (
                    "Operator-approved prepare inputs recorded during Grill; "
                    "prepare preflight must still verify local paths."
                ),
            }
        )
    return readiness


def validate_readiness(root: Path, data: dict[str, Any]) -> list[str]:
    data = normalize_readiness(data)
    schema = load_json(root / "schemas" / "execution_readiness.schema.json")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    rendered: list[str] = []
    for error in errors:
        location = "readiness"
        for part in error.path:
            location += f"[{part}]" if isinstance(part, int) else f".{part}"
        rendered.append(f"{location}: {error.message}")
    return rendered


def verify_path_inputs(root: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for index, item in enumerate(data.get("inputs", [])):
        if not isinstance(item, dict) or item.get("kind") != "path":
            continue
        value = item.get("value")
        if not isinstance(value, str) or not value.strip():
            errors.append(f"readiness.inputs[{index}].value: path value required")
            continue
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            errors.append(
                f"readiness.inputs[{index}].value: path does not exist: {value}"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Initialize or validate Grill execution readiness JSON."
    )
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument(
        "--output",
        default=".workflow_supervisor/readiness.json",
        help="Supervisor-owned readiness JSON path.",
    )
    parser.add_argument("--source", default="grill")
    parser.add_argument(
        "--source-ref",
        default="",
        help="Human-readable approval source for CLI-approved entries.",
    )
    parser.add_argument("--input-json")
    parser.add_argument(
        "--external-download-policy",
        choices=[
            "unset",
            "deny",
            "allow",
            "allow_if_approved",
            "requires_approval",
        ],
    )
    parser.add_argument(
        "--approve-dataset",
        action="append",
        default=[],
        help=(
            "Approve a dataset source from Grill, as "
            "id=<id>,source=<url-or-path>,target=<path>[,license=...]."
        ),
    )
    parser.add_argument(
        "--approve-baseline",
        action="append",
        default=[],
        help=(
            "Approve a baseline source from Grill, as "
            "id=<id>,repo=<url-or-path>,target=<path>[,ref=...]."
        ),
    )
    parser.add_argument(
        "--target-path",
        action="append",
        default=[],
        help="Record a target path as key=value, e.g. dataset_root=data/main.",
    )
    parser.add_argument(
        "--unknown",
        action="append",
        default=[],
        help="Record an unresolved readiness unknown.",
    )
    parser.add_argument("--operator-approved-at")
    parser.add_argument(
        "--verify-paths",
        action="store_true",
        help="Check that path-kind input values exist.",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--write-readiness",
        action="store_true",
        help="Write supervisor-owned readiness JSON after validation.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root(args.workspace_root)
    output = resolve_path(root, args.output)
    try:
        if args.input_json:
            data = load_json(Path(args.input_json))
        elif approval_args_present(args) and output.exists():
            data = load_json(output)
        else:
            data = empty_readiness(args.source)
        data = normalize_readiness(data)
        if approval_args_present(args):
            data = apply_cli_approvals(data, args)
        errors = validate_readiness(root, data)
        if not errors and args.verify_paths:
            errors.extend(verify_path_inputs(root, data))
        if errors:
            raise ValueError("; ".join(errors))
        should_write = args.write_readiness and not args.check and not args.dry_run
        if should_write:
            atomic_write_json(output, data)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        else:
            print(str(exc), file=sys.stderr)
        return 2

    payload = {
        "ok": True,
        "output": str(output),
        "written": should_write,
        "verified_path_count": (
            sum(1 for item in data.get("inputs", []) if item.get("kind") == "path")
            if args.verify_paths
            else 0
        ),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
