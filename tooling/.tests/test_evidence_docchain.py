# ruff: noqa: E501
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALID_FIXTURE = (
    REPO_ROOT / "tooling" / ".tests" / "fixtures" / "evidence_docchain" / "valid"
)


def load_validator():
    path = REPO_ROOT / "tooling" / "evidence" / "validate_docchain.py"
    spec = importlib.util.spec_from_file_location("validate_docchain", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tool(name: str):
    path = REPO_ROOT / "tooling" / "evidence" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)


def test_schema_files_parse_as_json() -> None:
    for schema_path in [
        REPO_ROOT / "schemas" / "evidence_chain.schema.json",
        REPO_ROOT / "schemas" / "source_manifest.schema.json",
        REPO_ROOT / "schemas" / "doc_audit.schema.json",
        REPO_ROOT / "schemas" / "evidence_index.schema.json",
        REPO_ROOT / "schemas" / "review_packet.schema.json",
        REPO_ROOT / "schemas" / "approval_record.schema.json",
        REPO_ROOT / "schemas" / "project_state.schema.json",
        REPO_ROOT / "schemas" / "iteration_log.schema.json",
        REPO_ROOT / "schemas" / "project_map.schema.json",
        REPO_ROOT / "schemas" / "docs_site_manifest.schema.json",
        REPO_ROOT / "schemas" / "codebase_map_doc.schema.json",
        REPO_ROOT / "schemas" / "glossary_doc.schema.json",
        REPO_ROOT / "schemas" / "architecture_doc.schema.json",
        REPO_ROOT / "schemas" / "api_reference_doc.schema.json",
        REPO_ROOT / "schemas" / "runbook_doc.schema.json",
        REPO_ROOT / "schemas" / "implementation_roadmap_doc.schema.json",
        REPO_ROOT / "schemas" / "decision_log_doc.schema.json",
        REPO_ROOT / "schemas" / "validation_report_doc.schema.json",
        REPO_ROOT / "schemas" / "evidence_preview_index.schema.json",
    ]:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert data["type"] == "object"
        assert data["required"]


def test_valid_docchain_fixture_passes_validator() -> None:
    validator = load_validator()
    assert validator.main([str(VALID_FIXTURE)]) == 0


def test_missing_docchain_file_fails_validator(tmp_path: Path) -> None:
    validator = load_validator()
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert validator.main([str(empty_dir)]) == 1


def copy_valid_docchain(tmp_path: Path) -> Path:
    target = tmp_path / "chain"
    shutil.copytree(VALID_FIXTURE, target)
    return target


def test_validator_fails_fact_missing_claim(tmp_path: Path) -> None:
    validator = load_validator()
    chain_dir = copy_valid_docchain(tmp_path)
    chain_path = chain_dir / "evidence_chain.json"
    chain = json.loads(chain_path.read_text(encoding="utf-8"))
    chain["facts"][0].pop("claim")
    chain_path.write_text(json.dumps(chain, indent=2) + "\n", encoding="utf-8")

    errors = validator.validate_evidence_chain(chain_path)

    assert any("facts[0]: missing claim" in error for error in errors)
    assert validator.main([str(chain_dir)]) == 1


def test_validator_fails_evidence_missing_supports(tmp_path: Path) -> None:
    validator = load_validator()
    chain_dir = copy_valid_docchain(tmp_path)
    chain_path = chain_dir / "evidence_chain.json"
    chain = json.loads(chain_path.read_text(encoding="utf-8"))
    chain["evidence"][0].pop("supports")
    chain_path.write_text(json.dumps(chain, indent=2) + "\n", encoding="utf-8")

    errors = validator.validate_evidence_chain(chain_path)

    assert any("evidence[0]: missing supports" in error for error in errors)
    assert validator.main([str(chain_dir)]) == 1


def test_validator_fails_doc_audit_check_missing_result(tmp_path: Path) -> None:
    validator = load_validator()
    chain_dir = copy_valid_docchain(tmp_path)
    audit_path = chain_dir / "doc_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit["checks"][0].pop("result")
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    errors = validator.validate_doc_audit(audit_path)

    assert any("checks[0]: missing result" in error for error in errors)
    assert validator.main([str(chain_dir)]) == 1


def test_compile_doc_generates_valid_docchain(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    preview_builder = load_tool("build_evidence_preview_index")
    site_builder = load_tool("build_docs_site")
    validator = load_validator()

    doc = tmp_path / "docs" / "10_contract" / "Project_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Project Contract\n\nStatus: draft\n\n"
        "- The project scope is draft. [F:project.scope]\n"
        "- Open issue. [U:project.open]\n",
        encoding="utf-8",
    )
    source.write_text('{"project": "demo"}\n', encoding="utf-8")

    summary = compiler.compile_document(
        tmp_path,
        Path("docs/10_contract/Project_Contract.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    chain_dir = (
        tmp_path
        / ".evidence"
        / "chains"
        / "docs__10_contract__Project_Contract"
        / "test_build"
    )
    assert summary["ok"] is True
    assert summary["fact_count"] == 1
    assert summary["unresolved_count"] == 1
    assert validator.main([str(chain_dir)]) == 0
    assert (
        validator.validate_evidence_index(tmp_path / ".evidence" / "index.json") == []
    )

    chain = json.loads((chain_dir / "evidence_chain.json").read_text(encoding="utf-8"))
    doc_text = doc.read_text(encoding="utf-8")
    index = json.loads(
        (tmp_path / ".evidence" / "index.json").read_text(encoding="utf-8")
    )

    assert chain["facts"][0]["fact_id"] == "project.scope"
    assert chain["facts"][0]["support_edges"][0]["preview_ref"].endswith(":E001")
    assert (
        chain["evidence"][0]["locator"]["path"]
        == "docs/10_contract/Project_Contract.md"
    )
    assert "The project scope is draft" in chain["evidence"][0]["preview"]["excerpt"]
    assert chain["unresolved"][0]["question_id"] == "project.open"
    assert chain["doc_links"]["markdown_path"] == "docs/10_contract/Project_Contract.md"
    chain_link = (
        "Evidence chain: `.evidence/chains/"
        "docs__10_contract__Project_Contract/test_build/evidence_chain.json`"
    )
    assert chain_link in doc_text
    assert (
        index["docs"]["docs__10_contract__Project_Contract"]["latest_build_id"]
        == "test_build"
    )
    assert "project.scope" in index["facts_by_id"]
    assert (
        "docs__10_contract__Project_Contract:test_build:E001" in index["evidence_by_id"]
    )
    assert (
        index["markers_by_doc"]["docs/10_contract/Project_Contract.md"][0]["marker"]
        == "[F:project.scope]"
    )

    preview = preview_builder.build_preview_index(
        tmp_path,
        output_path=Path("docs/_views/evidence_preview_index.json"),
    )
    preview_path = tmp_path / "docs" / "_views" / "evidence_preview_index.json"

    assert preview["facts"]["project.scope"]["previews"]
    assert (
        "The project scope is draft"
        in preview["markers"]["F:project.scope"]["previews"][0]["excerpt"]
    )
    assert preview["markers"]["F:project.scope"]["target_path"] == "PROJECT_STATE.json"
    assert preview_path.exists()
    assert validator.validate_evidence_preview_index(preview_path) == []

    manifest = site_builder.build_docs_site(tmp_path)
    manifest_path = tmp_path / "docs" / "_site" / "manifest.json"
    html_path = tmp_path / "docs" / "_site" / "10_contract" / "Project_Contract.html"
    html_text = html_path.read_text(encoding="utf-8")

    assert manifest_path.exists()
    assert html_path.exists()
    assert manifest["pages"][0]["source_path"] == "docs/10_contract/Project_Contract.md"
    assert manifest["pages"][0]["preview_index_path"] == (
        "docs/_views/evidence_preview_index.json"
    )
    assert validator.validate_docs_site_manifest(manifest_path) == []
    assert 'data-marker="F:project.scope"' in html_text
    assert 'href="../../../PROJECT_STATE.json"' in html_text
    assert "The project scope is draft" in html_text

    stale_html = tmp_path / "docs" / "_site" / "stale.html"
    stale_html.write_text("stale", encoding="utf-8")
    site_builder.build_docs_site(tmp_path)
    assert not stale_html.exists()


def test_compile_doc_preserves_dirty_source_patch(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    init_git_repo(tmp_path)

    doc = tmp_path / "docs" / "20_facts" / "Execution_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Execution Contract\n\nStatus: draft\n\n- Env: demo. [F:env.demo]\n",
        encoding="utf-8",
    )
    source.write_text('{"project": "demo"}\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    source.write_text('{"project": "demo", "dirty": true}\n', encoding="utf-8")
    compiler.compile_document(
        tmp_path,
        Path("docs/20_facts/Execution_Contract.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    chain_dir = (
        tmp_path
        / ".evidence"
        / "chains"
        / "docs__20_facts__Execution_Contract"
        / "test_build"
    )
    chain = json.loads((chain_dir / "evidence_chain.json").read_text(encoding="utf-8"))

    assert chain["git"]["is_dirty"] is True
    assert (
        chain["git"]["diff_path"]
        == ".evidence/chains/docs__20_facts__Execution_Contract/test_build/patch.diff"
    )
    assert (chain_dir / "patch.diff").exists()


def test_compile_doc_preserves_untracked_source_snapshot(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    init_git_repo(tmp_path)

    doc = tmp_path / "docs" / "20_facts" / "Project_Facts.md"
    source = tmp_path / "local_source.json"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Project Facts\n\nStatus: draft\n\n- Local source exists. [F:local.source]\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    source.write_text('{"local": true}\n', encoding="utf-8")

    compiler.compile_document(
        tmp_path,
        Path("docs/20_facts/Project_Facts.md"),
        [Path("local_source.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    chain_dir = (
        tmp_path
        / ".evidence"
        / "chains"
        / "docs__20_facts__Project_Facts"
        / "test_build"
    )
    chain = json.loads((chain_dir / "evidence_chain.json").read_text(encoding="utf-8"))
    snapshots = chain["git"]["untracked_snapshots"]

    assert snapshots[0]["path"] == "local_source.json"
    snapshot_path = (
        ".evidence/chains/docs__20_facts__Project_Facts/test_build/"
        "untracked/local_source.json"
    )
    assert snapshots[0]["snapshot_path"] == snapshot_path
    assert (chain_dir / "untracked" / "local_source.json").read_text(
        encoding="utf-8"
    ) == '{"local": true}\n'


def test_compile_doc_cli_fails_for_missing_source(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    doc = tmp_path / "docs" / "Project_Facts.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Project Facts\n", encoding="utf-8")

    rc = compiler.main(
        [
            "--workspace-root",
            str(tmp_path),
            "--doc",
            "docs/Project_Facts.md",
            "--source",
            "missing.json",
        ]
    )

    assert rc == 1
