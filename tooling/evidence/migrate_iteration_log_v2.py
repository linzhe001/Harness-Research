#!/usr/bin/env python3
"""Migrate legacy iteration_log.json files to strict Harness iteration v2."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

LEGACY_STATUS_TO_V2 = {
    "planned": "planned",
    "coding": "coding",
    "training": "ready_to_run",
    "running": "running",
    "completed": "completed",
    "abandoned": "abandoned",
    "debug": "needs_debug",
}
VALID_V2_STATUSES = {
    "planned",
    "coding",
    "ready_to_run",
    "running",
    "ready_to_eval",
    "needs_debug",
    "needs_more_evidence",
    "candidate_for_promotion",
    "promoting",
    "completed",
    "abandoned",
}
VALID_ACTIONS = {
    "plan",
    "code",
    "run_screening",
    "run_full",
    "eval",
    "debug",
    "compare",
    "ablate",
    "register",
    "promote",
    "discard",
    "stop",
}
PROMOTION_STATUSES = {
    "not_applicable",
    "not_ready",
    "candidate",
    "promoting",
    "promoted",
    "rejected",
}


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def today() -> str:
    return dt.date.today().isoformat()


def nonempty(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def infer_next_action(iteration: dict[str, Any], status: str) -> str:
    action_state = iteration.get("action_state")
    if isinstance(action_state, dict):
        action = action_state.get("next_action")
        if action in VALID_ACTIONS:
            return str(action)
    if status == "planned":
        return "code"
    if status == "coding":
        return "code"
    if status == "ready_to_run":
        screening = iteration.get("screening")
        if isinstance(screening, dict) and screening.get("recommended") is False:
            return "run_full"
        return "run_screening"
    if status == "running":
        return "run_full"
    if status == "ready_to_eval":
        return "eval"
    if status == "needs_debug":
        return "debug"
    if status == "needs_more_evidence":
        return "compare"
    if status == "candidate_for_promotion":
        return "promote"
    if status == "promoting":
        return "promote"
    return "stop"


def infer_scope(iteration: dict[str, Any]) -> str:
    implementation = iteration.get("implementation")
    if isinstance(implementation, dict):
        scope = implementation.get("scope")
        if scope in {
            "config_only",
            "run_local_code",
            "stable_candidate",
            "delegated_build",
        }:
            return str(scope)
    config_diff = iteration.get("config_diff")
    if isinstance(config_diff, dict):
        if nonempty(config_diff.get("delegated_build_run_id")):
            return "delegated_build"
        if nonempty(config_diff.get("run_local_config")):
            return "config_only"
    touched = iteration.get("touched_paths")
    if isinstance(touched, list) and touched:
        return "stable_candidate"
    return "config_only"


def default_code_manifest_path(iteration_id: str) -> str:
    return f"runs/wf10/{iteration_id}/code_manifest.json"


def promotion_status_for(iteration: dict[str, Any], scope: str) -> str:
    implementation = iteration.get("implementation")
    if isinstance(implementation, dict):
        promotion = implementation.get("promotion")
        if (
            isinstance(promotion, dict)
            and promotion.get("status") in PROMOTION_STATUSES
        ):
            return str(promotion["status"])
    if scope in {"run_local_code", "stable_candidate"}:
        return "not_ready"
    return "not_applicable"


def normalize_iteration(iteration: dict[str, Any]) -> dict[str, Any]:
    result = dict(iteration)
    iteration_id = nonempty(result.get("id"))
    if iteration_id is None:
        raise ValueError("iteration missing id")
    legacy_status = nonempty(result.get("status")) or "planned"
    result["status"] = LEGACY_STATUS_TO_V2.get(legacy_status, legacy_status)
    if result["status"] not in VALID_V2_STATUSES:
        raise ValueError(f"{iteration_id} has unsupported status {result['status']!r}")
    result.setdefault("date", today())
    result.setdefault("hypothesis", "Legacy migration placeholder hypothesis.")
    result.setdefault("changes_summary", "Generated from legacy iteration record.")
    result.setdefault("config_diff", {})
    if not isinstance(result["config_diff"], dict):
        result["config_diff"] = {"legacy_value": result["config_diff"]}
    scope = infer_scope(result)
    code_manifest_path = default_code_manifest_path(iteration_id)
    implementation = result.get("implementation")
    if not isinstance(implementation, dict):
        implementation = {}
    promotion = implementation.get("promotion")
    if not isinstance(promotion, dict):
        promotion = {}
    result["implementation"] = {
        "scope": scope,
        "code_manifest_path": implementation.get(
            "code_manifest_path",
            code_manifest_path,
        ),
        "touched_paths": implementation.get("touched_paths", []),
        "stable_api_changed": bool(implementation.get("stable_api_changed", False)),
        "delegated_build_run_id": implementation.get("delegated_build_run_id"),
        "promotion": {
            "status": promotion_status_for(result, scope),
            "plan_path": promotion.get("plan_path"),
            "promoted_commit": promotion.get("promoted_commit"),
            "risk": promotion.get("risk"),
        },
    }
    action_state = result.get("action_state")
    if not isinstance(action_state, dict):
        action_state = {}
    result["action_state"] = {
        "next_action": infer_next_action(result, result["status"]),
        "last_action": action_state.get("last_action"),
        "reason": action_state.get("reason")
        or "Generated by migrate_iteration_log_v2.py.",
        "blocked_by": action_state.get("blocked_by", []),
    }
    result.setdefault("metrics", {})
    result.setdefault("lessons", [])
    result.setdefault("light_evidence_refs", [])
    return result


def code_manifest_for(iteration: dict[str, Any]) -> dict[str, Any]:
    implementation = iteration["implementation"]
    return {
        "schema_version": "1",
        "iteration_id": iteration["id"],
        "scope": implementation["scope"],
        "purpose": iteration.get("hypothesis") or iteration.get("changes_summary"),
        "touched_paths": implementation.get("touched_paths", []),
        "entry_commands": _entry_commands(iteration),
        "validation_commands": [],
        "stable_api_changed": bool(implementation.get("stable_api_changed", False)),
        "delegated_build_run_id": implementation.get("delegated_build_run_id"),
        "promotion_criteria": (
            "Generated from legacy iteration; review before promotion."
        ),
        "rollback_plan": (
            "Legacy migration placeholder; inspect touched paths before rollback."
        ),
        "git_commit": iteration.get("git_commit"),
        "limitations": ["generated_from_legacy"],
    }


def _entry_commands(iteration: dict[str, Any]) -> list[str]:
    config_diff = iteration.get("config_diff")
    commands: list[str] = []
    if isinstance(config_diff, dict):
        command = nonempty(config_diff.get("planned_command"))
        if command:
            commands.append(command)
    run_manifest = iteration.get("run_manifest")
    if isinstance(run_manifest, dict):
        command = nonempty(run_manifest.get("command"))
        if command and command not in commands:
            commands.append(command)
    return commands


def migrate_log(root: Path, *, write_manifests: bool = True) -> dict[str, Any]:
    path = root / "iteration_log.json"
    log = load_json_object(path)
    iterations = log.get("iterations")
    if not isinstance(iterations, list):
        raise ValueError("iteration_log.json iterations must be a list")
    migrated = dict(log)
    migrated["schema_version"] = "2"
    migrated.setdefault("project", "unknown")
    migrated.setdefault("baseline_metrics", {})
    migrated.setdefault("best_iteration", None)
    migrated["iterations"] = [
        normalize_iteration(item) for item in iterations if isinstance(item, dict)
    ]
    if write_manifests:
        for iteration in migrated["iterations"]:
            manifest_path = iteration["implementation"].get("code_manifest_path")
            if not isinstance(manifest_path, str) or not manifest_path.strip():
                continue
            target = root / manifest_path
            if not target.exists():
                atomic_write_json(target, code_manifest_for(iteration))
    return migrated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        migrated = migrate_log(args.workspace_root, write_manifests=not args.dry_run)
        if not args.dry_run:
            atomic_write_json(args.workspace_root / "iteration_log.json", migrated)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    if args.json:
        print(json.dumps(migrated, indent=2, ensure_ascii=False))
    else:
        print(
            "DRY_RUN" if args.dry_run else "MIGRATED",
            f"iterations={len(migrated.get('iterations', []))}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
