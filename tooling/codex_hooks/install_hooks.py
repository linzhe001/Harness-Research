from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

RUNTIME_SCRIPTS = [
    "harness_contracts.py",
    "user_prompt_submit.py",
    "pre_tool_use_policy.py",
    "post_tool_use_markers.py",
    "require_gate_ledger.py",
]
RULE_TEMPLATES = [
    "harness_external_review.rules",
]
HOOKS_FEATURE = "hooks"
LEGACY_HOOKS_FEATURE = "codex_hooks"


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def _load_hook_config(source: Path, script_dir: Path | None) -> str:
    text = source.read_text(encoding="utf-8")
    if script_dir is None:
        return text

    data = json.loads(text)
    marker = '"$(git rev-parse --show-toplevel)/tooling/codex_hooks/'
    replacement = f'"{script_dir.as_posix()}/'
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command")
                if isinstance(command, str):
                    hook["command"] = command.replace(marker, replacement)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _is_feature_assignment(line: str, feature_name: str) -> bool:
    return re.match(rf"^{re.escape(feature_name)}\s*=", line) is not None


def _set_feature_assignment(line: str, feature_name: str) -> str:
    return re.sub(
        rf"^(\s*){re.escape(feature_name)}\s*=.*$",
        rf"\1{feature_name} = true",
        line,
        count=1,
    )


def _ensure_hooks_enabled(text: str) -> str:
    lines = text.splitlines()
    newline = "\n" if text.endswith("\n") or text == "" else ""

    features_index: int | None = None
    next_section_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[features]":
            features_index = index
            continue
        if (
            features_index is not None
            and index > features_index
            and stripped.startswith("[")
            and stripped.endswith("]")
        ):
            next_section_index = index
            break

    if features_index is not None:
        insert_at = next_section_index if next_section_index is not None else len(lines)
        hooks_index: int | None = None
        legacy_indexes: list[int] = []
        for index in range(features_index + 1, insert_at):
            stripped = lines[index].strip()
            if stripped.startswith("#"):
                continue
            if _is_feature_assignment(stripped, HOOKS_FEATURE):
                hooks_index = index
                continue
            if _is_feature_assignment(stripped, LEGACY_HOOKS_FEATURE):
                legacy_indexes.append(index)

        if hooks_index is not None:
            lines[hooks_index] = _set_feature_assignment(
                lines[hooks_index], HOOKS_FEATURE
            )
            for index in reversed(legacy_indexes):
                lines.pop(index)
            return "\n".join(lines) + newline

        if legacy_indexes:
            first_legacy_index = legacy_indexes[0]
            lines[first_legacy_index] = _set_feature_assignment(
                lines[first_legacy_index], LEGACY_HOOKS_FEATURE
            ).replace(LEGACY_HOOKS_FEATURE, HOOKS_FEATURE, 1)
            for index in reversed(legacy_indexes[1:]):
                lines.pop(index)
            return "\n".join(lines) + newline

        while insert_at > features_index + 1 and lines[insert_at - 1].strip() == "":
            insert_at -= 1
        lines.insert(insert_at, "hooks = true")
        return "\n".join(lines) + "\n"

    if not text:
        return "[features]\nhooks = true\n"
    prefix = "\n" if text and not text.endswith("\n") else ""
    return text + prefix + "\n[features]\nhooks = true\n"


def _ensure_codex_hooks_enabled(text: str) -> str:
    return _ensure_hooks_enabled(text)


def _ensure_feature_flag(config_path: Path) -> None:
    if not config_path.exists():
        config_path.write_text("[features]\nhooks = true\n", encoding="utf-8")
        return
    text = config_path.read_text(encoding="utf-8")
    updated = _ensure_hooks_enabled(text)
    if updated != text:
        config_path.write_text(updated, encoding="utf-8")


def _copy_runtime_scripts(root: Path, target_dir: Path) -> None:
    source_dir = root / "tooling" / "codex_hooks"
    target_dir.mkdir(parents=True, exist_ok=True)
    for script in RUNTIME_SCRIPTS:
        source = source_dir / script
        if not source.exists():
            raise FileNotFoundError(f"missing runtime script: {source}")
        shutil.copyfile(source, target_dir / script)


def _copy_rule_templates(root: Path, codex_dir: Path) -> None:
    source_dir = root / "tooling" / "codex_hooks" / "rules"
    target_dir = codex_dir / "rules"
    for template in RULE_TEMPLATES:
        source = source_dir / template
        if not source.exists():
            raise FileNotFoundError(f"missing rule template: {source}")
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target_dir / template)


def _remove_rule_templates(codex_dir: Path) -> None:
    target_dir = codex_dir / "rules"
    for template in RULE_TEMPLATES:
        (target_dir / template).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Harness Codex hooks.")
    parser.add_argument("--workspace-root", default=".", help="Repository root.")
    parser.add_argument(
        "--scope",
        choices=["workspace", "repo", "user"],
        default="workspace",
        help=(
            "Install into <workspace>/.codex by default. `repo` is a "
            "backward-compatible alias for `workspace`; user scope installs "
            "into the active Codex home."
        ),
    )
    args = parser.parse_args()

    root = Path(args.workspace_root).resolve()
    scope = "workspace" if args.scope == "repo" else args.scope
    source = root / "tooling" / "codex_hooks" / "hooks.json"
    if not source.exists():
        print(f"missing hook config: {source}")
        return 1

    codex_dir = root / ".codex" if scope == "workspace" else codex_home()
    if codex_dir.exists() and not codex_dir.is_dir():
        print(
            f"{codex_dir} exists but is not a directory. Move or remove the local file "
            "before installing hooks."
        )
        return 1

    codex_dir.mkdir(parents=True, exist_ok=True)
    if scope == "workspace":
        shutil.copyfile(source, codex_dir / "hooks.json")
    else:
        runtime_dir = codex_dir / "harness_hooks"
        _copy_runtime_scripts(root, runtime_dir)
        (codex_dir / "hooks.json").write_text(
            _load_hook_config(source, runtime_dir), encoding="utf-8"
        )

    config_path = codex_dir / "config.toml"
    _ensure_feature_flag(config_path)
    if scope == "workspace":
        _copy_rule_templates(root, codex_dir)
    else:
        _remove_rule_templates(codex_dir)

    print(f"installed Harness Codex hooks to {codex_dir} ({scope} scope)")
    print(
        "open /hooks in Codex and trust the Harness hooks before relying on "
        "them to run"
    )
    if scope == "user":
        print(f"copied hook runtime scripts to {codex_dir / 'harness_hooks'}")
        print("removed user-level Harness external review execpolicy rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
