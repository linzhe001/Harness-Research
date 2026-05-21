# ruff: noqa: E501
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_tool(name: str):
    path = REPO_ROOT / "tooling" / "evidence" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_evidence_tables(root: Path) -> None:
    write(
        root / "docs" / "30_evidence" / "Baseline_Table.md",
        "\n".join(
            [
                "# Baseline Table",
                "",
                "| ID | Baseline | Source | Why Relevant | Repro Status | Notes |",
                "|---|---|---|---|---|---|",
                "| B007 | BaseNet | paper x | standard comparison | verified | reproduced locally |",
                "",
            ]
        ),
    )
    write(
        root / "docs" / "30_evidence" / "Metric_Table.md",
        "\n".join(
            [
                "# Metric Table",
                "",
                "| ID | Metric | Direction | Measures | Known Issues | Evidence |",
                "|---|---|---|---|---|---|",
                "| M002 | Accuracy | maximize | classification correctness | class imbalance | validation script |",
                "",
            ]
        ),
    )
    write(
        root / "docs" / "30_evidence" / "Dataset_Table.md",
        "\n".join(
            [
                "# Dataset Table",
                "",
                "| ID | Dataset | Role | Split/Eval Notes | License/Risk | Evidence |",
                "|---|---|---|---|---|---|",
                "| D003 | DemoSet | train/val/test | official split | research use only | dataset card |",
                "",
            ]
        ),
    )
    write(
        root / "docs" / "30_evidence" / "Paper_Table.md",
        "\n".join(
            [
                "# Paper Table",
                "",
                "| ID | Paper | Venue/Year | Claim Used | Evidence Strength | Limitations |",
                "|---|---|---|---|---|---|",
                "| P004 | Useful Paper | 2026 | method works on related data | medium | small benchmark |",
                "",
            ]
        ),
    )
    write(
        root / "docs" / "30_evidence" / "Open_Questions.md",
        "\n".join(
            [
                "# Evidence Open Questions",
                "",
                "| ID | Question | Why It Matters | Blocking Stage | Next Evidence |",
                "|---|---|---|---|---|",
                "| U005 | Is cost a primary metric? | affects contract | WF5 | compare runtime |",
                "",
            ]
        ),
    )


def test_protocol_compiler_writes_draft_under_evidence(tmp_path: Path) -> None:
    compiler = load_tool("compile_protocol")
    write_evidence_tables(tmp_path)

    summary = compiler.compile_protocol(
        tmp_path,
        build_id_override="test_build",
        generated_date="2026-04-29",
    )

    output = tmp_path / ".evidence" / "protocol_compiler" / "test_build" / "docs" / "35_protocol" / "Research_Protocol.md"
    text = output.read_text(encoding="utf-8")

    assert summary["mode"] == "draft"
    assert summary["table_counts"]["baselines"] == 1
    assert "BaseNet" in text
    assert "Accuracy" in text
    assert "DemoSet" in text
    assert "[U:U005]" in text
    assert not (tmp_path / "docs" / "35_protocol" / "Research_Protocol.md").exists()


def test_protocol_compiler_apply_writes_protocol_docs(tmp_path: Path) -> None:
    compiler = load_tool("compile_protocol")
    write_evidence_tables(tmp_path)

    summary = compiler.compile_protocol(
        tmp_path,
        apply=True,
        build_id_override="test_build",
        generated_date="2026-04-29",
    )

    assert summary["mode"] == "apply"
    assert (tmp_path / "docs" / "35_protocol" / "Research_Protocol.md").exists()
    assert (tmp_path / "docs" / "35_protocol" / "Protocol_Assumptions.md").exists()
    assert (tmp_path / "docs" / "35_protocol" / "Protocol_Review.md").exists()
    assert (tmp_path / "docs" / "35_protocol" / "Protocol_Changelog.md").exists()


def test_protocol_compiler_apply_does_not_overwrite_without_flag(tmp_path: Path) -> None:
    compiler = load_tool("compile_protocol")
    write_evidence_tables(tmp_path)
    existing = tmp_path / "docs" / "35_protocol" / "Research_Protocol.md"
    write(existing, "custom protocol\n")

    summary = compiler.compile_protocol(tmp_path, apply=True, build_id_override="test_build")

    assert existing.read_text(encoding="utf-8") == "custom protocol\n"
    assert any(action["action"] == "skip_exists" and action["path"].endswith("Research_Protocol.md") for action in summary["actions"])


def test_protocol_compiler_apply_can_overwrite(tmp_path: Path) -> None:
    compiler = load_tool("compile_protocol")
    write_evidence_tables(tmp_path)
    existing = tmp_path / "docs" / "35_protocol" / "Research_Protocol.md"
    write(existing, "custom protocol\n")

    compiler.compile_protocol(tmp_path, apply=True, overwrite=True, build_id_override="test_build")

    text = existing.read_text(encoding="utf-8")
    assert "custom protocol" not in text
    assert "BaseNet" in text


def test_protocol_compiler_generates_placeholder_when_evidence_missing(tmp_path: Path) -> None:
    compiler = load_tool("compile_protocol")

    compiler.compile_protocol(tmp_path, build_id_override="test_build")

    text = (
        tmp_path
        / ".evidence"
        / "protocol_compiler"
        / "test_build"
        / "docs"
        / "35_protocol"
        / "Research_Protocol.md"
    ).read_text(encoding="utf-8")
    assert "No baseline evidence rows found" in text
    assert "No metric evidence rows found" in text
