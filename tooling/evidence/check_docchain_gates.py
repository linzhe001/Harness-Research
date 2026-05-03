#!/usr/bin/env python3
"""Check evidence-chain coverage for current project documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_docchain  # noqa: E402


TARGET_DIRS = (
    "docs/10_contract",
    "docs/20_facts",
    "docs/35_protocol",
)
VALID_STATUSES = {"missing", "draft", "approved", "superseded"}
EMPTY_VALUES = {"", "n/a", "na", "none", "null", "-"}
STRICT_CLEAN_PREFIXES = ("docs/10_contract/",)
PATCH_REQUIRED_PREFIXES = ("docs/20_facts/", "docs/40_iterations/")
SUPPORTING_RELATIONS = {"supports", "partially_supports"}
STRONG_CONFIDENCE = {"medium", "high"}


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def normalize_path(value: str | None, workspace_root: Path) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return relpath(path, workspace_root)
    return path.as_posix().removeprefix("./")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def read_status(text: str) -> str:
    for line in text.splitlines()[:24]:
        if line.lower().startswith("status:"):
            status = line.split(":", 1)[1].strip().lower()
            return status if status in VALID_STATUSES else "draft"
    return "draft"


def clean_header_value(value: str) -> str | None:
    value = value.strip()
    markdown_link = re.search(r"\[[^\]]+\]\(([^)]+)\)", value)
    if markdown_link:
        value = markdown_link.group(1).strip()
    elif "`" in value:
        parts = value.split("`")
        if len(parts) >= 3:
            value = parts[1].strip()
    else:
        value = value.split()[0] if value.split() else ""
    value = value.strip().strip("'\"")
    if value.lower() in EMPTY_VALUES:
        return None
    return value


def header_value(text: str, label: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", re.IGNORECASE)
    for line in text.splitlines()[:48]:
        match = pattern.match(line)
        if match:
            return clean_header_value(match.group(1))
    return None


def target_docs(workspace_root: Path, docs: list[Path] | None = None, target_dirs: tuple[str, ...] = TARGET_DIRS) -> list[Path]:
    selected: set[Path] = set()
    if docs:
        for doc in docs:
            selected.add((workspace_root / doc).resolve() if not doc.is_absolute() else doc.resolve())
    for relative in target_dirs:
        directory = workspace_root / relative
        if not directory.exists():
            continue
        selected.update(path.resolve() for path in directory.rglob("*.md") if path.is_file())
    return sorted(selected)


def add_check(checks: list[dict[str, Any]], name: str, doc_path: str | None, ok: bool, severity: str, detail: str) -> None:
    checks.append(
        {
            "name": name,
            "doc_path": doc_path,
            "ok": ok,
            "severity": severity,
            "detail": detail,
        }
    )


def load_json(path: Path) -> dict[str, Any]:
    return validate_docchain.load_json(path)


def resolve_workspace_path(workspace_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else workspace_root / path


def check_source_manifest_hash(manifest: dict[str, Any], doc_rel: str, doc_path: Path, workspace_root: Path) -> str | None:
    read_set = manifest.get("read_set", [])
    if not isinstance(read_set, list):
        return "source_manifest.read_set is not a list"
    for entry in read_set:
        if not isinstance(entry, dict):
            continue
        if normalize_path(str(entry.get("path", "")), workspace_root) == doc_rel or entry.get("path") == doc_rel:
            current_hash = sha256_file(doc_path)
            recorded_hash = entry.get("hash")
            if recorded_hash != current_hash:
                return f"Markdown hash changed after compilation: recorded {recorded_hash}, current {current_hash}."
            return None
    return "source_manifest.read_set does not include the current Markdown document"


def check_hash(path: Path, expected_hash: str | None) -> str | None:
    if not expected_hash:
        return "hash is missing"
    if not path.exists():
        return f"file does not exist: {path}"
    current_hash = sha256_file(path)
    if current_hash != expected_hash:
        return f"hash mismatch: recorded {expected_hash}, current {current_hash}"
    return None


def check_git_context(
    checks: list[dict[str, Any]],
    workspace_root: Path,
    doc_rel: str,
    chain: dict[str, Any],
) -> None:
    git = chain.get("git")
    if not isinstance(git, dict):
        add_check(checks, "git_context_recorded", doc_rel, False, "error", "Docchain git context is missing or invalid.")
        return

    if not git.get("commit"):
        add_check(checks, "git_commit_recorded", doc_rel, True, "warn", "Git commit is unavailable; clean-commit policy cannot be fully checked.")
    else:
        add_check(checks, "git_commit_recorded", doc_rel, True, "info", "Git commit is recorded.")

    if not git.get("is_dirty"):
        add_check(checks, "git_source_clean", doc_rel, True, "info", "Source git context was clean when compiled.")
        return

    if doc_rel.startswith(STRICT_CLEAN_PREFIXES):
        add_check(
            checks,
            "git_source_clean_required",
            doc_rel,
            False,
            "error",
            "Contract docs require a clean source commit before compilation.",
        )
        return

    if doc_rel.startswith(PATCH_REQUIRED_PREFIXES):
        diff_value = git.get("diff_path")
        diff_rel = normalize_path(diff_value, workspace_root) if isinstance(diff_value, str) else None
        diff_hash = git.get("diff_hash") if isinstance(git.get("diff_hash"), str) else None
        if not diff_rel:
            add_check(checks, "git_dirty_patch_recorded", doc_rel, False, "error", "Dirty source context requires git.diff_path.")
            return
        diff_path = resolve_workspace_path(workspace_root, diff_rel)
        hash_error = check_hash(diff_path, diff_hash)
        if hash_error:
            add_check(checks, "git_dirty_patch_hash", doc_rel, False, "error", hash_error)
        else:
            add_check(checks, "git_dirty_patch_hash", doc_rel, True, "info", "Dirty source patch is preserved and hash matches.")
        snapshot_error = check_untracked_snapshots(workspace_root, git)
        if snapshot_error:
            add_check(checks, "git_untracked_snapshots", doc_rel, False, "error", snapshot_error)
        else:
            add_check(checks, "git_untracked_snapshots", doc_rel, True, "info", "Untracked source snapshots are preserved when present.")
        return

    add_check(checks, "git_source_dirty", doc_rel, True, "warn", "Source git context was dirty when compiled.")


def check_untracked_snapshots(workspace_root: Path, git: dict[str, Any]) -> str | None:
    status_summary = str(git.get("status_summary", ""))
    snapshots = git.get("untracked_snapshots", [])
    if "?? " not in status_summary and not snapshots:
        return None
    if not isinstance(snapshots, list) or not snapshots:
        return "Dirty source context includes untracked files but git.untracked_snapshots is empty."
    for entry in snapshots:
        if not isinstance(entry, dict):
            return "git.untracked_snapshots contains a non-object entry."
        source_path = entry.get("path")
        snapshot_value = entry.get("snapshot_path")
        expected_hash = entry.get("hash")
        if not all(isinstance(value, str) and value for value in [source_path, snapshot_value, expected_hash]):
            return "git.untracked_snapshots entries require path, snapshot_path, and hash."
        snapshot_rel = normalize_path(snapshot_value, workspace_root)
        if not snapshot_rel:
            return f"Invalid untracked snapshot path for {source_path}."
        hash_error = check_hash(resolve_workspace_path(workspace_root, snapshot_rel), expected_hash)
        if hash_error:
            return f"Untracked snapshot for {source_path}: {hash_error}."
    return None


def check_contract_evidence_strength(
    checks: list[dict[str, Any]],
    doc_rel: str,
    chain: dict[str, Any],
) -> None:
    if not doc_rel.startswith("docs/10_contract/"):
        return
    facts = chain.get("facts", [])
    evidence = chain.get("evidence", [])
    if not isinstance(facts, list) or not facts:
        add_check(checks, "contract_facts_present", doc_rel, False, "error", "Contract docs require explicit fact markers in the evidence chain.")
        return
    if not isinstance(evidence, list):
        add_check(checks, "contract_evidence_present", doc_rel, False, "error", "Contract evidence must be a list.")
        return

    non_markdown_sources = [
        item
        for item in evidence
        if isinstance(item, dict) and item.get("kind") != "markdown" and item.get("path") != doc_rel
    ]
    if not non_markdown_sources:
        add_check(checks, "contract_non_markdown_source", doc_rel, False, "error", "Contract docs require at least one non-Markdown source artifact.")
    else:
        add_check(checks, "contract_non_markdown_source", doc_rel, True, "info", "Contract doc has a non-Markdown source artifact.")

    strong_facts = [
        item
        for item in facts
        if isinstance(item, dict) and str(item.get("confidence", "")).lower() in STRONG_CONFIDENCE
    ]
    if not strong_facts:
        add_check(checks, "contract_fact_confidence", doc_rel, False, "error", "Contract facts cannot all be low-confidence.")
    else:
        add_check(checks, "contract_fact_confidence", doc_rel, True, "info", "Contract doc has medium/high-confidence facts.")

    supporting_evidence = [
        item
        for item in evidence
        if isinstance(item, dict) and item.get("support_relation") in SUPPORTING_RELATIONS and item.get("supports")
    ]
    if not supporting_evidence:
        add_check(checks, "contract_support_relation", doc_rel, False, "error", "Contract evidence must include supports/partially_supports relations, not only context_only.")
    else:
        add_check(checks, "contract_support_relation", doc_rel, True, "info", "Contract evidence includes explicit support relations.")


def validate_chain_dir(chain_dir: Path) -> list[str]:
    errors: list[str] = []
    try:
        errors.extend(validate_docchain.validate_evidence_chain(chain_dir / "evidence_chain.json"))
        errors.extend(validate_docchain.validate_source_manifest(chain_dir / "source_manifest.json"))
        errors.extend(validate_docchain.validate_doc_audit(chain_dir / "doc_audit.json"))
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def check_doc(
    workspace_root: Path,
    doc_path: Path,
    *,
    allow_missing_draft: bool,
    allow_draft_audit: bool,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    doc_rel = relpath(doc_path, workspace_root)
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    status = read_status(text)
    chain_header = header_value(text, "Evidence chain")
    audit_header = header_value(text, "Evidence audit")

    if not chain_header:
        severity = "warn" if allow_missing_draft and status == "draft" else "error"
        add_check(
            checks,
            "evidence_chain_header",
            doc_rel,
            severity != "error",
            severity,
            "Missing Evidence chain header, or it is N/A.",
        )
        return checks

    chain_rel = normalize_path(chain_header, workspace_root)
    assert chain_rel is not None
    chain_path = resolve_workspace_path(workspace_root, chain_rel)
    if chain_path.name != "evidence_chain.json":
        add_check(checks, "evidence_chain_filename", doc_rel, False, "error", f"Expected evidence_chain.json, got {chain_rel}.")
        return checks
    if not chain_path.exists():
        add_check(checks, "evidence_chain_exists", doc_rel, False, "error", f"Missing evidence chain: {chain_rel}.")
        return checks

    chain_dir = chain_path.parent
    structural_errors = validate_chain_dir(chain_dir)
    if structural_errors:
        add_check(checks, "docchain_structure", doc_rel, False, "error", "; ".join(structural_errors))
        return checks
    add_check(checks, "docchain_structure", doc_rel, True, "info", f"Valid docchain directory: {relpath(chain_dir, workspace_root)}.")

    chain = load_json(chain_dir / "evidence_chain.json")
    check_git_context(checks, workspace_root, doc_rel, chain)
    chain_doc = chain.get("doc", {}) if isinstance(chain.get("doc"), dict) else {}
    chain_links = chain.get("doc_links", {}) if isinstance(chain.get("doc_links"), dict) else {}
    chain_doc_path = normalize_path(str(chain_doc.get("path", "")), workspace_root)
    chain_markdown_path = normalize_path(str(chain_links.get("markdown_path", "")), workspace_root)
    if chain_doc_path != doc_rel or chain_markdown_path != doc_rel:
        add_check(
            checks,
            "docchain_doc_path",
            doc_rel,
            False,
            "error",
            f"Docchain points to doc.path={chain_doc_path!r}, markdown_path={chain_markdown_path!r}; expected {doc_rel!r}.",
        )
    else:
        add_check(checks, "docchain_doc_path", doc_rel, True, "info", "Docchain points back to this Markdown document.")

    audit_rel = normalize_path(audit_header, workspace_root) if audit_header else normalize_path(str(chain_links.get("audit_path", "")), workspace_root)
    if not audit_rel:
        add_check(checks, "doc_audit_reference", doc_rel, False, "error", "No Evidence audit header or doc_links.audit_path.")
        return checks
    audit_path = resolve_workspace_path(workspace_root, audit_rel)
    if not audit_path.exists():
        add_check(checks, "doc_audit_exists", doc_rel, False, "error", f"Missing doc audit: {audit_rel}.")
        return checks

    audit = load_json(audit_path)
    audit_doc_path = normalize_path(str(audit.get("doc_path", "")), workspace_root)
    audit_chain_path = normalize_path(str(audit.get("evidence_chain_path", "")), workspace_root)
    if audit_doc_path != doc_rel or audit_chain_path != chain_rel:
        add_check(
            checks,
            "doc_audit_links",
            doc_rel,
            False,
            "error",
            f"Audit links doc_path={audit_doc_path!r}, evidence_chain_path={audit_chain_path!r}; expected {doc_rel!r} and {chain_rel!r}.",
        )
    else:
        add_check(checks, "doc_audit_links", doc_rel, True, "info", "Audit links match the Markdown document and evidence chain.")

    audit_result = audit.get("audit_result")
    if audit_result == "PASS":
        add_check(checks, "doc_audit_result", doc_rel, True, "info", "Audit result is PASS.")
    elif audit_result == "DRAFT_ONLY" and allow_draft_audit and status == "draft":
        add_check(checks, "doc_audit_result", doc_rel, True, "warn", "Audit result is DRAFT_ONLY and allowed for draft docs.")
    else:
        add_check(checks, "doc_audit_result", doc_rel, False, "error", f"Audit result is {audit_result!r}.")

    manifest_rel = normalize_path(str(chain_links.get("source_manifest_path", "")), workspace_root)
    if not manifest_rel:
        add_check(checks, "source_manifest_reference", doc_rel, False, "error", "Docchain lacks doc_links.source_manifest_path.")
        return checks
    manifest_path = resolve_workspace_path(workspace_root, manifest_rel)
    if not manifest_path.exists():
        add_check(checks, "source_manifest_exists", doc_rel, False, "error", f"Missing source manifest: {manifest_rel}.")
        return checks
    manifest = load_json(manifest_path)
    hash_error = check_source_manifest_hash(manifest, doc_rel, doc_path, workspace_root)
    if hash_error:
        add_check(checks, "source_manifest_doc_hash", doc_rel, False, "error", hash_error)
    else:
        add_check(checks, "source_manifest_doc_hash", doc_rel, True, "info", "Current Markdown hash matches source_manifest.read_set.")
    check_contract_evidence_strength(checks, doc_rel, chain)

    return checks


def gate_result(
    workspace_root: Path,
    *,
    docs: list[Path] | None = None,
    allow_missing_draft: bool = False,
    allow_draft_audit: bool = False,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    selected_docs = target_docs(workspace, docs)
    checks: list[dict[str, Any]] = []
    dynamic_dirs = [relative for relative in TARGET_DIRS if (workspace / relative).exists()]

    if not selected_docs:
        add_check(
            checks,
            "legacy_or_empty_docs",
            None,
            True,
            "info",
            "No dynamic current-doc directories or explicit docs found; docchain gate is not active.",
        )
    for doc in selected_docs:
        if not doc.exists():
            add_check(checks, "doc_exists", relpath(doc, workspace), False, "error", "Explicit doc does not exist.")
            continue
        checks.extend(
            check_doc(
                workspace,
                doc,
                allow_missing_draft=allow_missing_draft,
                allow_draft_audit=allow_draft_audit,
            )
        )

    errors = [check for check in checks if check["severity"] == "error" and not check["ok"]]
    warnings = [check for check in checks if check["severity"] == "warn"]
    return {
        "ok": not errors,
        "dynamic_docchain": bool(dynamic_dirs or selected_docs),
        "target_dirs": dynamic_dirs,
        "checked_doc_count": len(selected_docs),
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def print_text(result: dict[str, Any]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print(f"{status} docchain gates (checked_docs={result['checked_doc_count']})")
    for check in result["checks"]:
        marker = "OK" if check["ok"] else "NO"
        doc = f" {check['doc_path']}" if check.get("doc_path") else ""
        print(f"- [{marker}] {check['severity']}: {check['name']}{doc} - {check['detail']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Harness evidence docchain gates for current docs.")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--doc", type=Path, action="append", dest="docs", help="Additional or explicit Markdown doc to check.")
    parser.add_argument("--allow-missing-draft", action="store_true", help="Warn instead of fail when draft docs still have Evidence chain: N/A.")
    parser.add_argument("--allow-draft-audit", action="store_true", help="Allow DRAFT_ONLY audit results for draft docs.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = gate_result(
            args.workspace_root,
            docs=args.docs,
            allow_missing_draft=args.allow_missing_draft,
            allow_draft_audit=args.allow_draft_audit,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_text(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
