"""Shared validation for Harness run artifact bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_MANIFEST = object()

REQUIRED_COMPLETED_FIELDS = (
    "resolved_config_path",
    "stdout_log_path",
    "git_snapshot_path",
)


def run_artifact_errors(
    root: Path,
    iteration: dict[str, Any],
    *,
    run_manifest: dict[str, Any] | object = _DEFAULT_MANIFEST,
    manifest_name: str = "run_manifest",
    require_eval_artifacts: bool = True,
) -> list[str]:
    """Return human-readable run artifact bundle errors for an iteration."""
    if run_manifest is _DEFAULT_MANIFEST:
        run_manifest = iteration.get("run_manifest")
    if not isinstance(run_manifest, dict):
        return [f"{manifest_name} is required"]

    errors: list[str] = []
    for field in ("artifact_contract_version", "run_type", "command"):
        if _nonempty(run_manifest.get(field)) is None:
            errors.append(f"{manifest_name}.{field} is required")

    exp_dir = _nonempty(run_manifest.get("exp_dir"))
    if exp_dir is None:
        errors.append(f"{manifest_name}.exp_dir is required")
    elif not _path_is_dir(root, run_manifest, exp_dir):
        errors.append(
            f"{manifest_name}.exp_dir directory does not exist: {exp_dir}"
        )

    iteration_commit = _nonempty(iteration.get("git_commit"))
    manifest_commit = _nonempty(run_manifest.get("git_commit"))
    if iteration_commit is None:
        errors.append("iteration.git_commit is required")
    if manifest_commit is None:
        errors.append(f"{manifest_name}.git_commit is required")
    elif iteration_commit is not None and manifest_commit != iteration_commit:
        errors.append(
            f"{manifest_name}.git_commit must match iteration.git_commit "
            f"({manifest_commit!r} != {iteration_commit!r})"
        )

    for field in REQUIRED_COMPLETED_FIELDS:
        value = _nonempty(run_manifest.get(field))
        if value is None:
            errors.append(f"{manifest_name}.{field} is required")
        elif not _path_is_file(root, run_manifest, value):
            errors.append(f"{manifest_name}.{field} file does not exist: {value}")

    if require_eval_artifacts:
        eval_paths = run_manifest.get("eval_artifact_paths")
        if not isinstance(eval_paths, list) or not eval_paths:
            errors.append(f"{manifest_name}.eval_artifact_paths is required")
        else:
            for value in eval_paths:
                path_value = _nonempty(value)
                if path_value is None:
                    errors.append(
                        f"{manifest_name}.eval_artifact_paths contains empty path"
                    )
                elif not _path_is_file(root, run_manifest, path_value):
                    errors.append(
                        f"{manifest_name}.eval_artifact_paths file does not exist: "
                        f"{path_value}"
                    )

    checkpoint_path = _nonempty(run_manifest.get("checkpoint_path"))
    if checkpoint_path is not None and not _path_exists(
        root,
        run_manifest,
        checkpoint_path,
    ):
        errors.append(
            f"{manifest_name}.checkpoint_path path does not exist: "
            f"{checkpoint_path}"
        )

    git_snapshot_path = _nonempty(run_manifest.get("git_snapshot_path"))
    if git_snapshot_path is not None and manifest_commit is not None:
        snapshot_error = _git_snapshot_commit_error(
            root,
            run_manifest,
            git_snapshot_path,
            manifest_commit,
            manifest_name,
        )
        if snapshot_error:
            errors.append(snapshot_error)

    return errors


def _nonempty(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _candidate_paths(root: Path, manifest: dict[str, Any], value: str) -> list[Path]:
    path = Path(value)
    if path.is_absolute():
        return [path]
    candidates = [root / path]
    exp_dir = _nonempty(manifest.get("exp_dir"))
    if exp_dir is not None:
        candidates.append(root / exp_dir / path)
    return candidates


def _path_exists(root: Path, manifest: dict[str, Any], value: str) -> bool:
    return any(path.exists() for path in _candidate_paths(root, manifest, value))


def _path_is_file(root: Path, manifest: dict[str, Any], value: str) -> bool:
    return any(path.is_file() for path in _candidate_paths(root, manifest, value))


def _path_is_dir(root: Path, manifest: dict[str, Any], value: str) -> bool:
    return any(path.is_dir() for path in _candidate_paths(root, manifest, value))


def _first_existing_path(
    root: Path,
    manifest: dict[str, Any],
    value: str,
) -> Path | None:
    for path in _candidate_paths(root, manifest, value):
        if path.exists():
            return path
    return None


def _git_snapshot_commit_error(
    root: Path,
    manifest: dict[str, Any],
    git_snapshot_path: str,
    expected_commit: str,
    manifest_name: str,
) -> str | None:
    path = _first_existing_path(root, manifest, git_snapshot_path)
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"{manifest_name}.git_snapshot_path could not be read: {exc}"
    if not text.strip():
        return f"{manifest_name}.git_snapshot_path is empty: {git_snapshot_path}"
    observed = _json_commit_value(text)
    if observed is not None and observed != expected_commit:
        return (
            f"{manifest_name}.git_snapshot_path commit does not match "
            f"{manifest_name}.git_commit ({observed!r} != {expected_commit!r})"
        )
    if observed is None and expected_commit not in text:
        return (
            f"{manifest_name}.git_snapshot_path does not mention "
            f"{manifest_name}.git_commit {expected_commit!r}"
        )
    return None


def _json_commit_value(text: str) -> str | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    for key in ("git_commit", "commit", "commit_hash", "head"):
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None
