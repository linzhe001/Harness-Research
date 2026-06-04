#!/usr/bin/env python3
"""Compile a minimal evidence chain for a current Markdown document.

This v0 compiler does not author the Markdown body. It reads an existing target
document plus explicit source artifacts, extracts lightweight fact markers, and
writes:

- evidence_chain.json
- source_manifest.json
- doc_audit.json

The goal is to make doc compilation operational while keeping factual judgment
with the agent/human review loop.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

MARKER_RE = re.compile(r"\[(F|U|D|L):([A-Za-z0-9_.-]+)\]")
SCHEMA_VERSION = "0.1"
HEADER_PATH_LABELS = {"Evidence chain", "Evidence audit"}
MAX_PREVIEW_CHARS = 1200
MAX_PREVIEW_LINES = 16
TEXT_PREVIEW_SUFFIXES = {
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".log",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
GENERATED_UNTRACKED_PREFIXES = (
    ".auto_iterate/",
    ".evidence/",
    ".harness_hooks/",
    ".pytest_cache/",
    "__pycache__/",
    "docs/_site/",
    "docs/_views/",
)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def doc_id_for(doc_path: Path, workspace_root: Path) -> str:
    relative = relpath(doc_path, workspace_root)
    if relative.endswith(".md"):
        relative = relative[:-3]
    return relative.replace("/", "__")


def infer_kind(path: Path) -> str:
    name = path.name
    suffix = path.suffix.lower()
    if name in {"PROJECT_STATE.json", "iteration_log.json", "project_map.json"}:
        return "state_json"
    if suffix == ".md":
        return "markdown"
    if suffix in {".yaml", ".yml", ".toml", ".ini"}:
        return "config"
    if suffix == ".json":
        return "json"
    if suffix in {".py", ".go", ".rs", ".ts", ".tsx", ".js", ".sh"}:
        return "code"
    if suffix in {".log", ".txt"}:
        return "log"
    return "artifact"


def mime_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".json":
        return "application/json"
    if suffix in {".yaml", ".yml"}:
        return "application/yaml"
    if suffix == ".toml":
        return "application/toml"
    if suffix in TEXT_PREVIEW_SUFFIXES:
        return "text/plain"
    return "application/octet-stream"


def preview_for_path(
    path: Path,
    workspace_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    relative = relpath(path, workspace_root)
    locator = {
        "path": relative,
        "start_line": None,
        "end_line": None,
        "selector": None,
        "row_id": None,
    }
    if path.suffix.lower() not in TEXT_PREVIEW_SUFFIXES:
        excerpt = "Preview unavailable for non-text artifact."
        return locator, {
            "title": relative,
            "excerpt": excerpt,
            "excerpt_hash": sha256_bytes(excerpt.encode("utf-8")),
            "mime_type": mime_type_for(path),
            "truncated": False,
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    excerpt_lines = lines[:MAX_PREVIEW_LINES]
    excerpt = "\n".join(excerpt_lines).strip() or "(empty file)"
    truncated = len(lines) > MAX_PREVIEW_LINES or len(excerpt) > MAX_PREVIEW_CHARS
    if len(excerpt) > MAX_PREVIEW_CHARS:
        excerpt = excerpt[:MAX_PREVIEW_CHARS].rstrip() + "..."
    locator["start_line"] = 1 if lines else None
    locator["end_line"] = min(len(lines), MAX_PREVIEW_LINES) if lines else None
    return locator, {
        "title": relative,
        "excerpt": excerpt,
        "excerpt_hash": sha256_bytes(excerpt.encode("utf-8")),
        "mime_type": mime_type_for(path),
        "truncated": truncated,
    }


def run_git(workspace_root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace_root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def run_git_bytes(workspace_root: Path, args: list[str]) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace_root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout


def is_generated_untracked_path(relative: str) -> bool:
    normalized = relative.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in GENERATED_UNTRACKED_PREFIXES
    )


def source_status_summary(status: str | None) -> str:
    if not status:
        return ""
    kept: list[str] = []
    for line in status.splitlines():
        stripped = line.strip()
        if stripped.startswith("?? "):
            relative = stripped[3:].strip()
            if is_generated_untracked_path(relative):
                continue
        kept.append(line)
    return "\n".join(kept)


def git_untracked_files(
    workspace_root: Path,
    snapshot_allowlist: set[str] | None = None,
) -> list[str]:
    output = run_git(workspace_root, ["ls-files", "--others", "--exclude-standard"])
    if not output:
        return []
    untracked = [line.strip() for line in output.splitlines() if line.strip()]
    result: list[str] = []
    for relative in untracked:
        normalized = relative.replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        if is_generated_untracked_path(normalized):
            continue
        if snapshot_allowlist is not None and normalized not in snapshot_allowlist:
            continue
        result.append(normalized)
    return result


def snapshot_untracked_files(
    workspace_root: Path,
    chain_dir: Path,
    untracked_paths: list[str],
) -> list[dict[str, str]]:
    snapshots: list[dict[str, str]] = []
    workspace = workspace_root.resolve()
    snapshot_root = chain_dir / "untracked"
    for relative in untracked_paths:
        source = (workspace / relative).resolve()
        try:
            source.relative_to(workspace)
        except ValueError:
            continue
        if not source.is_file():
            continue
        data = source.read_bytes()
        destination = snapshot_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp = destination.with_suffix(destination.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(destination)
        snapshots.append(
            {
                "path": relative,
                "snapshot_path": relpath(destination, workspace),
                "hash": sha256_bytes(data),
            }
        )
    return snapshots


def write_dirty_patch(
    workspace_root: Path,
    chain_dir: Path,
    status: str,
    untracked_paths: list[str],
) -> tuple[str | None, str | None, list[dict[str, str]]]:
    patch_parts: list[bytes] = []
    for args in (["diff", "--binary", "--"], ["diff", "--cached", "--binary", "--"]):
        output = run_git_bytes(workspace_root, args)
        if output:
            patch_parts.append(output)
    untracked_snapshots = snapshot_untracked_files(
        workspace_root,
        chain_dir,
        untracked_paths,
    )
    if untracked_snapshots:
        snapshot_lines = ["# untracked files snapshotted"]
        snapshot_lines.extend(
            f"{item['path']} -> {item['snapshot_path']} {item['hash']}"
            for item in untracked_snapshots
        )
        patch_parts.append(("\n".join(snapshot_lines) + "\n").encode("utf-8"))
    if not patch_parts and status:
        patch_parts.append(("# git status --short\n" + status + "\n").encode("utf-8"))
    if not patch_parts:
        return None, None, untracked_snapshots

    chain_dir.mkdir(parents=True, exist_ok=True)
    patch = b"\n".join(patch_parts)
    patch_path = chain_dir / "patch.diff"
    tmp = patch_path.with_suffix(patch_path.suffix + ".tmp")
    tmp.write_bytes(patch)
    tmp.replace(patch_path)
    digest = sha256_bytes(patch)
    return relpath(patch_path, workspace_root), digest, untracked_snapshots


def snapshot_allowlist_for(paths: list[Path], workspace_root: Path) -> set[str]:
    allowlist: set[str] = set()
    workspace = workspace_root.resolve()
    for path in paths:
        try:
            relative = path.resolve().relative_to(workspace).as_posix()
        except ValueError:
            continue
        if not is_generated_untracked_path(relative):
            allowlist.add(relative)
    return allowlist


def git_context(
    workspace_root: Path,
    chain_dir: Path | None = None,
    snapshot_paths: list[Path] | None = None,
) -> dict[str, Any]:
    commit = run_git(workspace_root, ["rev-parse", "HEAD"])
    branch = run_git(workspace_root, ["branch", "--show-current"])
    raw_status = run_git(workspace_root, ["status", "--short", "--untracked-files=all"])
    status = source_status_summary(raw_status)
    is_dirty = bool(status)
    diff_path = None
    diff_hash = None
    untracked_snapshots: list[dict[str, str]] = []
    if is_dirty and chain_dir is not None:
        snapshot_allowlist = (
            snapshot_allowlist_for(snapshot_paths, workspace_root)
            if snapshot_paths is not None
            else None
        )
        diff_path, diff_hash, untracked_snapshots = write_dirty_patch(
            workspace_root,
            chain_dir,
            status or "",
            git_untracked_files(workspace_root, snapshot_allowlist),
        )
    return {
        "commit": commit,
        "branch": branch,
        "is_dirty": is_dirty,
        "status_summary": status or "",
        "raw_status_summary": raw_status or "",
        "generated_untracked_prefixes": list(GENERATED_UNTRACKED_PREFIXES),
        "untracked_snapshot_policy": "explicit_doc_and_sources_only",
        "diff_path": diff_path,
        "diff_hash": diff_hash,
        "untracked_snapshots": untracked_snapshots,
    }


def build_id(workspace_root: Path) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    commit = run_git(workspace_root, ["rev-parse", "--short", "HEAD"]) or "nogit"
    return f"{now}_{commit}"


def extract_markers(text: str) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    markers: list[tuple[str, str]] = []
    for match in MARKER_RE.finditer(text):
        marker = (match.group(1), match.group(2))
        if marker not in seen:
            seen.add(marker)
            markers.append(marker)
    return markers


def fact_status(marker_type: str) -> str:
    if marker_type == "D":
        return "DECISION"
    if marker_type == "L":
        return "LESSON"
    return "FACT"


def header_line(label: str, value: str) -> str:
    if label in HEADER_PATH_LABELS:
        return f"{label}: `{value}`"
    return f"{label}: {value}"


def upsert_markdown_headers(text: str, headers: dict[str, str]) -> tuple[str, bool]:
    lines = text.splitlines()
    if not lines:
        lines = ["# Untitled"]

    top_end = len(lines)
    for index, line in enumerate(lines[1:], start=1):
        if line.startswith("## "):
            top_end = index
            break

    replaced: set[str] = set()
    for index in range(top_end):
        for label, value in headers.items():
            if re.match(
                rf"^\s*{re.escape(label)}\s*:",
                lines[index],
                flags=re.IGNORECASE,
            ):
                lines[index] = header_line(label, value)
                replaced.add(label)
                break

    missing = [
        (label, value) for label, value in headers.items() if label not in replaced
    ]
    if missing:
        insert_at = 1 if lines and lines[0].startswith("#") else 0
        for index in range(top_end - 1, -1, -1):
            if re.match(r"^[A-Za-z][A-Za-z ]+:", lines[index]):
                insert_at = index + 1
                break
        lines[insert_at:insert_at] = [
            header_line(label, value) for label, value in missing
        ]

    updated = "\n".join(lines) + "\n"
    return updated, updated != text


def source_entries(
    paths: list[Path],
    workspace_root: Path,
    *,
    doc_id: str,
    build_id_value: str,
    support_relation: str = "context_only",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    read_set: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for index, path in enumerate(paths, start=1):
        file_hash = sha256_file(path)
        relative = relpath(path, workspace_root)
        evidence_id = f"E{index:03d}"
        span_id = f"{doc_id}:{build_id_value}:{evidence_id}"
        kind = infer_kind(path)
        locator, preview = preview_for_path(path, workspace_root)
        read_set.append(
            {
                "path": relative,
                "kind": kind,
                "reason": "explicit source for evidence compilation",
                "hash": file_hash,
                "facts_extracted": [],
            }
        )
        evidence.append(
            {
                "evidence_id": evidence_id,
                "span_id": span_id,
                "kind": kind,
                "path": relative,
                "git_commit": None,
                "start_line": locator["start_line"],
                "end_line": locator["end_line"],
                "symbol": None,
                "excerpt_hash": file_hash,
                "locator": locator,
                "preview": preview,
                "supports": [],
                "support_relation": support_relation,
                "human_note": (
                    "Explicit source read by compile_doc. Non-context support "
                    "relations mean the caller has reviewed the source against "
                    "the marked claims."
                ),
            }
        )
    return read_set, evidence


def support_edges_for(
    evidence: list[dict[str, Any]],
    *,
    fact_confidence: str,
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for entry in evidence:
        edges.append(
            {
                "evidence_id": entry["evidence_id"],
                "support_relation": entry["support_relation"],
                "confidence": fact_confidence,
                "preview_ref": entry["span_id"],
                "locator": entry["locator"],
            }
        )
    return edges


def compile_document(
    workspace_root: Path,
    doc_path: Path,
    sources: list[Path],
    *,
    build_id_override: str | None = None,
    compiled_by: str = "tooling/evidence/compile_doc.py",
    fact_confidence: str = "low",
    support_relation: str = "context_only",
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    doc = (
        (workspace / doc_path).resolve()
        if not doc_path.is_absolute()
        else doc_path.resolve()
    )
    if not doc.exists():
        raise FileNotFoundError(f"doc not found: {doc}")
    if fact_confidence not in {"low", "medium", "high"}:
        raise ValueError("fact_confidence must be one of low, medium, high")
    if support_relation not in {"context_only", "partially_supports", "supports"}:
        raise ValueError(
            "support_relation must be one of context_only, partially_supports, supports"
        )
    if support_relation != "context_only" and fact_confidence == "low":
        raise ValueError(
            "support_relation supports/partially_supports requires medium or "
            "high fact_confidence"
        )
    resolved_sources: list[Path] = []
    for source in sources:
        resolved = (
            (workspace / source).resolve()
            if not source.is_absolute()
            else source.resolve()
        )
        if not resolved.exists():
            raise FileNotFoundError(f"source not found: {resolved}")
        resolved_sources.append(resolved)

    doc_id = doc_id_for(doc, workspace)
    current_build_id = build_id_override or build_id(workspace)
    chain_dir = workspace / ".evidence" / "chains" / doc_id / current_build_id
    chain_id = f"docchain_{current_build_id}"
    chain_path = chain_dir / "evidence_chain.json"
    manifest_path = chain_dir / "source_manifest.json"
    audit_path = chain_dir / "doc_audit.json"
    audit_result = "PASS" if resolved_sources else "DRAFT_ONLY"
    read_paths = [doc, *resolved_sources]
    source_git_context = git_context(workspace, chain_dir, snapshot_paths=read_paths)

    doc_text_before = doc.read_text(encoding="utf-8")
    header_values = {
        "Evidence chain": relpath(chain_path, workspace),
        "Evidence audit": relpath(audit_path, workspace),
        "Audit result": audit_result,
    }
    doc_text, markdown_header_updated = upsert_markdown_headers(
        doc_text_before,
        header_values,
    )
    if markdown_header_updated:
        atomic_write_text(doc, doc_text)

    markers = extract_markers(doc_text)
    read_set, evidence = source_entries(
        read_paths,
        workspace,
        doc_id=doc_id,
        build_id_value=current_build_id,
        support_relation=support_relation,
    )
    evidence_ids = [entry["evidence_id"] for entry in evidence]
    support_edges = support_edges_for(evidence, fact_confidence=fact_confidence)

    facts: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    fact_marker_ids: set[str] = set()
    for marker_type, marker_id in markers:
        if marker_type == "U":
            unresolved.append(
                {
                    "question_id": marker_id,
                    "marker": f"[U:{marker_id}]",
                    "status": "open",
                    "note": (
                        "Unresolved marker found in Markdown during compile_doc v0."
                    ),
                }
            )
            continue
        fact_marker_ids.add(marker_id)
        facts.append(
            {
                "fact_id": marker_id,
                "fact_type": "markdown_marker",
                "claim": (
                    f"Markdown marker [{marker_type}:{marker_id}] is present in "
                    f"{relpath(doc, workspace)}."
                ),
                "epistemic_status": fact_status(marker_type),
                "confidence": fact_confidence,
                "evidence_refs": evidence_ids,
                "support_edges": support_edges,
                "support_summary": (
                    "compile_doc records marker presence and explicit sources; "
                    "non-low confidence requires caller review of the Markdown "
                    "claim text against the sources."
                ),
                "limitations": [
                    "This v0 compiler does not infer claim text or verify "
                    "semantic support automatically."
                ],
                "used_in_doc": True,
                "doc_anchors": [
                    {
                        "doc_path": relpath(doc, workspace),
                        "anchor": f"[{marker_type}:{marker_id}]",
                    }
                ],
                "review_status": "needs_review",
            }
        )

    for entry in evidence:
        entry["supports"] = sorted(fact_marker_ids)

    chain = {
        "schema_version": SCHEMA_VERSION,
        "chain_id": chain_id,
        "doc": {
            "path": relpath(doc, workspace),
            "doc_id": doc_id,
            "compiled_at": (
                dt.datetime.now(dt.timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            ),
            "compiled_by": compiled_by,
            "skill": "doc-compiler",
        },
        "git": source_git_context,
        "facts": facts,
        "evidence": evidence,
        "unresolved": unresolved,
        "doc_links": {
            "markdown_path": relpath(doc, workspace),
            "audit_path": relpath(audit_path, workspace),
            "source_manifest_path": relpath(manifest_path, workspace),
        },
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "chain_id": chain_id,
        "read_set": read_set,
        "ignored_candidates": [],
    }

    checks: list[dict[str, Any]] = [
        {
            "check": "explicit_sources_provided",
            "result": "PASS" if resolved_sources else "FAIL",
            "detail": f"{len(resolved_sources)} explicit source(s) provided.",
        },
        {
            "check": "all_fact_markers_recorded",
            "result": "PASS",
            "detail": f"{len(facts)} fact/decision/lesson marker(s) recorded.",
        },
        {
            "check": "open_questions_recorded",
            "result": "PASS",
            "detail": f"{len(unresolved)} unresolved marker(s) recorded.",
        },
        {
            "check": "semantic_support_review_required",
            "result": "WARN" if facts else "PASS",
            "detail": (
                "compile_doc v0 records explicit sources but does not prove "
                "semantic support."
            ),
        },
        {
            "check": "markdown_header_updated",
            "result": "PASS",
            "detail": (
                "Evidence chain, Evidence audit, and Audit result headers point "
                "at this build."
            ),
        },
        {
            "check": "git_context_recorded",
            "result": "WARN" if source_git_context["is_dirty"] else "PASS",
            "detail": (
                "Source git context was dirty; patch preserved."
                if source_git_context["diff_path"]
                else "Source git context was recorded."
            ),
        },
    ]
    audit = {
        "schema_version": SCHEMA_VERSION,
        "doc_path": relpath(doc, workspace),
        "evidence_chain_path": relpath(chain_path, workspace),
        "audit_result": audit_result,
        "checks": checks,
        "unsupported_claims": [],
        "unresolved_fact_markers": [],
        "stale_sources": [],
    }

    atomic_write_json(chain_path, chain)
    atomic_write_json(manifest_path, manifest)
    atomic_write_json(audit_path, audit)
    index_path = update_evidence_index(
        workspace,
        doc_id,
        current_build_id,
        chain_path,
        manifest_path,
        audit_path,
        audit_result,
        chain=chain,
    )

    return {
        "ok": audit_result == "PASS",
        "doc_id": doc_id,
        "build_id": current_build_id,
        "chain_dir": str(chain_dir),
        "evidence_chain_path": str(chain_path),
        "source_manifest_path": str(manifest_path),
        "doc_audit_path": str(audit_path),
        "index_path": str(index_path),
        "fact_count": len(facts),
        "unresolved_count": len(unresolved),
        "audit_result": audit_result,
        "markdown_header_updated": markdown_header_updated,
    }


def update_evidence_index(
    workspace_root: Path,
    doc_id: str,
    current_build_id: str,
    chain_path: Path,
    manifest_path: Path,
    audit_path: Path,
    audit_result: str,
    *,
    chain: dict[str, Any] | None = None,
) -> Path:
    index_path = workspace_root / ".evidence" / "index.json"
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if not isinstance(data, dict):
            data = {}
    else:
        data = {}

    data.setdefault("schema_version", SCHEMA_VERSION)
    docs = data.setdefault("docs", {})
    history = data.setdefault("history", [])
    latest_docchain_by_doc = data.setdefault("latest_docchain_by_doc", {})
    facts_by_id = data.setdefault("facts_by_id", {})
    evidence_by_id = data.setdefault("evidence_by_id", {})
    source_spans_by_id = data.setdefault("source_spans_by_id", {})
    markers_by_doc = data.setdefault("markers_by_doc", {})
    entry = {
        "doc_id": doc_id,
        "latest_build_id": current_build_id,
        "evidence_chain_path": relpath(chain_path, workspace_root),
        "source_manifest_path": relpath(manifest_path, workspace_root),
        "doc_audit_path": relpath(audit_path, workspace_root),
        "audit_result": audit_result,
    }
    docs[doc_id] = entry
    latest_docchain_by_doc[doc_id] = entry
    history.append(entry)
    if chain is not None:
        doc_info = chain.get("doc", {})
        doc_path_value = doc_info.get("path", "")
        doc_markers: list[dict[str, Any]] = []
        for fact in chain.get("facts", []):
            if not isinstance(fact, dict):
                continue
            fact_id = str(fact.get("fact_id", ""))
            facts_by_id[fact_id] = {
                "fact_id": fact_id,
                "doc_id": doc_id,
                "latest_build_id": current_build_id,
                "doc_path": doc_path_value,
                "evidence_chain_path": relpath(chain_path, workspace_root),
                "claim": str(fact.get("claim", "")),
                "epistemic_status": fact.get("epistemic_status"),
                "confidence": fact.get("confidence"),
                "evidence_refs": fact.get("evidence_refs", []),
                "support_edges": fact.get("support_edges", []),
                "doc_anchors": fact.get("doc_anchors", []),
            }
            for anchor in fact.get("doc_anchors", []):
                if not isinstance(anchor, dict):
                    continue
                marker = str(anchor.get("anchor", ""))
                marker_type = marker[1:2] if marker.startswith("[") else "F"
                doc_markers.append(
                    {
                        "marker": marker,
                        "marker_type": marker_type,
                        "marker_id": fact_id,
                        "fact_id": fact_id,
                        "question_id": None,
                    }
                )
        for unresolved in chain.get("unresolved", []):
            if not isinstance(unresolved, dict):
                continue
            question_id = str(unresolved.get("question_id", ""))
            doc_markers.append(
                {
                    "marker": str(unresolved.get("marker", f"[U:{question_id}]")),
                    "marker_type": "U",
                    "marker_id": question_id,
                    "fact_id": None,
                    "question_id": question_id,
                }
            )
        if doc_path_value:
            markers_by_doc[doc_path_value] = doc_markers
        for evidence_entry in chain.get("evidence", []):
            if not isinstance(evidence_entry, dict):
                continue
            span_id = str(
                evidence_entry.get(
                    "span_id",
                    (
                        f"{doc_id}:{current_build_id}:"
                        f"{evidence_entry.get('evidence_id', '')}"
                    ),
                )
            )
            span = {
                "span_id": span_id,
                "doc_id": doc_id,
                "latest_build_id": current_build_id,
                "evidence_id": str(evidence_entry.get("evidence_id", "")),
                "kind": str(evidence_entry.get("kind", "")),
                "path": str(evidence_entry.get("path", "")),
                "supports": evidence_entry.get("supports", []),
                "support_relation": evidence_entry.get("support_relation"),
                "evidence_chain_path": relpath(chain_path, workspace_root),
                "locator": evidence_entry.get("locator", {}),
                "preview": evidence_entry.get("preview", {}),
            }
            evidence_by_id[span_id] = span
            source_spans_by_id[span_id] = span
    atomic_write_json(index_path, data)
    return index_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a minimal Harness evidence docchain."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--doc",
        type=Path,
        required=True,
        help="Target Markdown document.",
    )
    parser.add_argument(
        "--source",
        "--sources",
        dest="sources",
        type=Path,
        nargs="+",
        required=True,
        help="Explicit source artifacts read for this compilation.",
    )
    parser.add_argument(
        "--build-id",
        dest="build_id_override",
        help="Optional deterministic build id.",
    )
    parser.add_argument("--compiled-by", default="tooling/evidence/compile_doc.py")
    parser.add_argument(
        "--fact-confidence",
        choices=["low", "medium", "high"],
        default="low",
        help="Confidence assigned to extracted fact markers after review.",
    )
    parser.add_argument(
        "--support-relation",
        choices=["context_only", "partially_supports", "supports"],
        default="context_only",
        help="How the source artifacts support the marked facts.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        summary = compile_document(
            args.workspace_root,
            args.doc,
            args.sources,
            build_id_override=args.build_id_override,
            compiled_by=args.compiled_by,
            fact_confidence=args.fact_confidence,
            support_relation=args.support_relation,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"{summary['audit_result']} {summary['chain_dir']}")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
