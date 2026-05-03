from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VALID_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "evidence_docchain" / "valid"


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
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)


def test_schema_files_parse_as_json() -> None:
    for schema_path in [
        REPO_ROOT / "schemas" / "evidence_chain.schema.json",
        REPO_ROOT / "schemas" / "source_manifest.schema.json",
        REPO_ROOT / "schemas" / "doc_audit.schema.json",
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


def test_compile_doc_generates_valid_docchain(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    validator = load_validator()

    doc = tmp_path / "docs" / "10_contract" / "Project_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Project Contract\n\nStatus: draft\n\n- The project scope is draft. [F:project.scope]\n- Open issue. [U:project.open]\n",
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

    chain_dir = tmp_path / ".evidence" / "chains" / "docs__10_contract__Project_Contract" / "test_build"
    assert summary["ok"] is True
    assert summary["fact_count"] == 1
    assert summary["unresolved_count"] == 1
    assert validator.main([str(chain_dir)]) == 0

    chain = json.loads((chain_dir / "evidence_chain.json").read_text(encoding="utf-8"))
    doc_text = doc.read_text(encoding="utf-8")
    index = json.loads((tmp_path / ".evidence" / "index.json").read_text(encoding="utf-8"))

    assert chain["facts"][0]["fact_id"] == "project.scope"
    assert chain["unresolved"][0]["question_id"] == "project.open"
    assert chain["doc_links"]["markdown_path"] == "docs/10_contract/Project_Contract.md"
    assert "Evidence chain: `.evidence/chains/docs__10_contract__Project_Contract/test_build/evidence_chain.json`" in doc_text
    assert index["docs"]["docs__10_contract__Project_Contract"]["latest_build_id"] == "test_build"


def test_compile_doc_preserves_dirty_source_patch(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    init_git_repo(tmp_path)

    doc = tmp_path / "docs" / "20_facts" / "Execution_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Execution Contract\n\nStatus: draft\n\n- Env: demo. [F:env.demo]\n", encoding="utf-8")
    source.write_text('{"project": "demo"}\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)

    source.write_text('{"project": "demo", "dirty": true}\n', encoding="utf-8")
    compiler.compile_document(
        tmp_path,
        Path("docs/20_facts/Execution_Contract.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    chain_dir = tmp_path / ".evidence" / "chains" / "docs__20_facts__Execution_Contract" / "test_build"
    chain = json.loads((chain_dir / "evidence_chain.json").read_text(encoding="utf-8"))

    assert chain["git"]["is_dirty"] is True
    assert chain["git"]["diff_path"] == ".evidence/chains/docs__20_facts__Execution_Contract/test_build/patch.diff"
    assert (chain_dir / "patch.diff").exists()


def test_compile_doc_preserves_untracked_source_snapshot(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    init_git_repo(tmp_path)

    doc = tmp_path / "docs" / "20_facts" / "Project_Facts.md"
    source = tmp_path / "local_source.json"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Project Facts\n\nStatus: draft\n\n- Local source exists. [F:local.source]\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)
    source.write_text('{"local": true}\n', encoding="utf-8")

    compiler.compile_document(
        tmp_path,
        Path("docs/20_facts/Project_Facts.md"),
        [Path("local_source.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    chain_dir = tmp_path / ".evidence" / "chains" / "docs__20_facts__Project_Facts" / "test_build"
    chain = json.loads((chain_dir / "evidence_chain.json").read_text(encoding="utf-8"))
    snapshots = chain["git"]["untracked_snapshots"]

    assert snapshots[0]["path"] == "local_source.json"
    assert snapshots[0]["snapshot_path"] == ".evidence/chains/docs__20_facts__Project_Facts/test_build/untracked/local_source.json"
    assert (chain_dir / "untracked" / "local_source.json").read_text(encoding="utf-8") == '{"local": true}\n'


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
