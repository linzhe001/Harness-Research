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


def write_clean_protocol_workspace(root: Path) -> None:
    write(
        root / "docs" / "35_protocol" / "Research_Protocol.md",
        "# Research Protocol\n\nStatus: draft\nReview required: no\n",
    )
    write(
        root / "docs" / "35_protocol" / "Protocol_Review.md",
        "# Protocol Review\n\nStatus: draft\n\n## Review Summary\n\n"
        "- Verdict: accepted\n"
        "- Main risk: none\n"
        "- Required changes: none\n",
    )
    write(
        root / "docs" / "35_protocol" / "Protocol_Assumptions.md",
        "# Protocol Assumptions\n\n"
        "| Assumption | Confidence | Evidence | Review Trigger |\n"
        "|---|---|---|---|\n",
    )
    write(
        root / "docs" / "30_evidence" / "Open_Questions.md",
        "# Evidence Open Questions\n\n"
        "| ID | Question | Why It Matters | Blocking Stage | Next Evidence |\n"
        "|---|---|---|---|---|\n",
    )


def test_protocol_drift_gate_passes_legacy_workspace(tmp_path: Path) -> None:
    drift = load_tool("check_protocol_drift")

    result = drift.gate_result(tmp_path, stage="wf10")

    assert result["ok"] is True
    assert result["dynamic_protocol"] is False


def test_protocol_drift_gate_fails_required_review_for_target_stage(
    tmp_path: Path,
) -> None:
    drift = load_tool("check_protocol_drift")
    write_clean_protocol_workspace(tmp_path)
    protocol = tmp_path / "docs" / "35_protocol" / "Research_Protocol.md"
    protocol.write_text(
        "# Research Protocol\n\nStatus: draft\nReview required: yes\n", encoding="utf-8"
    )

    result = drift.gate_result(tmp_path, stage="wf10")

    assert result["ok"] is False
    assert any(
        check["name"] == "protocol_review_required" and not check["ok"]
        for check in result["checks"]
    )


def test_protocol_drift_gate_detects_blocking_open_question(tmp_path: Path) -> None:
    drift = load_tool("check_protocol_drift")
    write_clean_protocol_workspace(tmp_path)
    write(
        tmp_path / "docs" / "30_evidence" / "Open_Questions.md",
        "\n".join(
            [
                "# Evidence Open Questions",
                "",
                "| ID | Question | Why It Matters | Blocking Stage | Next Evidence |",
                "|---|---|---|---|---|",
                "| U007 | Metric choice is unresolved | WF10 eval would be invalid "
                "| WF10 | compare metrics |",
                "",
            ]
        ),
    )

    result = drift.gate_result(tmp_path, stage="wf10")

    assert result["ok"] is False
    assert any(
        check["name"] == "blocking_open_questions" and not check["ok"]
        for check in result["checks"]
    )


def test_protocol_drift_gate_detects_due_low_confidence_assumption(
    tmp_path: Path,
) -> None:
    drift = load_tool("check_protocol_drift")
    write_clean_protocol_workspace(tmp_path)
    write(
        tmp_path / "docs" / "35_protocol" / "Protocol_Assumptions.md",
        "\n".join(
            [
                "# Protocol Assumptions",
                "",
                "| Assumption | Confidence | Evidence | Review Trigger |",
                "|---|---|---|---|",
                "| Cost is non-primary | low | survey only | before WF5 |",
                "",
            ]
        ),
    )

    result = drift.gate_result(tmp_path, stage="wf5")

    assert result["ok"] is False
    assert any(
        check["name"] == "low_confidence_assumptions_due" and not check["ok"]
        for check in result["checks"]
    )


def test_protocol_drift_gate_detects_unreviewed_negative_result(tmp_path: Path) -> None:
    drift = load_tool("check_protocol_drift")
    write_clean_protocol_workspace(tmp_path)
    write(
        tmp_path / "docs" / "50_memory" / "Negative_Results.md",
        "# Negative Results\n\n"
        "- ID: NEG-001\n"
        "- Hypothesis: wider model helps\n"
        "- Observed: lower metric\n",
    )

    result = drift.gate_result(tmp_path, stage="wf10")

    assert result["ok"] is False
    assert any(
        check["name"] == "unreviewed_negative_results" and not check["ok"]
        for check in result["checks"]
    )


def test_protocol_drift_gate_passes_when_negative_result_is_reviewed(
    tmp_path: Path,
) -> None:
    drift = load_tool("check_protocol_drift")
    write_clean_protocol_workspace(tmp_path)
    write(
        tmp_path / "docs" / "50_memory" / "Negative_Results.md",
        "# Negative Results\n\n"
        "- ID: NEG-001\n"
        "- Hypothesis: wider model helps\n"
        "- Observed: lower metric\n",
    )
    write(
        tmp_path / "docs" / "35_protocol" / "Protocol_Changelog.md",
        "# Protocol Changelog\n\n"
        "| Date | Change | Reason | Evidence | Reviewer |\n"
        "|---|---|---|---|---|\n"
        "| 2026-04-29 | keep width fixed | NEG-001 reviewed | "
        "docs/50_memory/Negative_Results.md | human |\n",
    )

    result = drift.gate_result(tmp_path, stage="wf10")

    assert result["ok"] is True


def test_protocol_drift_gate_detects_unreviewed_pivot_decision(tmp_path: Path) -> None:
    drift = load_tool("check_protocol_drift")
    write_clean_protocol_workspace(tmp_path)
    write_json(
        tmp_path / "iteration_log.json",
        {
            "project": "demo",
            "baseline_metrics": {},
            "iterations": [
                {
                    "id": "iter1",
                    "date": "2026-04-29",
                    "hypothesis": "test",
                    "status": "completed",
                    "decision": "PIVOT",
                }
            ],
        },
    )

    result = drift.gate_result(tmp_path, stage="wf10")

    assert result["ok"] is False
    assert any(
        check["name"] == "iteration_decision_protocol_drift" and not check["ok"]
        for check in result["checks"]
    )


def test_protocol_drift_gate_fails_unknown_review_verdict(tmp_path: Path) -> None:
    drift = load_tool("check_protocol_drift")
    write_clean_protocol_workspace(tmp_path)
    review = tmp_path / "docs" / "35_protocol" / "Protocol_Review.md"
    review.write_text(
        "# Protocol Review\n\nStatus: draft\n\n## Review Summary\n\n"
        "- Verdict: greenlight\n- Main risk: none\n- Required changes: none\n",
        encoding="utf-8",
    )

    result = drift.gate_result(tmp_path, stage="wf10")

    assert result["ok"] is False
    assert any(
        check["name"] == "protocol_review_verdict" and not check["ok"]
        for check in result["checks"]
    )


def test_protocol_drift_old_decimal_stage_token_does_not_crash(tmp_path: Path) -> None:
    drift = load_tool("check_protocol_drift")
    write_clean_protocol_workspace(tmp_path)
    write(
        tmp_path / "docs" / "30_evidence" / "Open_Questions.md",
        "| ID | Question | Why It Matters | Blocking Stage | Next Evidence |\n"
        "|---|---|---|---|---|\n"
        f"| U010 | Legacy trigger | old docs | WF7{'.'}5 | inspect old docs |\n",
    )

    result = drift.gate_result(tmp_path, stage="wf10")

    assert result["ok"] is False
    assert any(
        check["name"] == "blocking_open_questions" and not check["ok"]
        for check in result["checks"]
    )
