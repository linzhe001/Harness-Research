from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "grill"))

import draft  # noqa: E402
import questions  # noqa: E402


def make_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas")
    return root


def test_grill_init_writes_draft_docs_without_evidence_runtime(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path)

    code = draft.main(
        [
            "--workspace-root",
            str(root),
            "init",
            "--seed",
            "Test whether a smaller baseline can expose the core failure.",
            "--json",
        ]
    )

    assert code == 0
    intent = (root / "docs" / "Research_Intent_Draft.md").read_text(
        encoding="utf-8"
    )
    log = (root / "docs" / "Grill_Round_Log.md").read_text(encoding="utf-8")
    packet = (root / "docs" / "Execution_Readiness_Packet.md").read_text(
        encoding="utf-8"
    )
    assert "Status: draft" in intent
    assert "does not complete WF1-WF3" in intent
    assert "## Grill Maturity Checklist" in intent
    assert "## Human Exit Decision" in intent
    assert "Test whether a smaller baseline" in log
    assert "## Round Contract" in log
    assert "## Current Gap Check" in log
    assert "This packet is not a Review Packet" in packet
    assert "## Dataset Access Ledger" in packet
    assert "## Execution Intent Ledger" in packet
    assert "## Baseline Source Ledger" in packet
    assert "direct acquisition source" in packet
    assert "code repository URL" in packet
    assert "Execution Decision must be one of" in packet
    assert "| pending | pending | pending | not run | deferred | pending |" in packet
    assert "baseline_repo_missing" in packet
    assert not (root / ".evidence").exists()
    assert not (root / ".workflow_supervisor").exists()


def test_grill_init_does_not_overwrite_without_force(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    docs = root / "docs"
    docs.mkdir()
    existing = docs / "Research_Intent_Draft.md"
    existing.write_text("custom draft\n", encoding="utf-8")

    code = draft.main(
        ["--workspace-root", str(root), "init", "--seed", "new seed"]
    )

    assert code == 0
    assert existing.read_text(encoding="utf-8") == "custom draft\n"


def test_grill_round_appends_next_round(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    assert draft.main(["--workspace-root", str(root), "init"]) == 0

    code = draft.main(
        [
            "--workspace-root",
            str(root),
            "round",
            "--lens",
            "skeptic",
            "--answer-summary",
            "baseline risk clarified",
            "--risk",
            "claim may depend on baseline choice",
            "--gap-check",
            "baseline choice is still underspecified",
            "--next-question",
            "Which baseline would make the idea unnecessary?",
            "--exit-recommendation",
            "continue_grill",
        ]
    )

    assert code == 0
    log = (root / "docs" / "Grill_Round_Log.md").read_text(encoding="utf-8")
    assert "| 2 | skeptic | baseline risk clarified |" in log
    assert "baseline choice is still underspecified" in log
    assert "Which baseline would make the idea unnecessary?" in log
    assert "- exit_recommendation: `continue_grill`" in log
    assert "## Human Exit Decision\n\n`pending`" in log


def test_grill_packet_redacts_readiness_values(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    readiness_path = root / "readiness.json"
    readiness_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-06-05T00:00:00Z",
                "source": "test",
                "inputs": [
                    {
                        "key": "dataset_root",
                        "kind": "path",
                        "value": "/secret/data/root",
                        "redacted_value": "/data/<redacted>",
                        "verification_status": "candidate",
                        "verified_at": None,
                        "verification_command": "test -d /secret/data/root",
                        "notes": "local path",
                    },
                    {
                        "key": "hf_access_policy",
                        "kind": "policy",
                        "value": (
                            "use operator HF auth for RealX3D and "
                            "SeeThroughSmoke"
                        ),
                        "redacted_value": (
                            "Use operator HF auth for RealX3D and "
                            "SeeThroughSmoke; no credentials recorded"
                        ),
                        "verification_status": "candidate",
                        "verified_at": None,
                        "verification_command": "operator input",
                        "notes": "source-specific HF allowance",
                    },
                    {
                        "key": "baseline_clone_scope",
                        "kind": "policy",
                        "value": "Free-SurGS, Feature 3DGS",
                        "redacted_value": "Free-SurGS, Feature 3DGS",
                        "verification_status": "candidate",
                        "verified_at": None,
                        "verification_command": "operator input",
                        "notes": "first baseline set only",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = draft.main(
        [
            "--workspace-root",
            str(root),
            "init",
            "--readiness-json",
            str(readiness_path),
            "--force",
        ]
    )

    assert code == 0
    packet = (root / "docs" / "Execution_Readiness_Packet.md").read_text(
        encoding="utf-8"
    )
    assert "/data/<redacted>" in packet
    assert "/secret/data/root" not in packet
    assert "hf_access_policy" in packet
    assert "baseline_clone_scope" in packet
    assert "Free-SurGS, Feature 3DGS" in packet
    assert "no credentials recorded" in packet


def test_questions_render_known_lens() -> None:
    payload = questions.question_round("implementation")

    assert payload["schema_version"] == 2
    assert payload["lens"] == "implementation"
    assert payload["questions"][0]["why_this_matters"]
    assert payload["questions"][0]["answer_type"] == "path"
    assert payload["gap_check"][0]["key"] == "operator_observation"
    assert "continue_grill" in payload["exit_options"]
    assert "local path" in questions.render_markdown(payload)
    assert "Maturity gap template" in questions.render_markdown(payload)
