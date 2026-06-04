#!/usr/bin/env python3
"""Build browser-friendly Evidence Chain preview data for human docs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"
DEFAULT_INDEX_PATH = Path(".evidence/index.json")
DEFAULT_OUTPUT_PATH = Path("docs/_views/evidence_preview_index.json")


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def preview_entry(
    span: dict[str, Any], support_relation: str | None = None
) -> dict[str, Any]:
    preview = span.get("preview")
    if not isinstance(preview, dict):
        preview = {}
    locator = span.get("locator")
    if not isinstance(locator, dict):
        locator = {}
    relation = support_relation or span.get("support_relation")
    path = str(span.get("path", ""))
    return {
        "span_id": str(span.get("span_id", "")),
        "evidence_id": str(span.get("evidence_id", "")),
        "title": str(preview.get("title") or path),
        "path": path,
        "kind": span.get("kind"),
        "support_relation": relation,
        "locator": locator,
        "excerpt": str(preview.get("excerpt", "")),
        "excerpt_hash": preview.get("excerpt_hash"),
        "mime_type": preview.get("mime_type"),
        "truncated": bool(preview.get("truncated", False)),
    }


def fact_previews(
    fact: dict[str, Any],
    evidence_spans: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    source_refs: list[str] = []
    source_previews: list[dict[str, Any]] = []
    edges = fact.get("support_edges", [])
    if not isinstance(edges, list):
        return source_refs, source_previews
    doc_path = str(fact.get("doc_path", ""))
    doc_previews: list[dict[str, Any]] = []
    doc_refs: list[str] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        preview_ref = edge.get("preview_ref")
        if not isinstance(preview_ref, str):
            continue
        span = evidence_spans.get(preview_ref)
        if not isinstance(span, dict):
            continue
        entry = preview_entry(span, support_relation=edge.get("support_relation"))
        if entry["path"] == doc_path:
            doc_refs.append(preview_ref)
            doc_previews.append(entry)
        else:
            source_refs.append(preview_ref)
            source_previews.append(entry)
    refs = [*doc_refs, *source_refs]
    previews = [*doc_previews, *source_previews]
    return refs, previews


def target_path_for_previews(
    previews: list[dict[str, Any]],
    *,
    doc_path: str,
) -> str:
    for preview in previews:
        path = str(preview.get("path") or "")
        if path and path != doc_path:
            return path
    if previews:
        return str(previews[0].get("path") or "")
    return ""


def unresolved_marker_previews(
    doc_path: str,
    evidence_source: dict[str, Any],
) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for span in evidence_source.values():
        if not isinstance(span, dict):
            continue
        if str(span.get("path", "")) == doc_path:
            previews.append(preview_entry(span))
    return previews


def build_preview_index(
    workspace_root: Path,
    *,
    index_path: Path = DEFAULT_INDEX_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    dry_run: bool = False,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    source_index = (workspace / index_path).resolve()
    if not source_index.exists():
        raise FileNotFoundError(
            f"evidence index not found: {relpath(source_index, workspace)}"
        )
    index = load_json_object(source_index)
    evidence_source = index.get("evidence_by_id", {})
    facts_source = index.get("facts_by_id", {})
    markers_source = index.get("markers_by_doc", {})
    if not isinstance(evidence_source, dict):
        raise ValueError(".evidence/index.json evidence_by_id must be an object")
    if not isinstance(facts_source, dict):
        raise ValueError(".evidence/index.json facts_by_id must be an object")
    if not isinstance(markers_source, dict):
        raise ValueError(".evidence/index.json markers_by_doc must be an object")

    evidence = {
        span_id: preview_entry(span)
        for span_id, span in evidence_source.items()
        if isinstance(span_id, str) and isinstance(span, dict)
    }
    facts: dict[str, Any] = {}
    for fact_id, fact in facts_source.items():
        if not isinstance(fact_id, str) or not isinstance(fact, dict):
            continue
        refs, previews = fact_previews(fact, evidence_source)
        facts[fact_id] = {
            "fact_id": fact_id,
            "claim": str(fact.get("claim", "")),
            "epistemic_status": fact.get("epistemic_status"),
            "confidence": fact.get("confidence"),
            "doc_path": str(fact.get("doc_path", "")),
            "doc_id": str(fact.get("doc_id", "")),
            "build_id": str(fact.get("latest_build_id", "")),
            "doc_anchors": fact.get("doc_anchors", []),
            "evidence_refs": refs,
            "previews": previews,
            "target_path": target_path_for_previews(
                previews,
                doc_path=str(fact.get("doc_path", "")),
            ),
        }

    markers: dict[str, Any] = {}
    for doc_path, marker_items in markers_source.items():
        if not isinstance(marker_items, list):
            continue
        for marker in marker_items:
            if not isinstance(marker, dict):
                continue
            marker_type = str(marker.get("marker_type", ""))
            marker_id = str(marker.get("marker_id", ""))
            key = f"{marker_type}:{marker_id}"
            fact_id = marker.get("fact_id")
            previews = (
                facts.get(fact_id, {}).get("previews", [])
                if isinstance(fact_id, str)
                else []
            )
            if not previews and marker_type == "U" and isinstance(doc_path, str):
                previews = unresolved_marker_previews(doc_path, evidence_source)
            target_path = ""
            if isinstance(fact_id, str):
                target_path = str(facts.get(fact_id, {}).get("target_path") or "")
            if not target_path and isinstance(doc_path, str):
                target_path = target_path_for_previews(previews, doc_path=doc_path)
            markers[key] = {
                "marker": str(marker.get("marker", "")),
                "marker_type": marker_type,
                "marker_id": marker_id,
                "fact_id": fact_id,
                "question_id": marker.get("question_id"),
                "previews": previews,
                "target_path": target_path,
            }

    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "source_index_path": relpath(source_index, workspace),
        "facts": facts,
        "evidence": evidence,
        "markers": markers,
    }
    if not dry_run:
        destination = (workspace / output_path).resolve()
        atomic_write_json(destination, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Evidence Chain hover preview data for human docs."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--index", dest="index_path", type=Path, default=DEFAULT_INDEX_PATH
    )
    parser.add_argument(
        "--output", dest="output_path", type=Path, default=DEFAULT_OUTPUT_PATH
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        preview = build_preview_index(
            args.workspace_root,
            index_path=args.index_path,
            output_path=args.output_path,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(preview, indent=2, ensure_ascii=False))
    else:
        print(f"PASS {args.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
