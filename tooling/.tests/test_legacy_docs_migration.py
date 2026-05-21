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


def test_legacy_docs_migration_dry_run_does_not_move_files(tmp_path: Path) -> None:
    tool = load_tool("migrate_legacy_docs")
    old = tmp_path / "docs" / "legacy" / "old.md"
    old.parent.mkdir(parents=True)
    old.write_text("old\n", encoding="utf-8")

    summary = tool.migrate_legacy_docs(tmp_path, date="2026-04-30", timestamp="010203")

    assert summary["applied"] is False
    assert summary["move_count"] == 1
    assert old.exists()
    assert summary["actions"][0]["destination"] == "docs/90_legacy/2026-04-30/old__010203.md"


def test_legacy_docs_migration_apply_moves_with_subdir_context(tmp_path: Path) -> None:
    tool = load_tool("migrate_legacy_docs")
    old = tmp_path / "docs" / "legacy" / "nested" / "old.md"
    old.parent.mkdir(parents=True)
    old.write_text("old\n", encoding="utf-8")

    summary = tool.migrate_legacy_docs(tmp_path, apply=True, date="2026-04-30", timestamp="010203")

    destination = tmp_path / "docs" / "90_legacy" / "2026-04-30" / "nested__old__010203.md"
    assert summary["applied"] is True
    assert summary["move_count"] == 1
    assert not old.exists()
    assert destination.read_text(encoding="utf-8") == "old\n"


def test_legacy_docs_migration_apply_avoids_flattened_name_collisions(tmp_path: Path) -> None:
    tool = load_tool("migrate_legacy_docs")
    nested = tmp_path / "docs" / "legacy" / "nested" / "old.md"
    flat_collision = tmp_path / "docs" / "legacy" / "nested__old.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("nested\n", encoding="utf-8")
    flat_collision.write_text("flat\n", encoding="utf-8")

    summary = tool.migrate_legacy_docs(tmp_path, apply=True, date="2026-04-30", timestamp="010203")

    destinations = [action["destination"] for action in summary["actions"] if action["action"] == "move"]
    assert len(destinations) == 2
    assert len(set(destinations)) == 2
    assert (tmp_path / "docs" / "90_legacy" / "2026-04-30" / "nested__old__010203.md").exists()
    assert (tmp_path / "docs" / "90_legacy" / "2026-04-30" / "nested__old__010203__1.md").exists()


def test_legacy_docs_migration_ignores_gitkeep(tmp_path: Path) -> None:
    tool = load_tool("migrate_legacy_docs")
    placeholder = tmp_path / "docs" / "legacy" / ".gitkeep"
    placeholder.parent.mkdir(parents=True)
    placeholder.write_text("", encoding="utf-8")

    summary = tool.migrate_legacy_docs(tmp_path, apply=True, date="2026-04-30", timestamp="010203")

    assert summary["move_count"] == 0
    assert summary["actions"][0]["action"] == "skip_empty_source"
    assert placeholder.exists()


def test_legacy_docs_migration_missing_source_is_noop(tmp_path: Path) -> None:
    tool = load_tool("migrate_legacy_docs")

    summary = tool.migrate_legacy_docs(tmp_path, apply=True, date="2026-04-30", timestamp="010203")

    assert summary["ok"] is True
    assert summary["move_count"] == 0
    assert summary["actions"][0]["action"] == "skip_missing_source"
