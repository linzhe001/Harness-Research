#!/usr/bin/env python3
"""Build a paper-facing experiment evidence index from WF10 run records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLING_DIR = REPO_ROOT / "tooling"
AUTO_ITERATE_DIR = TOOLING_DIR / "auto_iterate" / "scripts"
for candidate in (TOOLING_DIR, AUTO_ITERATE_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from auto_iterate.events import iso_now  # noqa: E402
from auto_iterate.state import atomic_write_json  # noqa: E402
from build_light_evidence_index import build_light_index  # noqa: E402
from check_workflow_state import (  # noqa: E402
    existing_iteration_report_path,
    iteration_metrics,
)
from run_artifacts import run_artifact_errors  # noqa: E402

SCHEMA_VERSION = "0.1"
COMPLETED_STATUSES = {"completed", "complete", "done", "success", "succeeded"}
MANIFEST_PATH_FIELDS = (
    "exp_dir",
    "resolved_config_path",
    "stdout_log_path",
    "git_snapshot_path",
    "checkpoint_path",
    "wandb_url",
    "tensorboard_log_dir",
)
MANIFEST_TEXT_FIELDS = (
    "resolved_config_path",
    "stdout_log_path",
    "eval_artifact_paths",
)
MAX_SOURCE_TEXT_CHARS = 12_000
MAX_SNIPPET_CHARS = 240
DEFAULT_FORBIDDEN_WORDING = (
    "Do not claim superiority, novelty, statistical significance, or "
    "generalization beyond the recorded protocol."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build docs/30_evidence/Experiment_Evidence_Index.*."
    )
    parser.add_argument("--workspace-root", default=".", type=Path)
    parser.add_argument("--iteration-log", default="iteration_log.json", type=Path)
    parser.add_argument(
        "--output-json",
        default=Path("docs/30_evidence/Experiment_Evidence_Index.json"),
        type=Path,
    )
    parser.add_argument(
        "--output-md",
        default=Path("docs/30_evidence/Experiment_Evidence_Index.md"),
        type=Path,
    )
    parser.add_argument("--json", action="store_true", help="Print index JSON.")
    return parser.parse_args()


def load_iteration_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("iterations", "entries", "log"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def as_relative(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def nonempty_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def compact_text(value: str, *, limit: int = MAX_SNIPPET_CHARS) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def unique_nonempty(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = compact_text(value)
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def read_text_sample(path: Path) -> str:
    if not path.is_file():
        return ""
    with path.open(encoding="utf-8", errors="ignore") as handle:
        return handle.read(MAX_SOURCE_TEXT_CHARS)


def add_read_source(
    sources: list[dict[str, Any]],
    *,
    source_type: str,
    path: str,
    role: str,
    weak_signal: bool = False,
) -> None:
    item = {
        "source_type": source_type,
        "path": path,
        "role": role,
        "weak_signal": weak_signal,
    }
    if item not in sources:
        sources.append(item)


def manifest_candidates(root: Path, manifest: dict[str, Any], value: str) -> list[Path]:
    path = Path(value)
    if path.is_absolute():
        return [path]
    candidates = [root / path]
    exp_dir = nonempty_string(manifest.get("exp_dir"))
    if exp_dir:
        candidates.append(root / exp_dir / path)
    return candidates


def first_existing_manifest_path(
    root: Path,
    manifest: dict[str, Any],
    value: str,
) -> Path | None:
    for candidate in manifest_candidates(root, manifest, value):
        if candidate.exists():
            return candidate
    return None


def read_manifest_text_sources(
    root: Path,
    iteration: dict[str, Any],
    evidence_sources: list[dict[str, Any]],
) -> dict[str, str]:
    manifest = iteration.get("run_manifest")
    if not isinstance(manifest, dict):
        return {}
    result: dict[str, str] = {}
    for field in MANIFEST_TEXT_FIELDS:
        value = manifest.get(field)
        values = value if isinstance(value, list) else [value]
        snippets: list[str] = []
        for item in values:
            path_value = nonempty_string(item)
            if not path_value:
                continue
            path = first_existing_manifest_path(root, manifest, path_value)
            if path is None:
                continue
            text = read_text_sample(path)
            if not text:
                continue
            add_read_source(
                evidence_sources,
                source_type="run_artifact",
                path=as_relative(root, path),
                role=field,
            )
            snippets.append(text)
        if snippets:
            result[field] = "\n".join(snippets)
    return result


def field_texts(
    iteration: dict[str, Any],
    keys: tuple[str, ...],
) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for key in keys:
        value = iteration.get(key)
        if isinstance(value, str) and value.strip():
            values.append((key, value.strip()))
    config_diff = iteration.get("config_diff")
    if isinstance(config_diff, dict):
        for key in keys:
            value = config_diff.get(key)
            if isinstance(value, str) and value.strip():
                values.append((f"config_diff.{key}", value.strip()))
    return values


def keyword_lines(text: str, keywords: tuple[str, ...], *, limit: int = 3) -> list[str]:
    if not text:
        return []
    result: list[str] = []
    lowered_keywords = tuple(keyword.lower() for keyword in keywords)
    for raw in text.splitlines():
        line = raw.strip(" #\t")
        if not line or line.startswith("| ---"):
            continue
        lowered = line.lower()
        if any(keyword in lowered for keyword in lowered_keywords):
            result.append(line)
        if len(result) >= limit:
            break
    return result


def summarize_purpose(
    iteration: dict[str, Any],
    report_text: str,
    manifest_texts: dict[str, str],
) -> tuple[str, list[dict[str, str]]]:
    snippets: list[str] = []
    sources: list[dict[str, str]] = []
    for field, value in field_texts(
        iteration,
        (
            "purpose",
            "hypothesis",
            "objective",
            "goal",
            "question",
            "rationale",
            "expected_effect",
            "changes_summary",
            "planned_change",
        ),
    ):
        snippets.append(value)
        sources.append({"source": "iteration_log.json", "field": field})
    for line in keyword_lines(
        report_text,
        ("purpose", "hypothesis", "objective", "goal", "why", "tested"),
    ):
        snippets.append(line)
        sources.append({"source": "iteration_report", "field": "keyword_line"})
    config_text = manifest_texts.get("resolved_config_path", "")
    for line in keyword_lines(
        config_text,
        ("experiment", "purpose", "hypothesis", "objective", "seed", "dataset"),
        limit=2,
    ):
        snippets.append(line)
        sources.append({"source": "resolved_config_path", "field": "keyword_line"})
    values = unique_nonempty(snippets)
    return "; ".join(values[:4]) if values else "not recorded", sources


def summarize_results(
    iteration: dict[str, Any],
    metrics: dict[str, Any],
    report_text: str,
    manifest_texts: dict[str, str],
) -> tuple[str, list[dict[str, str]]]:
    snippets: list[str] = []
    sources: list[dict[str, str]] = []
    if metrics:
        snippets.append(json.dumps(metrics, ensure_ascii=False, sort_keys=True))
        sources.append({"source": "iteration_log.json", "field": "metrics"})
    lessons = iteration.get("lessons")
    if isinstance(lessons, list):
        for lesson in lessons:
            text = nonempty_string(lesson)
            if text:
                snippets.append(text)
                sources.append({"source": "iteration_log.json", "field": "lessons"})
    decision = nonempty_string(iteration.get("decision"))
    if decision:
        snippets.append(f"decision={decision}")
        sources.append({"source": "iteration_log.json", "field": "decision"})
    for line in keyword_lines(
        report_text,
        ("result", "finding", "metric", "accuracy", "loss", "decision"),
    ):
        snippets.append(line)
        sources.append({"source": "iteration_report", "field": "keyword_line"})
    eval_text = manifest_texts.get("eval_artifact_paths", "")
    for line in keyword_lines(
        eval_text,
        ("accuracy", "loss", "metric", "score", "result"),
        limit=3,
    ):
        snippets.append(line)
        sources.append({"source": "eval_artifact_paths", "field": "keyword_line"})
    values = unique_nonempty(snippets)
    return "; ".join(values[:5]) if values else "not recorded", sources


def trust_assessment(
    artifact_errors: list[str],
    evidence_sources: list[dict[str, Any]],
    purpose_sources: list[dict[str, str]],
    result_sources: list[dict[str, str]],
) -> dict[str, Any]:
    source_types = {str(item["source_type"]) for item in evidence_sources}
    purpose_cross_checked = any(
        item["source"] != "iteration_log.json" for item in purpose_sources
    )
    result_cross_checked = any(
        item["source"] != "iteration_log.json" for item in result_sources
    )
    if artifact_errors:
        level = "incomplete"
    elif (
        purpose_cross_checked
        and result_cross_checked
        and "run_artifact" in source_types
    ):
        level = "cross_checked"
    elif "run_artifact" in source_types or "iteration_report" in source_types:
        level = "partially_cross_checked"
    else:
        level = "log_only"
    notes: list[str] = []
    if not purpose_cross_checked:
        notes.append("Purpose is not cross-checked outside iteration_log.json.")
    if not result_cross_checked:
        notes.append("Result summary is not cross-checked outside iteration_log.json.")
    if artifact_errors:
        notes.extend(artifact_errors[:3])
    return {
        "level": level,
        "purpose_cross_checked": purpose_cross_checked,
        "result_cross_checked": result_cross_checked,
        "notes": notes,
    }


def first_claim_candidate(iteration: dict[str, Any]) -> dict[str, Any]:
    candidates = iteration.get("lesson_candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict) and nonempty_string(candidate.get("claim")):
                return candidate
    return {}


def claim_text(iteration: dict[str, Any], candidate: dict[str, Any]) -> str:
    candidate_claim = nonempty_string(candidate.get("claim"))
    if candidate_claim:
        return candidate_claim
    lessons = iteration.get("lessons")
    if isinstance(lessons, list):
        for lesson in lessons:
            text = nonempty_string(lesson)
            if text:
                return text
    return ""


def candidate_boundary(candidate: dict[str, Any]) -> str:
    for key in ("boundary", "scope_limit", "risk_note"):
        value = nonempty_string(candidate.get(key))
        if value:
            return value
    return DEFAULT_FORBIDDEN_WORDING


def candidate_uncertainty(candidate: dict[str, Any]) -> str:
    confidence = nonempty_string(candidate.get("confidence"))
    boundary = nonempty_string(candidate.get("boundary"))
    if confidence and boundary:
        return f"confidence={confidence}; boundary={boundary}"
    if confidence:
        return f"confidence={confidence}"
    if boundary:
        return boundary
    return "not recorded"


def candidate_next_check(candidate: dict[str, Any]) -> str:
    for key in ("future_action", "next_check", "recommended_next_step"):
        value = nonempty_string(candidate.get(key))
        if value:
            return value
    return ""


def manifest_paths(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        return {}
    result = {
        field: manifest[field]
        for field in MANIFEST_PATH_FIELDS
        if nonempty_string(manifest.get(field))
    }
    eval_paths = manifest.get("eval_artifact_paths")
    if isinstance(eval_paths, list):
        result["eval_artifact_paths"] = [
            item for item in eval_paths if nonempty_string(item)
        ]
    return result


def entry_status(
    iteration: dict[str, Any],
    artifact_errors: list[str],
    metrics: dict[str, Any],
    claim: str,
    trust: dict[str, Any],
) -> tuple[str, bool, list[str]]:
    limitations: list[str] = []
    status = nonempty_string(iteration.get("status")).lower()
    completed = status in COMPLETED_STATUSES
    if not completed:
        limitations.append("Iteration is not marked completed.")
    if artifact_errors:
        limitations.extend(artifact_errors[:5])
    if not metrics:
        limitations.append("No metrics recorded.")
    if not claim:
        limitations.append("No lesson or claim candidate recorded.")
    if not trust.get("purpose_cross_checked") or not trust.get(
        "result_cross_checked"
    ):
        limitations.append(
            "Purpose or result evidence is not sufficiently cross-checked."
        )
    valid_for_claim = (
        completed
        and not artifact_errors
        and bool(metrics)
        and bool(claim)
        and bool(trust.get("purpose_cross_checked"))
        and bool(trust.get("result_cross_checked"))
    )
    if valid_for_claim:
        return "valid_for_claim", True, limitations
    if completed and not artifact_errors:
        return "artifact_only", False, limitations
    return "incomplete", False, limitations


def build_index(root: Path, iteration_log: Path) -> dict[str, Any]:
    iterations = load_iteration_log(iteration_log)
    light_index_path = root / ".evidence" / "light" / "index.json"
    light_index_source = (
        ".evidence/light/index.json"
        if light_index_path.is_file()
        else "generated_in_memory"
    )
    try:
        light_index = (
            json.loads(light_index_path.read_text(encoding="utf-8"))
            if light_index_path.is_file()
            else build_light_index(root)
        )
    except (OSError, ValueError, json.JSONDecodeError):
        light_index = {"records": []}
    entries: list[dict[str, Any]] = []
    for index, iteration in enumerate(iterations, start=1):
        iteration_id = nonempty_string(iteration.get("id")) or f"iteration_{index}"
        metrics = iteration_metrics(iteration)
        artifact_errors = run_artifact_errors(root, iteration)
        evidence_sources: list[dict[str, Any]] = []
        add_read_source(
            evidence_sources,
            source_type="iteration_log",
            path=as_relative(root, iteration_log),
            role="weak purpose/result signal",
            weak_signal=True,
        )
        report_path = existing_iteration_report_path(root, iteration_id)
        report_text = ""
        if report_path is not None:
            report_text = read_text_sample(report_path)
            add_read_source(
                evidence_sources,
                source_type="iteration_report",
                path=as_relative(root, report_path),
                role="purpose/result narrative cross-check",
            )
        manifest_texts = read_manifest_text_sources(root, iteration, evidence_sources)
        purpose_summary, purpose_sources = summarize_purpose(
            iteration,
            report_text,
            manifest_texts,
        )
        result_summary, result_sources = summarize_results(
            iteration,
            metrics,
            report_text,
            manifest_texts,
        )
        trust = trust_assessment(
            artifact_errors,
            evidence_sources,
            purpose_sources,
            result_sources,
        )
        candidate = first_claim_candidate(iteration)
        claim = claim_text(iteration, candidate)
        status, valid_for_claim, limitations = entry_status(
            iteration,
            artifact_errors,
            metrics,
            claim,
            trust,
        )
        entries.append(
            {
                "evidence_id": f"exp_ev_{index:03d}",
                "experiment_id": iteration_id,
                "source_iteration_id": iteration_id,
                "run_type": nonempty_string(
                    iteration.get("run_type")
                    or iteration.get("run_manifest", {}).get("run_type")
                ),
                "status": status,
                "valid_for_claim": valid_for_claim,
                "purpose_summary": purpose_summary,
                "purpose_sources": purpose_sources,
                "result_summary": result_summary,
                "result_sources": result_sources,
                "claim_candidate": claim,
                "allowed_wording": claim,
                "forbidden_stronger_wording": candidate_boundary(candidate),
                "metrics": metrics,
                "uncertainty": candidate_uncertainty(candidate),
                "run_manifest_paths": manifest_paths(iteration.get("run_manifest")),
                "analysis_report_path": as_relative(root, report_path),
                "evidence_read_set": evidence_sources,
                "trust_assessment": trust,
                "figure_paths": [
                    item
                    for item in iteration.get("figure_paths", [])
                    if nonempty_string(item)
                ]
                if isinstance(iteration.get("figure_paths"), list)
                else [],
                "limitations": limitations,
                "next_check": candidate_next_check(candidate),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "source": as_relative(root, iteration_log),
        "light_evidence_index": {
            "source": light_index_source,
            "record_count": len(light_index.get("records", []))
            if isinstance(light_index.get("records"), list)
            else 0,
        },
        "entries": entries,
    }


def md_escape(value: object) -> str:
    text = (
        json.dumps(value, ensure_ascii=False)
        if isinstance(value, dict)
        else str(value)
    )
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(index: dict[str, Any]) -> str:
    entries = index["entries"]
    light_source = index.get("light_evidence_index", {}).get("source", "unknown")
    light_count = index.get("light_evidence_index", {}).get("record_count", 0)
    counts = {
        "valid_for_claim": sum(
            1 for item in entries if item["status"] == "valid_for_claim"
        ),
        "artifact_only": sum(
            1 for item in entries if item["status"] == "artifact_only"
        ),
        "incomplete": sum(1 for item in entries if item["status"] == "incomplete"),
    }
    lines = [
        "# Experiment Evidence Index",
        "",
        f"- Generated at: `{index['generated_at']}`",
        f"- Source: `{index['source']}`",
        f"- Light Evidence source: `{light_source}`",
        f"- Light Evidence records: {light_count}",
        f"- Entries: {len(entries)}",
        f"- Valid for claim: {counts['valid_for_claim']}",
        f"- Artifact only: {counts['artifact_only']}",
        f"- Incomplete: {counts['incomplete']}",
        "",
        "| evidence_id | source_iteration_id | status | trust | "
        "purpose_summary | result_summary | claim_candidate | next_check |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in entries:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(item["evidence_id"]),
                    md_escape(item["source_iteration_id"]),
                    md_escape(item["status"]),
                    md_escape(item["trust_assessment"]["level"]),
                    md_escape(item["purpose_summary"]),
                    md_escape(item["result_summary"]),
                    md_escape(item["claim_candidate"]),
                    md_escape(item["next_check"]),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.extend(
        [
            "## Claim Boundary",
            "",
            "Only rows with `valid_for_claim=true` may support paper claims. "
            "Rows marked `artifact_only` or `incomplete` may inform planning, "
            "but they require additional `$run` or `$analyze` work before claim use.",
            "",
            "`iteration_log.json` is a weak signal in this index. Paper claims "
            "should use the purpose/result summaries only after checking "
            "`trust_assessment` and the listed `evidence_read_set` artifacts.",
            "",
        ]
    )
    return "\n".join(lines)


def resolve_output(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def main() -> int:
    args = parse_args()
    root = args.workspace_root.resolve()
    iteration_log = resolve_output(root, args.iteration_log)
    output_json = resolve_output(root, args.output_json)
    output_md = resolve_output(root, args.output_md)
    index = build_index(root, iteration_log)
    atomic_write_json(output_json, index)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(index), encoding="utf-8")
    if args.json:
        print(json.dumps(index, indent=2, ensure_ascii=False))
    else:
        print(f"Wrote {output_json} and {output_md}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
