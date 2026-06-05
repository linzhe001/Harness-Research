#!/usr/bin/env python3
"""Build hover-preview references for the workflow handbook."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

SCHEMA_VERSION = "0.1"
SOURCE_INDEX_VERSION = "skill_contracts:0.1"
OUTPUT_PATH = Path("docs/_views/workflow_handbook_reference_index.json")
SCHEMA_PATH = Path("schemas/workflow_handbook_reference_index.schema.json")
SKILL_CONTRACTS = Path("schemas/skill_contracts.json")
NAV_CONFIG = Path("workflow_handbook/config/navigation.json")
WIKI_REF_RE = re.compile(r"\[\[([A-Za-z][A-Za-z0-9_-]*:[^\]|]+)(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
TERM_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|")
REFERENCE_ID_RE = re.compile(
    r"^(stage|skill|artifact|term|source|page):[A-Za-z0-9_./:# -]+$"
)
STAGE_BY_SKILL = {
    "init-project": ("WF0", "wf0_init", "WF0 Init"),
    "survey-idea": ("WF1", "wf1_survey_idea", "WF1 Survey Idea"),
    "idea-debate": ("WF2", "wf2_idea_debate", "WF2 Idea Debate"),
    "refine-idea": ("WF3", "wf3_refine_idea", "WF3 Refine Idea"),
    "data-prep": ("WF4", "wf4_data_prep", "WF4 Data Prep"),
    "baseline-repro": ("WF5", "wf5_baseline_repro", "WF5 Baseline Repro"),
    "refine-arch": ("WF6", "wf6_refine_arch", "WF6 Refine Arch"),
    "build-plan": ("WF7", "wf7_build_plan", "WF7 Build Plan"),
    "code-expert": ("WF8", "wf8_code_expert", "WF8 Code Expert"),
    "validate-run": ("WF9", "wf9_validate_run", "WF9 Validate Run"),
    "iterate": ("WF10", "wf10_iterate", "WF10 Iterate"),
    "final-exp": ("WF11", "wf11_final_exp", "WF11 Final Exp"),
    "release": ("WF12", "wf12_release", "WF12 Release"),
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


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


def validate_schema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    rendered: list[str] = []
    for error in errors:
        location = "workflow_handbook_reference_index"
        for part in error.path:
            if isinstance(part, int):
                location += f"[{part}]"
            else:
                location += f".{part}"
        rendered.append(f"{location}: {error.message}")
    return rendered


def preview(title: str, body: str, *, truncated: bool = False) -> dict[str, Any]:
    return {
        "title": title,
        "body": body,
        "format": "plain",
        "source_excerpt": None,
        "excerpt_hash": None,
        "truncated": truncated,
    }


def truncate(text: str, limit: int = 280) -> tuple[str, bool]:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized, False
    return normalized[: limit - 3].rstrip() + "...", True


def entry(
    *,
    ref: str,
    kind: str,
    title: str,
    summary: str,
    truth_status: str,
    owner: str,
    source_paths: list[dict[str, Any]],
    related_refs: list[str] | None = None,
    body: str | None = None,
) -> dict[str, Any]:
    body_text, truncated = truncate(body or summary)
    return {
        "ref": ref,
        "kind": kind,
        "title": title,
        "summary": summary,
        "truth_status": truth_status,
        "owner": owner,
        "source_paths": source_paths,
        "preview": preview(title, body_text, truncated=truncated),
        "related_refs": related_refs or [],
        "last_validated_by": "build_workflow_handbook_reference_index.py",
    }


def frontmatter_description(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return ""
    data = yaml.safe_load(match.group(1)) or {}
    if isinstance(data, dict) and isinstance(data.get("description"), str):
        return str(data["description"])
    return ""


def parse_page_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} frontmatter must be an object")
    return data, text[match.end() :]


def load_contracts(workspace_root: Path) -> list[dict[str, Any]]:
    data = load_json(workspace_root / SKILL_CONTRACTS)
    contracts = data.get("contracts")
    if not isinstance(contracts, list):
        raise ValueError(f"{SKILL_CONTRACTS} contracts must be a list")
    return [contract for contract in contracts if isinstance(contract, dict)]


def read_paths(contract: dict[str, Any]) -> list[str]:
    read_set = contract.get("required_read_set", {})
    paths: list[str] = []
    if not isinstance(read_set, dict):
        return paths
    for section in ("harness", "skill", "project_when_present", "project_optional"):
        values = read_set.get(section, [])
        if isinstance(values, list):
            paths.extend(str(value) for value in values)
    return list(dict.fromkeys(paths))


def write_paths(contract: dict[str, Any]) -> list[str]:
    scope = contract.get("write_scope", {})
    if not isinstance(scope, dict):
        return []
    values = scope.get("allowed_paths", [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def artifact_paths(contract: dict[str, Any]) -> list[str]:
    outputs = contract.get("artifact_outputs", [])
    paths: list[str] = []
    if not isinstance(outputs, list):
        return paths
    for output in outputs:
        if not isinstance(output, dict):
            continue
        values = output.get("paths", [])
        if isinstance(values, list):
            paths.extend(str(value) for value in values)
    return list(dict.fromkeys(paths))


def source_locator(
    path: str, role: str, *, anchor: str | None = None
) -> dict[str, Any]:
    return {"path": path, "anchor": anchor, "line": None, "role": role}


def add_skill_entries(
    workspace_root: Path,
    entries: dict[str, dict[str, Any]],
    contracts: list[dict[str, Any]],
) -> None:
    for contract in contracts:
        skill = str(contract.get("skill"))
        skill_path = workspace_root / ".agents" / "skills" / skill / "SKILL.md"
        summary = frontmatter_description(skill_path) or f"{skill} Skill Contract."
        writes = ", ".join(write_paths(contract)[:5]) or "no declared writes"
        actions = ", ".join(
            str(value) for value in contract.get("required_actions", [])[:5]
        )
        body = (
            f"Reads {len(read_paths(contract))} declared paths; "
            f"writes {writes}; must prove {actions}."
        )
        owner = "docs-site" if skill == "docs-site" else "skill"
        entries[f"skill:{skill}"] = entry(
            ref=f"skill:{skill}",
            kind="skill",
            title=skill,
            summary=summary,
            truth_status="source_of_truth",
            owner=owner,
            source_paths=[
                source_locator(
                    "schemas/skill_contracts.json", "skill_contract", anchor=skill
                ),
                source_locator(f".agents/skills/{skill}/SKILL.md", "skill_source"),
            ],
            related_refs=["term:Gate Evidence"],
            body=body,
        )
        entries[f"source:schemas/skill_contracts.json#{skill}"] = entry(
            ref=f"source:schemas/skill_contracts.json#{skill}",
            kind="source",
            title=f"Skill Contract: {skill}",
            summary=f"Machine-readable Skill Contract entry for {skill}.",
            truth_status="source_of_truth",
            owner="maintainer",
            source_paths=[
                source_locator(
                    "schemas/skill_contracts.json", "skill_contract", anchor=skill
                )
            ],
            related_refs=[f"skill:{skill}"],
        )


def add_stage_entries(
    entries: dict[str, dict[str, Any]],
    contracts: list[dict[str, Any]],
) -> None:
    by_skill = {str(contract.get("skill")): contract for contract in contracts}
    for skill, (stage_id, page_id, title) in STAGE_BY_SKILL.items():
        contract = by_skill.get(skill)
        if not contract:
            continue
        gates = ", ".join(
            str(value) for value in contract.get("gate_ledger_required_when", [])[:5]
        )
        summary = f"{title} runs through the {skill} Skill Contract."
        entries[f"stage:{stage_id}"] = entry(
            ref=f"stage:{stage_id}",
            kind="stage",
            title=title,
            summary=summary,
            truth_status="source_of_truth",
            owner="skill",
            source_paths=[
                source_locator(
                    "schemas/skill_contracts.json", "skill_contract", anchor=skill
                ),
                source_locator(
                    f"workflow_handbook/stages/{page_id}.md", "handbook_page"
                ),
            ],
            related_refs=[f"skill:{skill}", "term:Gate Evidence"],
            body=f"Primary skill: {skill}. Gate conditions: {gates}.",
        )


def normalize_owner(owner: str) -> str:
    mapping = {
        "docs-site": "docs-site",
        "evidence-tooling": "evidence_tooling",
        "auto-iterate-controller": "auto_iterate_controller",
        "hook-runtime": "hook_runtime",
        "orchestrator": "orchestrator",
    }
    return mapping.get(owner, "skill")


def artifact_truth_status(path: str) -> str:
    if path.startswith("docs/_site/") or path.startswith("docs/_views/"):
        return "generated_view"
    if (
        path.startswith(".evidence/")
        or path.startswith(".auto_iterate/")
        or path.startswith(".workflow_supervisor/")
    ):
        return "runtime_state"
    return "source_of_truth"


def add_artifact_entries(
    entries: dict[str, dict[str, Any]],
    contracts: list[dict[str, Any]],
) -> None:
    artifacts: dict[str, dict[str, Any]] = {
        "docs/_views/workflow_handbook_reference_index.json": {
            "owner": "docs-site",
            "source": "tooling/evidence/build_workflow_handbook_reference_index.py",
            "summary": (
                "Generated framework reference preview index for workflow "
                "handbook hover cards."
            ),
        },
        "docs/_site/workflow_handbook": {
            "owner": "docs-site",
            "source": "tooling/evidence/build_docs_site.py",
            "summary": "Generated HTML view for the workflow handbook.",
        },
        ".evidence/index.json": {
            "owner": "evidence-tooling",
            "source": "tooling/evidence/compile_doc.py",
            "summary": "Project Evidence Chain index for claim-bearing current docs.",
        },
    }
    for contract in contracts:
        skill = str(contract.get("skill"))
        outputs = contract.get("artifact_outputs", [])
        if not isinstance(outputs, list):
            continue
        for output in outputs:
            if not isinstance(output, dict):
                continue
            for path in output.get("paths", []):
                value = str(path)
                if not REFERENCE_ID_RE.match(f"artifact:{value}"):
                    continue
                artifacts.setdefault(
                    value,
                    {
                        "owner": str(output.get("owner", "skill")),
                        "source": "schemas/skill_contracts.json",
                        "source_anchor": skill,
                        "summary": str(
                            output.get("notes") or f"{value} is declared by {skill}."
                        ),
                    },
                )
    for path, info in sorted(artifacts.items()):
        ref = f"artifact:{path}"
        if not REFERENCE_ID_RE.match(ref):
            continue
        source = str(info.get("source", "schemas/skill_contracts.json"))
        source_role = "tooling" if source.startswith("tooling/") else "skill_contract"
        entries[ref] = entry(
            ref=ref,
            kind="artifact",
            title=path,
            summary=str(info["summary"]),
            truth_status=artifact_truth_status(path),
            owner=normalize_owner(str(info["owner"])),
            source_paths=[
                source_locator(source, source_role, anchor=info.get("source_anchor"))
            ],
            related_refs=[],
        )


def add_term_entries(workspace_root: Path, entries: dict[str, dict[str, Any]]) -> None:
    source = Path(".agents/references/ubiquitous-language.md")
    path = workspace_root / source
    if not path.exists():
        return
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = TERM_ROW_RE.match(line)
        if not match:
            continue
        term = match.group(1).strip()
        definition = re.sub(r"`([^`]+)`", r"\1", match.group(2).strip())
        ref = f"term:{term}"
        if not REFERENCE_ID_RE.match(ref):
            continue
        entries[ref] = entry(
            ref=ref,
            kind="term",
            title=term,
            summary=definition,
            truth_status="source_of_truth",
            owner="maintainer",
            source_paths=[
                {
                    "path": source.as_posix(),
                    "anchor": term,
                    "line": line_number,
                    "role": "shared_rule",
                }
            ],
            related_refs=[],
        )


def html_path_for_source(source_path: str) -> str:
    relative = Path(source_path).relative_to("workflow_handbook").with_suffix(".html")
    return (Path("docs/_site/workflow_handbook") / relative).as_posix()


def add_page_entry(
    entries: dict[str, dict[str, Any]],
    *,
    page_id: str,
    title: str,
    source_path: str,
    summary: str,
    kind: str = "page",
) -> None:
    entries[f"page:{page_id}"] = entry(
        ref=f"page:{page_id}",
        kind="page",
        title=title,
        summary=summary,
        truth_status="source_of_truth",
        owner="maintainer",
        source_paths=[source_locator(source_path, "handbook_page")],
        related_refs=[],
        body=f"{title}: {summary}",
    )


def nav_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for item in items:
        flattened.append(item)
        children = item.get("children", [])
        if isinstance(children, list):
            flattened.extend(
                nav_items([child for child in children if isinstance(child, dict)])
            )
    return flattened


def add_page_entries(workspace_root: Path, entries: dict[str, dict[str, Any]]) -> None:
    for path in sorted((workspace_root / "workflow_handbook").rglob("*.md")):
        metadata, _ = parse_page_frontmatter(path)
        source_path = path.relative_to(workspace_root).as_posix()
        if metadata and isinstance(metadata.get("page_id"), str):
            add_page_entry(
                entries,
                page_id=str(metadata["page_id"]),
                title=str(metadata.get("title") or path.stem),
                source_path=source_path,
                summary=str(metadata.get("summary") or "Workflow handbook page."),
                kind=str(metadata.get("kind") or "page"),
            )
    nav_path = workspace_root / NAV_CONFIG
    if not nav_path.exists():
        return
    nav = load_json(nav_path)
    for section in nav.get("sections", []):
        if not isinstance(section, dict):
            continue
        for item in nav_items(section.get("items", [])):
            if not isinstance(item, dict):
                continue
            page_id = item.get("page_id")
            source_path = item.get("source_path")
            label = item.get("label")
            if not all(
                isinstance(value, str) for value in [page_id, source_path, label]
            ):
                continue
            ref = f"page:{page_id}"
            if ref not in entries:
                add_page_entry(
                    entries,
                    page_id=str(page_id),
                    title=str(label),
                    source_path=str(source_path),
                    summary=f"Navigation entry for {label}.",
                )


def add_source_entries(entries: dict[str, dict[str, Any]]) -> None:
    sources = [
        (
            "source:schemas/skill_contracts.json",
            "schemas/skill_contracts.json",
            "schema",
        ),
        (
            "source:tooling/evidence/build_docs_site.py",
            "tooling/evidence/build_docs_site.py",
            "tooling",
        ),
        (
            "source:tooling/evidence/build_workflow_handbook_reference_index.py",
            "tooling/evidence/build_workflow_handbook_reference_index.py",
            "tooling",
        ),
        (
            "source:tooling/evidence/validate_workflow_handbook.py",
            "tooling/evidence/validate_workflow_handbook.py",
            "tooling",
        ),
    ]
    for ref, path, role in sources:
        entries.setdefault(
            ref,
            entry(
                ref=ref,
                kind="source",
                title=path,
                summary=f"Framework source file {path}.",
                truth_status="source_of_truth",
                owner="maintainer",
                source_paths=[source_locator(path, role)],
                related_refs=[],
            ),
        )


def target_html_for_ref(ref: str) -> str | None:
    prefix, value = ref.split(":", 1)
    if prefix == "skill":
        return f"docs/_site/workflow_handbook/skills/{value}.html"
    if prefix == "stage":
        for stage_id, page_id, _title in STAGE_BY_SKILL.values():
            if stage_id == value:
                return f"docs/_site/workflow_handbook/stages/{page_id}.html"
    if prefix == "page":
        return None
    return None


def extract_links(
    workspace_root: Path,
    entries: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    links_by_doc: dict[str, list[dict[str, Any]]] = {}
    page_targets = {
        ref: html_path_for_source(item["source_paths"][0]["path"])
        for ref, item in entries.items()
        if ref.startswith("page:")
        and item.get("source_paths")
        and str(item["source_paths"][0]["path"]).startswith("workflow_handbook/")
    }
    for path in sorted((workspace_root / "workflow_handbook").rglob("*.md")):
        source_path = path.relative_to(workspace_root).as_posix()
        links: list[dict[str, Any]] = []
        in_fence = False
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            visible_line = re.sub(r"`[^`]*`", "", line)
            for match in WIKI_REF_RE.finditer(visible_line):
                marker = match.group(0)
                ref = match.group(1).split("|", 1)[0].strip()
                target_html = (
                    page_targets.get(ref)
                    if ref.startswith("page:")
                    else target_html_for_ref(ref)
                )
                links.append(
                    {
                        "ref": ref,
                        "source_path": source_path,
                        "marker": marker,
                        "line": line_number,
                        "status": "resolved" if ref in entries else "missing",
                        "target_html": target_html,
                    }
                )
        if links:
            links_by_doc[source_path] = links
    return links_by_doc


def build_reference_index(workspace_root: Path) -> dict[str, Any]:
    contracts = load_contracts(workspace_root)
    entries: dict[str, dict[str, Any]] = {}
    add_skill_entries(workspace_root, entries, contracts)
    add_stage_entries(entries, contracts)
    add_artifact_entries(entries, contracts)
    add_term_entries(workspace_root, entries)
    add_page_entries(workspace_root, entries)
    add_source_entries(entries)
    index = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "source_index_version": SOURCE_INDEX_VERSION,
        "source_roots": [
            "schemas/skill_contracts.json",
            ".agents/skills",
            ".agents/references",
            "workflow_handbook",
        ],
        "entries": dict(sorted(entries.items())),
        "links_by_doc": {},
    }
    index["links_by_doc"] = extract_links(workspace_root, index["entries"])
    return index


def validate_reference_index(workspace_root: Path, data: dict[str, Any]) -> list[str]:
    schema = load_json(workspace_root / SCHEMA_PATH)
    errors = validate_schema(data, schema)
    entries = data.get("entries", {})
    if isinstance(entries, dict):
        for ref in entries:
            if not REFERENCE_ID_RE.match(ref):
                errors.append(f"invalid reference id: {ref}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build workflow handbook framework reference preview index."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    workspace_root = args.workspace_root.resolve()
    try:
        data = build_reference_index(workspace_root)
        errors = validate_reference_index(workspace_root, data)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    if not args.dry_run:
        output = (
            args.output if args.output.is_absolute() else workspace_root / args.output
        )
        atomic_write_json(output, data)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"PASS {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
