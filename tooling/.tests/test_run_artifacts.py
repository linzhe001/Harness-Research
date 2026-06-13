from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling"))

from run_artifacts import run_artifact_errors  # noqa: E402


def _iteration(exp_dir: str = "experiments/iter1") -> dict:
    return {
        "id": "iter1",
        "git_commit": "abc123",
        "run_manifest": {
            "artifact_contract_version": "1",
            "run_type": "full",
            "command": "python train.py",
            "exp_dir": exp_dir,
            "resolved_config_path": f"{exp_dir}/run_param.yaml",
            "stdout_log_path": f"{exp_dir}/stdout+stderr.log",
            "git_snapshot_path": f"{exp_dir}/git_status/commit.txt",
            "git_commit": "abc123",
            "eval_artifact_paths": [f"{exp_dir}/epochs/1/eval.jsonl"],
        },
    }


def _write_bundle(root: Path, iteration: dict, *, commit: str = "abc123") -> None:
    manifest = iteration["run_manifest"]
    exp_dir = root / manifest["exp_dir"]
    (exp_dir / "git_status").mkdir(parents=True, exist_ok=True)
    (exp_dir / "epochs" / "1").mkdir(parents=True, exist_ok=True)
    (exp_dir / "run_param.yaml").write_text("seed: 1\n", encoding="utf-8")
    (exp_dir / "stdout+stderr.log").write_text("done\n", encoding="utf-8")
    (exp_dir / "git_status" / "commit.txt").write_text(
        f"{commit}\n",
        encoding="utf-8",
    )
    (exp_dir / "epochs" / "1" / "eval.jsonl").write_text(
        '{"metric": 1}\n',
        encoding="utf-8",
    )


def test_run_artifact_errors_accepts_valid_bundle(tmp_path: Path) -> None:
    iteration = _iteration()
    _write_bundle(tmp_path, iteration)

    assert run_artifact_errors(tmp_path, iteration) == []


def test_run_artifact_errors_rejects_file_exp_dir(tmp_path: Path) -> None:
    iteration = _iteration()
    exp_dir_path = tmp_path / iteration["run_manifest"]["exp_dir"]
    exp_dir_path.parent.mkdir(parents=True, exist_ok=True)
    exp_dir_path.write_text("not a directory\n", encoding="utf-8")

    errors = run_artifact_errors(tmp_path, iteration)

    assert any("exp_dir directory does not exist" in error for error in errors)


def test_run_artifact_errors_rejects_directory_stdout_log(
    tmp_path: Path,
) -> None:
    iteration = _iteration()
    _write_bundle(tmp_path, iteration)
    log_path = tmp_path / iteration["run_manifest"]["stdout_log_path"]
    log_path.unlink()
    log_path.mkdir()

    errors = run_artifact_errors(tmp_path, iteration)

    assert any("stdout_log_path file does not exist" in error for error in errors)


def test_run_artifact_errors_rejects_snapshot_commit_mismatch(
    tmp_path: Path,
) -> None:
    iteration = _iteration()
    _write_bundle(tmp_path, iteration, commit="def456")

    errors = run_artifact_errors(tmp_path, iteration)

    assert any("git_snapshot_path does not mention" in error for error in errors)
