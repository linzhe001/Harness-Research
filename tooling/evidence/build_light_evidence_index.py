#!/usr/bin/env python3
"""Build the default lightweight Evidence index for daily workflow use."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLING_DIR = REPO_ROOT / "tooling"
if str(TOOLING_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLING_DIR))

from run_artifacts import run_artifact_errors  # noqa: E402

SCHEMA_VERSION = "light-v1"
DEFAULT_OUTPUT = Path(".evidence/light/index.json")


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def workspace_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def source_ref(root: Path, path_value: str, role: str) -> dict[str, Any]:
    path = workspace_path(root, path_value)
    return {
        "path": path_value,
        "role": role,
        "sha256": sha256_file(path),
    }


def nonempty(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def iteration_metrics(iteration: dict[str, Any]) -> dict[str, Any]:
    metrics = iteration.get("metrics")
    if isinstance(metrics, dict) and metrics:
        return metrics
    full_run = iteration.get("full_run")
    if isinstance(full_run, dict):
        nested = full_run.get("metrics")
        if isinstance(nested, dict):
            return nested
    screening = iteration.get("screening")
    if isinstance(screening, dict):
        nested = screening.get("metrics")
        if isinstance(nested, dict):
            return nested
    return {}


def primary_metric_record(
    log: dict[str, Any],
    iteration: dict[str, Any],
) -> dict[str, Any] | None:
    metric_name = primary_metric_name(log.get("evaluation_protocol"))
    metrics = iteration_metrics(iteration)
    if metric_name and metric_name in metrics:
        return {"name": metric_name, "value": metrics[metric_name]}
    if metrics:
        name = sorted(metrics)[0]
        return {"name": name, "value": metrics[name]}
    return None


def primary_metric_name(protocol: Any) -> str | None:
    if not isinstance(protocol, dict):
        return None
    metric = protocol.get("primary_metric")
    if isinstance(metric, str) and metric.strip():
        return metric.strip()
    if isinstance(metric, dict):
        name = metric.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def watchdog_status_paths(root: Path, iteration_id: str) -> list[str]:
    if not iteration_id:
        return []
    status_dir = root / ".auto_iterate" / "run_health" / "status"
    if not status_dir.is_dir():
        return []
    matches: list[tuple[str, str]] = []
    for path in sorted(status_dir.glob("*.json")):
        if path.name == "summary.json":
            continue
        try:
            data = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("iteration_id") != iteration_id:
            continue
        phase_key = nonempty(data.get("phase_key"))
        matches.append((phase_key, relpath(path, root)))
    priority = {"run_full": 0, "run_screening": 1, "eval": 2}
    matches.sort(key=lambda item: (priority.get(item[0], 99), item[1]))
    return [path for _phase, path in matches]


def run_record(
    root: Path,
    log: dict[str, Any],
    iteration: dict[str, Any],
) -> dict[str, Any]:
    iteration_id = nonempty(iteration.get("id"))
    status = nonempty(iteration.get("status"))
    errors = run_artifact_errors(root, iteration)
    manifest = iteration.get("run_manifest")
    source_refs = [source_ref(root, "iteration_log.json", "iteration_log")]
    detail_ref = None
    if isinstance(manifest, dict):
        for field, role in (
            ("resolved_config_path", "resolved_config"),
            ("stdout_log_path", "stdout_log"),
            ("git_snapshot_path", "git_snapshot"),
        ):
            value = nonempty(manifest.get(field))
            if value:
                source_refs.append(source_ref(root, value, role))
        eval_paths = manifest.get("eval_artifact_paths")
        if isinstance(eval_paths, list):
            for value in eval_paths:
                if nonempty(value):
                    source_refs.append(source_ref(root, value, "eval_artifact"))
        detail_ref = nonempty(manifest.get("exp_dir")) or None
    watchdog_paths = watchdog_status_paths(root, iteration_id)
    manifest_watchdog_path = (
        nonempty(manifest.get("watchdog_status_path"))
        if isinstance(manifest, dict)
        else ""
    )
    watchdog_status_path = manifest_watchdog_path or (
        watchdog_paths[0] if watchdog_paths else ""
    )
    if watchdog_status_path:
        source_refs.append(source_ref(root, watchdog_status_path, "watchdog_status"))
    summary = (
        iteration.get("changes_summary")
        or iteration.get("hypothesis")
        or iteration_id
    )
    if errors:
        status = "incomplete"
        summary = f"{summary} ({len(errors)} artifact issue(s))"
    return {
        "id": f"run:{iteration_id}",
        "kind": "run",
        "summary": str(summary),
        "status": status,
        "iteration_id": iteration_id,
        "git_commit": iteration.get("git_commit"),
        "pre_train_commit": (
            manifest.get("pre_train_commit") if isinstance(manifest, dict) else None
        ),
        "pre_eval_commit": (
            manifest.get("pre_eval_commit") if isinstance(manifest, dict) else None
        ),
        "pre_eval_commit_NOT_CHANGED": (
            manifest.get("pre_eval_commit_NOT_CHANGED")
            if isinstance(manifest, dict)
            else None
        ),
        "watchdog_status_path": watchdog_status_path or None,
        "watchdog_status_paths": watchdog_paths,
        "primary_metric": primary_metric_record(log, iteration),
        "source_refs": source_refs,
        "detail_ref": detail_ref,
    }


def code_record(root: Path, iteration: dict[str, Any]) -> dict[str, Any] | None:
    implementation = iteration.get("implementation")
    if not isinstance(implementation, dict):
        return None
    manifest_path = nonempty(implementation.get("code_manifest_path"))
    if not manifest_path:
        return None
    iteration_id = nonempty(iteration.get("id"))
    scope = nonempty(implementation.get("scope"))
    touched = implementation.get("touched_paths")
    touched_count = len(touched) if isinstance(touched, list) else 0
    return {
        "id": f"code:{iteration_id}",
        "kind": "code",
        "summary": f"{scope} code manifest with {touched_count} touched path(s)",
        "status": scope or "unknown",
        "iteration_id": iteration_id,
        "git_commit": iteration.get("git_commit"),
        "primary_metric": None,
        "source_refs": [source_ref(root, manifest_path, "code_manifest")],
        "detail_ref": manifest_path,
    }


def promotion_record(root: Path, iteration: dict[str, Any]) -> dict[str, Any] | None:
    implementation = iteration.get("implementation")
    if not isinstance(implementation, dict):
        return None
    promotion = implementation.get("promotion")
    if not isinstance(promotion, dict):
        return None
    status = nonempty(promotion.get("status"))
    if status in {"", "not_applicable"}:
        return None
    plan_path = nonempty(promotion.get("plan_path"))
    iteration_id = nonempty(iteration.get("id"))
    refs = [source_ref(root, "iteration_log.json", "iteration_log")]
    if plan_path:
        refs.append(source_ref(root, plan_path, "promotion_plan"))
    return {
        "id": f"promotion:{iteration_id}",
        "kind": "promotion",
        "summary": f"promotion status={status}",
        "status": status,
        "iteration_id": iteration_id,
        "git_commit": promotion.get("promoted_commit") or iteration.get("git_commit"),
        "primary_metric": None,
        "source_refs": refs,
        "detail_ref": plan_path or None,
    }


def docchain_records(root: Path) -> list[dict[str, Any]]:
    index_path = root / ".evidence" / "index.json"
    if not index_path.is_file():
        return []
    index = load_json(index_path)
    docs = index.get("docs")
    if not isinstance(docs, dict):
        return []
    records = []
    for doc_id, entry in docs.items():
        if not isinstance(entry, dict):
            continue
        chain_path = nonempty(entry.get("evidence_chain_path"))
        audit_result = nonempty(entry.get("audit_result")) or "unknown"
        refs = []
        if chain_path:
            refs.append(source_ref(root, chain_path, "evidence_chain"))
        manifest_path = nonempty(entry.get("source_manifest_path"))
        if manifest_path:
            refs.append(source_ref(root, manifest_path, "source_manifest"))
        records.append(
            {
                "id": f"docchain:{doc_id}",
                "kind": "docchain",
                "summary": f"latest docchain for {doc_id}",
                "status": audit_result,
                "iteration_id": None,
                "git_commit": None,
                "primary_metric": None,
                "source_refs": refs,
                "detail_ref": chain_path or None,
            }
        )
    return records


def discovery_records(root: Path) -> list[dict[str, Any]]:
    path = root / "docs" / "45_discoveries" / "Discovery_Ledger.md"
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 7 or cells[0].lower() in {"id", "pending"}:
            continue
        identifier, _date, level, status, summary, evidence_refs, _hint = cells[:7]
        if not identifier:
            continue
        records.append(
            {
                "id": f"discovery:{identifier}",
                "kind": "discovery",
                "summary": summary or identifier,
                "status": status or "open",
                "iteration_id": None,
                "git_commit": None,
                "primary_metric": None,
                "source_refs": [
                    source_ref(
                        root,
                        path.relative_to(root).as_posix(),
                        "discovery_ledger",
                    )
                ],
                "detail_ref": path.relative_to(root).as_posix(),
                "level": level or "observation",
                "evidence_refs": evidence_refs,
            }
        )
    if not records:
        records.append(
            {
                "id": "discovery:ledger",
                "kind": "discovery",
                "summary": "Discovery ledger exists but has no active entries",
                "status": "empty",
                "iteration_id": None,
                "git_commit": None,
                "primary_metric": None,
                "source_refs": [
                    source_ref(
                        root,
                        path.relative_to(root).as_posix(),
                        "discovery_ledger",
                    )
                ],
                "detail_ref": path.relative_to(root).as_posix(),
            }
        )
    return records


def experiment_queue_records(root: Path) -> list[dict[str, Any]]:
    path = root / "docs" / "40_iterations" / "Experiment_Queue.md"
    rel = "docs/40_iterations/Experiment_Queue.md"
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() in {"id", "queue id", "pending"}:
            continue
        identifier = cells[0]
        status = cells[2] if len(cells) > 2 else "open"
        axis = cells[3] if len(cells) > 3 else ""
        summary = cells[4] if len(cells) > 4 else axis or identifier
        records.append(
            {
                "id": f"experiment_queue:{identifier}",
                "kind": "experiment_queue",
                "summary": summary or identifier,
                "status": status or "open",
                "iteration_id": None,
                "git_commit": None,
                "primary_metric": None,
                "source_refs": [source_ref(root, rel, "experiment_queue")],
                "detail_ref": rel,
                "priority": cells[1] if len(cells) > 1 else "",
                "assurance_axis": axis,
                "evidence_needed": cells[6] if len(cells) > 6 else "",
            }
        )
    if not records:
        records.append(
            {
                "id": "experiment_queue:index",
                "kind": "experiment_queue",
                "summary": "Experiment queue exists but has no active entries",
                "status": "empty",
                "iteration_id": None,
                "git_commit": None,
                "primary_metric": None,
                "source_refs": [source_ref(root, rel, "experiment_queue")],
                "detail_ref": rel,
            }
        )
    return records


def research_wiki_records(root: Path) -> list[dict[str, Any]]:
    path = root / "docs" / "45_discoveries" / "Research_Wiki.md"
    rel = "docs/45_discoveries/Research_Wiki.md"
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() in {"id", "wiki id", "pending"}:
            continue
        identifier = cells[0]
        topic_type = cells[1] if len(cells) > 1 else "note"
        status = cells[2] if len(cells) > 2 else "open"
        summary = cells[3] if len(cells) > 3 else identifier
        records.append(
            {
                "id": f"research_wiki:{identifier}",
                "kind": "research_wiki",
                "summary": summary or identifier,
                "status": status or "open",
                "iteration_id": None,
                "git_commit": None,
                "primary_metric": None,
                "source_refs": [source_ref(root, rel, "research_wiki")],
                "detail_ref": rel,
                "topic_type": topic_type,
                "evidence_refs": cells[4] if len(cells) > 4 else "",
            }
        )
    if not records:
        records.append(
            {
                "id": "research_wiki:index",
                "kind": "research_wiki",
                "summary": "Research Wiki exists but has no active entries",
                "status": "empty",
                "iteration_id": None,
                "git_commit": None,
                "primary_metric": None,
                "source_refs": [source_ref(root, rel, "research_wiki")],
                "detail_ref": rel,
            }
        )
    return records


def build_light_index(root: Path) -> dict[str, Any]:
    log_path = root / "iteration_log.json"
    log = load_json(log_path) if log_path.is_file() else {"iterations": []}
    if not isinstance(log, dict):
        raise ValueError("iteration_log.json must contain an object")
    iterations = log.get("iterations", [])
    if not isinstance(iterations, list):
        raise ValueError("iteration_log.json iterations must be a list")
    records: list[dict[str, Any]] = []
    for iteration in iterations:
        if not isinstance(iteration, dict):
            continue
        records.append(run_record(root, log, iteration))
        code = code_record(root, iteration)
        if code is not None:
            records.append(code)
        promotion = promotion_record(root, iteration)
        if promotion is not None:
            records.append(promotion)
    records.extend(docchain_records(root))
    records.extend(discovery_records(root))
    records.extend(experiment_queue_records(root))
    records.extend(research_wiki_records(root))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "records": records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        index = build_light_index(args.workspace_root)
        output = args.workspace_root / args.output
        atomic_write_json(output, index)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(index, indent=2, ensure_ascii=False))
    else:
        print(f"WROTE {args.output.as_posix()} records={len(index['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
