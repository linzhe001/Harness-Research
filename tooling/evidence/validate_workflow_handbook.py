#!/usr/bin/env python3
"""Validate workflow handbook source pages and reference metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
ROOT = Path("workflow_handbook")
NAV_CONFIG = ROOT / "config" / "navigation.json"
REFERENCE_INDEX = Path("docs/_views/workflow_handbook_reference_index.json")
ROOT_ENTRYPOINTS = {
    "Workflow_Operator_Handbook.md",
    "Workflow_Stage_Cards.md",
}
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
HEADING_RE = re.compile(r"^#{2,6}\s+(.+?)\s*$")
WIKI_REF_RE = re.compile(r"\[\[([A-Za-z][A-Za-z0-9_-]*:[^\]|]+)(?:\|[^\]]+)?\]\]")
VALID_PREFIXES = {"stage", "skill", "artifact", "term", "source", "page"}

REQUIRED_HEADINGS = {
    "overview": ["Purpose", "Mental Model", "Start Here", "Related Pages"],
    "concept": ["Purpose", "Model", "Boundaries", "Common Confusions", "Related Pages"],
    "how_to": [
        "Goal",
        "Prerequisites",
        "Steps",
        "Expected Outputs",
        "Gates",
        "Troubleshooting",
    ],
    "reference": [
        "Source Of Truth",
        "Fields Or Paths",
        "Validation",
        "Related References",
    ],
    "playbook": ["Scenario", "Decision Inputs", "Procedure", "Gate Ledger", "Recovery"],
    "stage": [
        "Purpose",
        "Inputs",
        "Outputs",
        "Required Reads",
        "Gates",
        "Exit Condition",
    ],
    "skill": [
        "Purpose",
        "Triggers",
        "Can Write",
        "Must Read",
        "Must Prove",
        "Cannot Do",
    ],
    "artifact": [
        "Purpose",
        "Owner",
        "Source Or View",
        "Update Trigger",
        "Related References",
    ],
    "term": ["Definition", "Use When", "Do Not Confuse With", "Related Terms"],
    "maintenance": ["Scope", "Required Reads", "Change Steps", "Validation", "Handoff"],
    "plan": ["Purpose", "Scope", "Design", "Slices", "Validation", "Open Decisions"],
}


@dataclass(frozen=True)
class HandbookPage:
    path: Path
    relative_path: Path
    metadata: dict[str, Any] | None
    body: str


def rel(path: Path, workspace_root: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def load_schema(name: str) -> dict[str, Any]:
    return load_json(SCHEMA_DIR / name)


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


def parse_frontmatter(path: Path, workspace_root: Path) -> HandbookPage:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    relative = path.relative_to(workspace_root)
    if not match:
        return HandbookPage(path, relative, None, text)
    raw_metadata = match.group(1)
    loaded = yaml.safe_load(raw_metadata) if raw_metadata.strip() else {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{rel(path, workspace_root)} frontmatter must be an object")
    return HandbookPage(path, relative, loaded, text[match.end() :])


def discover_pages(workspace_root: Path) -> list[HandbookPage]:
    root = workspace_root / ROOT
    if not root.exists():
        raise ValueError(f"missing directory: {ROOT}")
    return [
        parse_frontmatter(path, workspace_root) for path in sorted(root.rglob("*.md"))
    ]


def validate_root_entrypoints(pages: list[HandbookPage]) -> list[str]:
    errors: list[str] = []
    for page in pages:
        if (
            page.relative_path.parent == ROOT
            and page.relative_path.name not in ROOT_ENTRYPOINTS
        ):
            allowed = ", ".join(sorted(ROOT_ENTRYPOINTS))
            errors.append(
                f"{page.relative_path.as_posix()}: "
                f"root handbook Markdown must be one of {allowed}"
            )
    return errors


def should_require_frontmatter(page: HandbookPage) -> bool:
    parts = page.relative_path.parts
    if len(parts) < 2:
        return False
    return parts[1] in {"pages", "stages", "skills"}


def discovered_headings(markdown: str) -> set[str]:
    return {
        match.group(1).strip()
        for line in markdown.splitlines()
        if (match := HEADING_RE.match(line))
    }


def validate_page_metadata(page: HandbookPage) -> list[str]:
    errors: list[str] = []
    label = page.relative_path.as_posix()
    if page.metadata is None:
        if should_require_frontmatter(page):
            return [f"{label}: missing required frontmatter"]
        return []

    errors.extend(
        validate_json_schema(
            label,
            page.metadata,
            "workflow_handbook_page.schema.json",
        )
    )
    source_path = page.metadata.get("source_path")
    if source_path != label:
        errors.append(f"{label}: source_path must match file path")
    kind = page.metadata.get("kind")
    if isinstance(kind, str) and kind in REQUIRED_HEADINGS:
        found = discovered_headings(page.body)
        for heading in REQUIRED_HEADINGS[kind]:
            if heading not in found:
                errors.append(f"{label}: missing required heading ## {heading}")
    return errors


def normalize_ref(raw_ref: str) -> str:
    return raw_ref.split("|", 1)[0].strip()


def extract_markers(page: HandbookPage) -> list[tuple[int, str, str]]:
    links: list[tuple[int, str, str]] = []
    in_fence = False
    for line_number, line in enumerate(page.body.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        visible_line = re.sub(r"`[^`]*`", "", line)
        for match in WIKI_REF_RE.finditer(visible_line):
            marker = match.group(0)
            ref = normalize_ref(match.group(1))
            links.append((line_number, marker, ref))
    return links


def validate_marker_syntax(pages: list[HandbookPage]) -> list[str]:
    errors: list[str] = []
    for page in pages:
        for line_number, marker, ref in extract_markers(page):
            prefix = ref.split(":", 1)[0]
            if prefix not in VALID_PREFIXES:
                location = f"{page.relative_path.as_posix()}:{line_number}"
                errors.append(
                    f"{location}: unsupported reference {marker}"
                )
    return errors


def iter_nav_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for item in items:
        flattened.append(item)
        children = item.get("children", [])
        if isinstance(children, list):
            flattened.extend(
                iter_nav_items([child for child in children if isinstance(child, dict)])
            )
    return flattened


def validate_navigation(workspace_root: Path, pages: list[HandbookPage]) -> list[str]:
    path = workspace_root / NAV_CONFIG
    if not path.exists():
        return []
    try:
        data = load_json(path)
    except ValueError as exc:
        return [str(exc)]
    errors = validate_json_schema(
        NAV_CONFIG.as_posix(),
        data,
        "workflow_handbook_nav.schema.json",
    )
    seen_page_ids: set[str] = set()
    nav_source_paths: set[str] = set()
    for item in iter_nav_items(data.get("topbar", [])):
        page_id = item.get("page_id")
        source_path = item.get("source_path")
        if isinstance(page_id, str):
            if page_id in seen_page_ids:
                errors.append(f"{NAV_CONFIG}: duplicate topbar page_id {page_id}")
            seen_page_ids.add(page_id)
        if isinstance(source_path, str):
            nav_source_paths.add(source_path)
            if not (workspace_root / source_path).exists():
                errors.append(f"{NAV_CONFIG}: missing source_path {source_path}")

    seen_page_ids.clear()
    for section in data.get("sections", []):
        if not isinstance(section, dict):
            continue
        for item in iter_nav_items(section.get("items", [])):
            page_id = item.get("page_id")
            source_path = item.get("source_path")
            if isinstance(page_id, str):
                if page_id in seen_page_ids:
                    errors.append(f"{NAV_CONFIG}: duplicate page_id {page_id}")
                seen_page_ids.add(page_id)
            if isinstance(source_path, str):
                nav_source_paths.add(source_path)
                if not (workspace_root / source_path).exists():
                    errors.append(f"{NAV_CONFIG}: missing source_path {source_path}")

    for page in pages:
        if page.metadata is None:
            continue
        html = page.metadata.get("html", {})
        if isinstance(html, dict) and html.get("render") is True:
            source_path = page.relative_path.as_posix()
            if source_path not in nav_source_paths:
                errors.append(
                    f"{source_path}: html.render page is not present in navigation"
                )
    return errors


def validate_reference_index(
    workspace_root: Path, pages: list[HandbookPage]
) -> list[str]:
    path = workspace_root / REFERENCE_INDEX
    if not path.exists():
        return []
    try:
        data = load_json(path)
    except ValueError as exc:
        return [str(exc)]
    errors = validate_json_schema(
        REFERENCE_INDEX.as_posix(),
        data,
        "workflow_handbook_reference_index.schema.json",
    )
    entries = data.get("entries", {})
    links_by_doc = data.get("links_by_doc", {})
    if not isinstance(entries, dict) or not isinstance(links_by_doc, dict):
        return errors

    for page in pages:
        source_path = page.relative_path.as_posix()
        marker_refs = [ref for _, _, ref in extract_markers(page)]
        indexed_refs = {
            link.get("ref")
            for link in links_by_doc.get(source_path, [])
            if isinstance(link, dict)
        }
        for ref in marker_refs:
            if ref not in indexed_refs:
                errors.append(f"{source_path}: marker {ref} missing from links_by_doc")
            if ref not in entries:
                errors.append(f"{source_path}: unresolved reference {ref}")

    for page in pages:
        if not page.metadata:
            continue
        for ref in page.metadata.get("references", []):
            if ref not in entries:
                errors.append(
                    f"{page.relative_path.as_posix()}: references[] missing {ref}"
                )

    for doc, links in links_by_doc.items():
        if not isinstance(links, list):
            continue
        for link in links:
            if isinstance(link, dict) and link.get("status") != "resolved":
                errors.append(f"{doc}: unresolved reference {link.get('ref')}")
    return errors


def validate_workflow_handbook(workspace_root: Path) -> list[str]:
    pages = discover_pages(workspace_root)
    errors: list[str] = []
    errors.extend(validate_root_entrypoints(pages))
    for page in pages:
        try:
            errors.extend(validate_page_metadata(page))
        except ValueError as exc:
            errors.append(str(exc))
    errors.extend(validate_marker_syntax(pages))
    errors.extend(validate_navigation(workspace_root, pages))
    errors.extend(validate_reference_index(workspace_root, pages))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate workflow_handbook source pages and HTML metadata."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    try:
        errors = validate_workflow_handbook(args.workspace_root.resolve())
    except ValueError as exc:
        errors = [str(exc)]

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("PASS workflow_handbook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
