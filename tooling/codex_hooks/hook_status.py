from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from harness_contracts import CONTRACTS_PATH, repo_root

REQUIRED_HOOKS = {
    "UserPromptSubmit": "user_prompt_submit.py",
    "PreToolUse": "pre_tool_use_policy.py",
    "PostToolUse": "post_tool_use_markers.py",
    "Stop": "require_gate_ledger.py",
}


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def file_kind(path: Path) -> str:
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    if path.exists():
        return "other"
    return "missing"


def feature_enabled(config_path: Path) -> bool:
    if not config_path.exists():
        return False
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        match = re.match(
            r"^codex_hooks\s*=\s*(true|false)\b", stripped, flags=re.IGNORECASE
        )
        if match:
            return match.group(1).lower() == "true"
    return False


def hook_commands(hooks_path: Path) -> list[str]:
    if not hooks_path.exists():
        return []
    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    commands: list[str] = []
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command")
                if isinstance(command, str):
                    commands.append(command)
    return commands


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hook_errors(
    hooks_path: Path,
    expected_runtime_dir: Path | None = None,
    source_runtime_dir: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if not hooks_path.exists():
        return [f"missing hooks config: {hooks_path}"]
    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid hooks JSON: {exc}"]

    for event, script in REQUIRED_HOOKS.items():
        groups = data.get("hooks", {}).get(event)
        if not groups:
            errors.append(f"missing hook event: {event}")
            continue
        commands = [
            hook.get("command", "")
            for group in groups
            for hook in group.get("hooks", [])
            if isinstance(hook.get("command"), str)
        ]
        if not any(script in command for command in commands):
            errors.append(f"{event}: missing script reference {script}")
        if expected_runtime_dir is not None:
            expected_fragment = (expected_runtime_dir / script).as_posix()
            if not any(expected_fragment in command for command in commands):
                errors.append(
                    f"{event}: command does not point to installed runtime "
                    f"{expected_fragment}"
                )

    if expected_runtime_dir is not None:
        for script in set(REQUIRED_HOOKS.values()) | {"harness_contracts.py"}:
            installed = expected_runtime_dir / script
            if not installed.exists():
                errors.append(f"missing installed runtime script: {installed}")
                continue
            if source_runtime_dir is not None:
                source = source_runtime_dir / script
                if source.exists() and sha256(installed) != sha256(source):
                    errors.append(f"stale installed runtime script: {installed}")
    return errors


def build_status(
    workspace_root: Path | str = ".", codex_dir: Path | None = None
) -> dict[str, Any]:
    root = repo_root(workspace_root)
    home = (codex_dir or codex_home()).resolve()
    user_config = home / "config.toml"
    user_hooks = home / "hooks.json"
    user_runtime = home / "harness_hooks"
    source_runtime = root / "tooling" / "codex_hooks"
    repo_codex = root / ".codex"
    repo_config = repo_codex / "config.toml"
    repo_hooks = repo_codex / "hooks.json"
    user_hook_errors = (
        hook_errors(user_hooks, user_runtime, source_runtime)
        if user_hooks.exists()
        else []
    )
    repo_hook_errors = hook_errors(repo_hooks) if repo_hooks.exists() else []
    user_hooks_ok = user_hooks.exists() and not user_hook_errors
    repo_hooks_ok = repo_hooks.exists() and not repo_hook_errors
    user_feature_enabled = feature_enabled(user_config)
    repo_feature_enabled = feature_enabled(repo_config)
    hooks_enabled = user_feature_enabled or repo_feature_enabled
    ready = hooks_enabled and (user_hooks_ok or repo_hooks_ok)

    return {
        "workspace_root": root.as_posix(),
        "harness_workspace": (root / CONTRACTS_PATH).exists(),
        "contract_path": (root / CONTRACTS_PATH).as_posix(),
        "codex_home": home.as_posix(),
        "user_config": user_config.as_posix(),
        "user_config_exists": user_config.exists(),
        "user_codex_hooks_enabled": user_feature_enabled,
        "codex_hooks_enabled": hooks_enabled,
        "user_hooks": user_hooks.as_posix(),
        "user_hooks_exists": user_hooks.exists(),
        "user_runtime": user_runtime.as_posix(),
        "user_runtime_exists": user_runtime.is_dir(),
        "user_hook_errors": user_hook_errors,
        "user_hook_commands": hook_commands(user_hooks),
        "repo_codex": repo_codex.as_posix(),
        "repo_codex_kind": file_kind(repo_codex),
        "repo_config": repo_config.as_posix(),
        "repo_config_exists": repo_config.exists(),
        "repo_codex_hooks_enabled": repo_feature_enabled,
        "repo_hooks": repo_hooks.as_posix(),
        "repo_hooks_exists": repo_hooks.exists(),
        "repo_hook_errors": repo_hook_errors,
        "repo_hook_commands": hook_commands(repo_hooks),
        "active_hook_source": "workspace"
        if repo_hooks_ok
        else ("user" if user_hooks_ok else "none"),
        "hook_install_ready": ready,
        "workspace_policy_effect": "active"
        if (root / CONTRACTS_PATH).exists()
        else "no-op",
    }


def render_status(status: dict[str, Any]) -> str:
    harness_state = "present" if status["harness_workspace"] else "missing"
    effective_flag = "enabled" if status["codex_hooks_enabled"] else "disabled"
    workspace_flag = (
        "enabled" if status["repo_codex_hooks_enabled"] else "disabled"
    )
    user_flag = "enabled" if status["user_codex_hooks_enabled"] else "disabled"
    user_hooks = "present" if status["user_hooks_exists"] else "missing"
    user_runtime = "present" if status["user_runtime_exists"] else "missing"
    repo_hooks = "present" if status["repo_hooks_exists"] else "missing"
    lines = [
        "Harness Codex hook status",
        f"- workspace: {status['workspace_root']}",
        f"- Harness contracts: {harness_state} ({status['contract_path']})",
        f"- policy effect here: {status['workspace_policy_effect']}",
        f"- Codex home: {status['codex_home']}",
        f"- effective feature flag: {effective_flag}",
        f"- active hook source: {status['active_hook_source']}",
        f"- workspace feature flag: {workspace_flag} ({status['repo_config']})",
        f"- user feature flag: {user_flag} ({status['user_config']})",
        f"- user hooks: {user_hooks} ({status['user_hooks']})",
        f"- user runtime: {user_runtime} ({status['user_runtime']})",
        f"- repo .codex: {status['repo_codex_kind']} ({status['repo_codex']})",
        f"- repo hooks: {repo_hooks} ({status['repo_hooks']})",
    ]
    user_errors = status.get("user_hook_errors", [])
    repo_errors = status.get("repo_hook_errors", [])
    if user_errors:
        lines.append("- user hook issues:")
        lines.extend(f"  - {error}" for error in user_errors)
    if repo_errors:
        lines.append("- repo hook issues:")
        lines.extend(f"  - {error}" for error in repo_errors)
    if status.get("user_hook_commands"):
        lines.append("- user hook commands:")
        lines.extend(f"  - {command}" for command in status["user_hook_commands"])
    if status.get("repo_hook_commands"):
        lines.append("- workspace hook commands:")
        lines.extend(f"  - {command}" for command in status["repo_hook_commands"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report Harness Codex hook installation status."
    )
    parser.add_argument(
        "--workspace-root", default=".", help="Repository root or subdirectory."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable status.",
    )
    args = parser.parse_args()

    status = build_status(Path(args.workspace_root))
    if args.json:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print(render_status(status))
    if not status["hook_install_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
