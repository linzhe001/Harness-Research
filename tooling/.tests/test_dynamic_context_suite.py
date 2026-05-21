# ruff: noqa: E501
from __future__ import annotations

import importlib.util
import json
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


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_dynamic_context_suite_passes_legacy_status(tmp_path: Path) -> None:
    suite = load_tool("check_dynamic_context")

    result = suite.check_dynamic_context(tmp_path, stage="status")

    assert result["ok"] is True
    assert result["summary"]["context"]["ok"] is True
    assert result["summary"]["protocol_drift"]["ok"] is True
    assert result["summary"]["docchain"]["ok"] is True


def test_dynamic_context_suite_fails_dynamic_wf10_without_contract(tmp_path: Path) -> None:
    suite = load_tool("check_dynamic_context")
    write_json(tmp_path / "PROJECT_STATE.json", {"context_model_version": "dynamic-protocol-v1"})

    result = suite.check_dynamic_context(tmp_path, stage="wf10")

    assert result["ok"] is False
    assert result["summary"]["context"]["ok"] is False
    assert result["error_count"] >= 1


def test_dynamic_context_suite_writes_review_packet_with_same_results(tmp_path: Path) -> None:
    suite = load_tool("check_dynamic_context")
    write_json(tmp_path / "PROJECT_STATE.json", {"context_model_version": "dynamic-protocol-v1"})
    write(tmp_path / "docs" / "10_contract" / "Evaluation_Contract.md", "# Evaluation Contract\n\nStatus: draft\nEvidence chain: N/A\n")

    result = suite.check_dynamic_context(
        tmp_path,
        stage="wf10",
        write_review_packet=True,
        build_id_override="test_build",
    )

    packet = result["review_packet"]
    assert packet is not None
    packet_path = tmp_path / ".evidence" / "review_packets" / "wf10" / "test_build" / "review_packet.json"
    packet_json = json.loads(packet_path.read_text(encoding="utf-8"))

    assert packet["markdown_path"].endswith("review_packet.md")
    assert packet_json["gates"]["context"]["ok"] == result["gates"]["context"]["ok"]
    assert packet_json["gates"]["docchain"]["ok"] == result["gates"]["docchain"]["ok"]


def test_dynamic_context_suite_allow_flags_can_downgrade_draft_docchain(tmp_path: Path) -> None:
    suite = load_tool("check_dynamic_context")
    write(tmp_path / "docs" / "35_protocol" / "Research_Protocol.md", "# Research Protocol\n\nStatus: draft\nReview required: yes\nEvidence chain: N/A\n")

    strict = suite.check_dynamic_context(tmp_path, stage="status")
    allowed = suite.check_dynamic_context(
        tmp_path,
        stage="status",
        allow_review_required=True,
        allow_missing_draft_docchain=True,
    )

    assert strict["summary"]["docchain"]["ok"] is False
    assert allowed["summary"]["docchain"]["ok"] is True
