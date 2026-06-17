from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INIT_SCRIPT = REPO_ROOT / ".agents/skills/auto-paper/scripts/init_artifacts.py"
INVENTORY_SCRIPT = (
    REPO_ROOT / ".agents/skills/auto-paper/scripts/reference_inventory.py"
)
CHECK_SCRIPT = REPO_ROOT / ".agents/skills/auto-paper/scripts/artifact_check.py"
FIGURE_SCAN_SCRIPT = (
    REPO_ROOT / ".agents/skills/auto-paper/scripts/figure_requirement_scan.py"
)
CONTROLLER = REPO_ROOT / "tooling/auto_paper/scripts/auto_paper_ctl.py"


def run_python(
    *args: str | Path,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *(str(arg) for arg in args)],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_init_artifacts_list_does_not_require_paper_id() -> None:
    result = run_python(INIT_SCRIPT, "--list")

    assert result.returncode == 0, result.stderr
    assert "config.yaml" in result.stdout
    assert "figure_requirement_scan.md" in result.stdout
    assert "figure_contract.md" in result.stdout
    assert "run_request_register.json" in result.stdout


def test_reference_inventory_excludes_iteration_log(tmp_path: Path) -> None:
    (tmp_path / "iteration_log.json").write_text(
        '{"iterations":[]}\n',
        encoding="utf-8",
    )
    (tmp_path / "data.json").write_text('{"metric":1}\n', encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"

    result = run_python(
        INVENTORY_SCRIPT,
        "--paper-id",
        "paper",
        "--artifact-dir",
        artifact_dir,
        "--root",
        tmp_path,
        "--json",
    )

    assert result.returncode == 0, result.stderr
    items = json.loads(result.stdout)
    paths = {item["path"] for item in items}
    assert "data.json" in paths
    assert "iteration_log.json" not in paths


def test_artifact_check_rejects_placeholder_config_and_empty_rows(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "artifacts"
    init = run_python(
        INIT_SCRIPT,
        "--paper-id",
        "paper",
        "--artifact-dir",
        artifact_dir,
    )
    assert init.returncode == 0, init.stderr

    result = run_python(CHECK_SCRIPT, artifact_dir, "--phase", "intake", "--json")

    assert result.returncode == 1
    findings = json.loads(result.stdout)
    checks = {item["check"] for item in findings}
    assert "config" in checks
    assert "table-rows" in checks


def test_auto_paper_controller_dry_run_detects_run_request(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "auto_paper_output" / "paper"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "run_request_register.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "paper_id": "paper",
                "requests": [
                    {
                        "request_id": "run_req_001",
                        "needed_evidence": "baseline comparison",
                        "status": "pending",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_python(
        CONTROLLER,
        "--workspace-root",
        tmp_path,
        "start",
        "--paper-id",
        "paper",
        "--artifact-dir",
        artifact_dir,
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert state["status"] == "paused"
    assert state["last_decision"] == "RUN_REQUEST"
    assert not (tmp_path / ".auto_paper").exists()


def test_figure_requirement_scan_finds_markdown_visual_cues(
    tmp_path: Path,
) -> None:
    note = tmp_path / "notes.md"
    note.write_text(
        "\n".join(
            [
                "# Plan",
                "建议正文至少包含 4 张核心图表。",
                "Figure 1. Clinical Value-Cost Landscape.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "auto_paper_output" / "paper"

    result = run_python(
        FIGURE_SCAN_SCRIPT,
        note,
        "--paper-id",
        "paper",
        "--artifact-dir",
        artifact_dir,
        "--root",
        tmp_path,
        "--json",
    )

    assert result.returncode == 0, result.stderr
    cues = json.loads(result.stdout)
    assert len(cues) == 2
    assert cues[0]["owner"] == "auto-paper-figure"
    assert cues[0]["suggested_artifact"] == "figure_contract.md"
    assert (artifact_dir / "figure_requirement_scan.md").exists()
