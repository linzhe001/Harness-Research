from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "grill"))

import readiness  # noqa: E402


def make_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas")
    return root


def test_readiness_helper_does_not_write_without_explicit_flag(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)

    code = readiness.main(["--workspace-root", str(root)])

    assert code == 0
    output = root / ".workflow_supervisor" / "readiness.json"
    assert not output.exists()


def test_readiness_helper_writes_supervisor_owned_json(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)

    code = readiness.main(["--workspace-root", str(root), "--write-readiness"])

    assert code == 0
    output = root / ".workflow_supervisor" / "readiness.json"
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["source"] == "grill"
    assert data["external_download_policy"] == "unset"
    assert data["approved_datasets"] == []
    assert data["approved_baselines"] == []
    assert data["target_paths"] == {}
    assert data["unknowns"] == []
    assert data["operator_approved_at"] is None
    assert data["inputs"] == []


def test_readiness_helper_rejects_invalid_payload(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    bad = root / "bad.json"
    bad.write_text('{"schema_version": 1, "inputs": []}\n', encoding="utf-8")

    code = readiness.main(
        ["--workspace-root", str(root), "--input-json", str(bad), "--check"]
    )

    assert code == 2


def test_readiness_helper_accepts_policy_inputs(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    payload = root / "readiness.json"
    payload.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-06-07T00:00:00Z",
                "source": "grill",
                "inputs": [
                    {
                        "key": "baseline_clone_policy",
                        "kind": "policy",
                        "value": "clone_first_baseline_set_only",
                        "redacted_value": "clone first baseline set only",
                        "verification_status": "candidate",
                        "verified_at": None,
                        "verification_command": "operator input",
                        "notes": "source-specific baseline clone policy",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = readiness.main(
        ["--workspace-root", str(root), "--input-json", str(payload), "--check"]
    )

    assert code == 0


def test_readiness_helper_accepts_structured_approval_fields(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    payload = root / "readiness.json"
    payload.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-06-07T00:00:00Z",
                "source": "grill",
                "external_download_policy": "allow_if_approved",
                "approved_datasets": [
                    {
                        "source": "https://huggingface.co/datasets/example/realx3d",
                        "target": "data/realx3d",
                        "license": "unknown",
                        "max_size_gb": 50,
                        "access_status": "approved",
                        "source_ref": "operator input",
                        "notes": "first prepare source",
                    }
                ],
                "approved_baselines": [
                    {
                        "id": "free_surgs",
                        "repo": "https://github.com/example/Free-SurGS",
                        "ref": "main",
                        "target": "baselines/Free-SurGS",
                        "access_status": "approved",
                        "role": "baseline",
                        "source_ref": "operator input",
                        "notes": "first baseline set",
                    }
                ],
                "target_paths": {
                    "dataset_root": "data",
                    "baseline_cache": "baselines",
                },
                "unknowns": ["private credentials are not recorded"],
                "operator_approved_at": "2026-06-07T00:00:00Z",
                "inputs": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = readiness.main(
        ["--workspace-root", str(root), "--input-json", str(payload), "--check"]
    )

    assert code == 0


def test_readiness_helper_verifies_synthetic_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = make_workspace(tmp_path)
    data_dir = root / "synthetic"
    data_dir.mkdir()
    target = data_dir / "dataset.txt"
    target.write_text("ok\n", encoding="utf-8")
    payload = root / "readiness.json"
    payload.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-06-05T00:00:00Z",
                "source": "test",
                "inputs": [
                    {
                        "key": "dataset_root",
                        "kind": "path",
                        "value": "synthetic/dataset.txt",
                        "redacted_value": "synthetic/<redacted>",
                        "verification_status": "candidate",
                        "verified_at": None,
                        "verification_command": "test -f synthetic/dataset.txt",
                        "notes": "synthetic path fixture",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = readiness.main(
        [
            "--workspace-root",
            str(root),
            "--input-json",
            str(payload),
            "--check",
            "--verify-paths",
            "--json",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert code == 0
    assert output["verified_path_count"] == 1


def test_readiness_helper_rejects_missing_synthetic_path(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    payload = root / "readiness.json"
    payload.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-06-05T00:00:00Z",
                "source": "test",
                "inputs": [
                    {
                        "key": "dataset_root",
                        "kind": "path",
                        "value": "synthetic/missing.txt",
                        "redacted_value": "synthetic/<redacted>",
                        "verification_status": "candidate",
                        "verified_at": None,
                        "verification_command": "test -f synthetic/missing.txt",
                        "notes": "synthetic path fixture",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = readiness.main(
        [
            "--workspace-root",
            str(root),
            "--input-json",
            str(payload),
            "--check",
            "--verify-paths",
        ]
    )

    assert code == 2
