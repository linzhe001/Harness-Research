from __future__ import annotations

import importlib.util
import json
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


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_review_packet_passes_legacy_workspace(tmp_path: Path) -> None:
    packet_tool = load_tool("build_review_packet")

    summary = packet_tool.build_review_packet(tmp_path, stage="status", build_id_override="test_build")

    packet_path = tmp_path / ".evidence" / "review_packets" / "status" / "test_build" / "review_packet.md"
    assert summary["ready_for_human_approval"] is False
    assert summary["blocking_count"] == 0
    assert packet_path.exists()
    packet_text = packet_path.read_text(encoding="utf-8")
    assert "Review Packet - Dynamic Context Status" in packet_text
    assert "Review applicability: not_applicable_legacy_or_empty" in packet_text


def test_review_packet_summarizes_dynamic_blockers(tmp_path: Path) -> None:
    packet_tool = load_tool("build_review_packet")
    write_json(tmp_path / "PROJECT_STATE.json", {"context_model_version": "dynamic-protocol-v1"})
    write(tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md", "# Evaluation Contract\n\nStatus: draft\nEvidence chain: N/A\n")
    write(tmp_path / "docs" / "35_protocol" / "Research_Protocol.md", "# Research Protocol\n\nStatus: draft\nReview required: yes\nEvidence chain: N/A\n")
    write(
        tmp_path / "docs" / "35_protocol" / "Protocol_Review.md",
        "# Protocol Review\n\nStatus: draft\n\n## Review Summary\n\n- Verdict: pending\n",
    )
    write(
        tmp_path / "docs" / "30_evidence" / "Open_Questions.md",
        "\n".join(
            [
                "# Evidence Open Questions",
                "",
                "| ID | Question | Why It Matters | Blocking Stage | Next Evidence |",
                "|---|---|---|---|---|",
                "| U009 | Metric is unsettled | invalid eval | WF10 | compare candidates |",
                "",
            ]
        ),
    )

    summary = packet_tool.build_review_packet(tmp_path, stage="wf10", build_id_override="test_build")

    packet_path = tmp_path / ".evidence" / "review_packets" / "wf10" / "test_build" / "review_packet.md"
    packet_text = packet_path.read_text(encoding="utf-8")
    packet_json = json.loads((packet_path.parent / "review_packet.json").read_text(encoding="utf-8"))

    assert summary["ready_for_human_approval"] is False
    assert summary["blocking_count"] > 0
    assert "U009" in packet_text
    assert "baseline_contract" in packet_text
    assert "docs/10_contract/Baseline_Contract.md" in packet_text
    assert "Human Action" in packet_text
    assert packet_json["stage"] == "wf10"
    assert packet_json["ready_for_human_approval"] is False
    assert any(row[0] == "baseline_contract" for row in packet_json["contract_rows"])


def test_review_packet_dry_run_does_not_write(tmp_path: Path) -> None:
    packet_tool = load_tool("build_review_packet")

    summary = packet_tool.build_review_packet(tmp_path, stage="status", build_id_override="test_build", dry_run=True)

    assert summary["markdown_path"].endswith("review_packet.md")
    assert not (tmp_path / ".evidence" / "review_packets").exists()
