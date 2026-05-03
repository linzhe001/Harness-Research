from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_tool(name: str):
    path = REPO_ROOT / "tooling" / "evidence" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)


def test_docchain_gate_passes_legacy_workspace(tmp_path: Path) -> None:
    gates = load_tool("check_docchain_gates")

    result = gates.gate_result(tmp_path)

    assert result["ok"] is True
    assert result["checked_doc_count"] == 0
    assert result["dynamic_docchain"] is False


def test_docchain_gate_fails_missing_chain_for_current_doc(tmp_path: Path) -> None:
    gates = load_tool("check_docchain_gates")
    doc = tmp_path / "docs" / "10_contract" / "Project_Contract.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Project Contract\n\nStatus: approved\nEvidence chain: N/A\n", encoding="utf-8")

    result = gates.gate_result(tmp_path)

    assert result["ok"] is False
    assert result["error_count"] == 1
    assert result["checks"][0]["name"] == "evidence_chain_header"


def test_docchain_gate_can_warn_for_missing_draft_chain(tmp_path: Path) -> None:
    gates = load_tool("check_docchain_gates")
    doc = tmp_path / "docs" / "35_protocol" / "Research_Protocol.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Research Protocol\n\nStatus: draft\nEvidence chain: N/A\n", encoding="utf-8")

    result = gates.gate_result(tmp_path, allow_missing_draft=True)

    assert result["ok"] is True
    assert result["warning_count"] == 1


def test_docchain_gate_passes_valid_compiled_doc(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")

    doc = tmp_path / "docs" / "20_facts" / "Project_Facts.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    chain_path = ".evidence/chains/docs__20_facts__Project_Facts/test_build/evidence_chain.json"
    audit_path = ".evidence/chains/docs__20_facts__Project_Facts/test_build/doc_audit.json"
    doc.write_text(
        "\n".join(
            [
                "# Project Facts",
                "",
                "Status: draft",
                f"Evidence chain: `{chain_path}`",
                f"Evidence audit: `{audit_path}`",
                "Audit result: PASS",
                "",
                "- The project scope is draft. [F:project.scope]",
                "- Open issue. [U:project.open]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_json(source, {"project": "demo"})

    compiler.compile_document(
        tmp_path,
        Path("docs/20_facts/Project_Facts.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    result = gates.gate_result(tmp_path)

    assert result["ok"] is True
    assert result["checked_doc_count"] == 1
    assert result["error_count"] == 0


def test_docchain_gate_fails_contract_with_context_only_evidence(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")

    doc = tmp_path / "docs" / "10_contract" / "Project_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Project Contract\n\nStatus: draft\n\n- Scope: demo. [F:scope.demo]\n", encoding="utf-8")
    write_json(source, {"project": "demo"})

    compiler.compile_document(
        tmp_path,
        Path("docs/10_contract/Project_Contract.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    result = gates.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(check["name"] == "contract_fact_confidence" and not check["ok"] for check in result["checks"])
    assert any(check["name"] == "contract_support_relation" and not check["ok"] for check in result["checks"])


def test_docchain_gate_accepts_contract_with_explicit_support(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")

    doc = tmp_path / "docs" / "10_contract" / "Project_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Project Contract\n\nStatus: draft\n\n- Scope: demo. [F:scope.demo]\n", encoding="utf-8")
    write_json(source, {"project": "demo"})

    compiler.compile_document(
        tmp_path,
        Path("docs/10_contract/Project_Contract.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )
    chain_path = tmp_path / ".evidence" / "chains" / "docs__10_contract__Project_Contract" / "test_build" / "evidence_chain.json"
    chain = json.loads(chain_path.read_text(encoding="utf-8"))
    chain["facts"][0]["confidence"] = "medium"
    for entry in chain["evidence"]:
        if entry["path"] == "PROJECT_STATE.json":
            entry["support_relation"] = "supports"
            entry["supports"] = ["scope.demo"]
    chain_path.write_text(json.dumps(chain, indent=2) + "\n", encoding="utf-8")

    result = gates.gate_result(tmp_path)

    assert result["ok"] is True
    assert any(check["name"] == "contract_support_relation" and check["ok"] for check in result["checks"])


def test_compile_doc_reviewed_support_can_satisfy_contract_gate(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")

    doc = tmp_path / "docs" / "10_contract" / "Project_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Project Contract\n\nStatus: draft\n\n- Scope: demo. [F:scope.demo]\n", encoding="utf-8")
    write_json(source, {"project": "demo"})

    compiler.compile_document(
        tmp_path,
        Path("docs/10_contract/Project_Contract.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
        fact_confidence="medium",
        support_relation="supports",
    )

    result = gates.gate_result(tmp_path)

    assert result["ok"] is True
    assert any(check["name"] == "contract_fact_confidence" and check["ok"] for check in result["checks"])
    assert any(check["name"] == "contract_support_relation" and check["ok"] for check in result["checks"])


def test_docchain_gate_passes_after_compile_from_template_headers(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")

    doc = tmp_path / "docs" / "20_facts" / "Project_Facts.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "\n".join(
            [
                "# Project Facts",
                "",
                "Status: draft",
                "Evidence chain: N/A",
                "Evidence audit: N/A",
                "Audit result: N/A",
                "",
                "- Project name: demo. [F:project.name]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_json(source, {"project": "demo"})

    compiler.compile_document(
        tmp_path,
        Path("docs/20_facts/Project_Facts.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    result = gates.gate_result(tmp_path)

    assert result["ok"] is True
    assert not any(check["name"] == "source_manifest_doc_hash" and not check["ok"] for check in result["checks"])


def test_docchain_gate_detects_stale_markdown_after_compile(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")

    doc = tmp_path / "docs" / "20_facts" / "Project_Facts.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    chain_path = ".evidence/chains/docs__20_facts__Project_Facts/test_build/evidence_chain.json"
    audit_path = ".evidence/chains/docs__20_facts__Project_Facts/test_build/doc_audit.json"
    doc.write_text(
        "\n".join(
            [
                "# Project Facts",
                "",
                "Status: draft",
                f"Evidence chain: `{chain_path}`",
                f"Evidence audit: `{audit_path}`",
                "Audit result: PASS",
                "",
                "- Project name: demo. [F:project.name]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_json(source, {"project": "demo"})
    compiler.compile_document(
        tmp_path,
        Path("docs/20_facts/Project_Facts.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )
    doc.write_text(doc.read_text(encoding="utf-8") + "- Added after compile. [F:stale]\n", encoding="utf-8")

    result = gates.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(check["name"] == "source_manifest_doc_hash" and not check["ok"] for check in result["checks"])


def test_docchain_gate_fails_dirty_contract_source_context(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")
    init_git_repo(tmp_path)

    doc = tmp_path / "docs" / "10_contract" / "Project_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Project Contract\n\nStatus: draft\n\n- Scope: demo. [F:scope.demo]\n", encoding="utf-8")
    write_json(source, {"project": "demo"})
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)

    source.write_text('{"project": "demo", "dirty": true}\n', encoding="utf-8")
    compiler.compile_document(
        tmp_path,
        Path("docs/10_contract/Project_Contract.md"),
        [Path("PROJECT_STATE.json")],
        build_id_override="test_build",
        compiled_by="test",
    )

    result = gates.gate_result(tmp_path)

    assert result["ok"] is False
    assert any(check["name"] == "git_source_clean_required" and not check["ok"] for check in result["checks"])


def test_docchain_gate_accepts_dirty_fact_doc_with_patch(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")
    init_git_repo(tmp_path)

    doc = tmp_path / "docs" / "20_facts" / "Execution_Contract.md"
    source = tmp_path / "PROJECT_STATE.json"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Execution Contract\n\nStatus: draft\n\n- Env: demo. [F:env.demo]\n", encoding="utf-8")
    write_json(source, {"project": "demo"})
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

    result = gates.gate_result(tmp_path)

    assert result["ok"] is True
    assert any(check["name"] == "git_dirty_patch_hash" and check["ok"] for check in result["checks"])


def test_docchain_gate_accepts_dirty_fact_doc_with_untracked_snapshot(tmp_path: Path) -> None:
    compiler = load_tool("compile_doc")
    gates = load_tool("check_docchain_gates")
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

    result = gates.gate_result(tmp_path)

    assert result["ok"] is True
    assert any(check["name"] == "git_untracked_snapshots" and check["ok"] for check in result["checks"])
