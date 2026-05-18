from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import subprocess
import time
from pathlib import Path
from typing import Any

from harness_contracts import CONTRACTS_PATH, repo_root

REQUIRED_HOOKS = {
    "UserPromptSubmit": "user_prompt_submit.py",
    "PreToolUse": "pre_tool_use_policy.py",
    "PostToolUse": "post_tool_use_markers.py",
    "Stop": "require_gate_ledger.py",
}
HOOKS_FEATURE = "hooks"
LEGACY_HOOKS_FEATURE = "codex_hooks"
REVIEW_REQUIRED_HOOK_STATUSES = {"untrusted", "modified"}
DEFAULT_TRUST_TIMEOUT_SECONDS = 15.0


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
    legacy_enabled = False
    in_features = False
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_features = stripped == "[features]"
            continue
        if not in_features:
            continue
        if stripped.startswith("#"):
            continue
        match = re.match(
            rf"^{HOOKS_FEATURE}\s*=\s*(true|false)\b",
            stripped,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1).lower() == "true"
        match = re.match(
            rf"^{LEGACY_HOOKS_FEATURE}\s*=\s*(true|false)\b",
            stripped,
            flags=re.IGNORECASE,
        )
        if match:
            legacy_enabled = match.group(1).lower() == "true"
    return legacy_enabled


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


def _read_json_rpc_response(
    process: subprocess.Popen[str],
    request_id: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    if process.stdout is None:
        raise RuntimeError("Codex app-server stdout is unavailable")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            stderr_text = _read_process_stderr(process)
            message = f"Codex app-server exited with code {exit_code}"
            if stderr_text:
                message = f"{message}: {stderr_text}"
            raise RuntimeError(message)
        ready, _, _ = select.select([process.stdout], [], [], 0.2)
        if not ready:
            continue
        line = process.stdout.readline()
        if not line:
            break
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("id") == request_id:
            return payload
    exit_code = process.poll()
    if exit_code is not None:
        stderr_text = _read_process_stderr(process)
        message = f"Codex app-server exited with code {exit_code}"
        if stderr_text:
            message = f"{message}: {stderr_text}"
        raise RuntimeError(message)
    raise TimeoutError(f"timed out waiting for Codex app-server response {request_id}")


def _write_json_message(
    process: subprocess.Popen[str],
    payload: dict[str, Any],
) -> None:
    if process.stdin is None:
        raise RuntimeError("Codex app-server stdin is unavailable")
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()


def _write_json_rpc_request(
    process: subprocess.Popen[str],
    request_id: int,
    method: str,
    params: dict[str, Any] | None,
) -> None:
    request: dict[str, Any] = {
        "id": request_id,
        "method": method,
    }
    if params is not None:
        request["params"] = params
    _write_json_message(process, request)


def _write_json_rpc_notification(
    process: subprocess.Popen[str],
    method: str,
    params: dict[str, Any] | None = None,
) -> None:
    notification: dict[str, Any] = {"method": method}
    if params is not None:
        notification["params"] = params
    _write_json_message(process, notification)


def _read_process_stderr(process: subprocess.Popen[str]) -> str:
    if process.stderr is None:
        return ""
    try:
        stderr_text = process.stderr.read()
    except OSError:
        return ""
    if not isinstance(stderr_text, str):
        return ""
    return stderr_text.strip().replace("\n", " | ")


def _fetch_hook_trust_entries_once(
    workspace_root: Path,
    codex_home_dir: Path,
    timeout_seconds: float = DEFAULT_TRUST_TIMEOUT_SECONDS,
) -> tuple[list[dict[str, Any]], str | None]:
    env = os.environ.copy()
    env["CODEX_HOME"] = codex_home_dir.as_posix()
    try:
        process = subprocess.Popen(
            ["codex", "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
    except FileNotFoundError:
        return [], "codex executable not found on PATH"

    try:
        _write_json_rpc_request(
            process,
            1,
            "initialize",
            {
                "clientInfo": {
                    "name": "harness-hook-status",
                    "title": "Harness Hook Status",
                    "version": "0.1.0",
                }
            },
        )
        init_response = _read_json_rpc_response(process, 1, timeout_seconds)
        if "error" in init_response:
            return [], f"Codex app-server initialize failed: {init_response['error']}"

        _write_json_rpc_notification(process, "initialized")

        _write_json_rpc_request(
            process,
            2,
            "hooks/list",
            {"cwds": [workspace_root.as_posix()]},
        )
        hooks_response = _read_json_rpc_response(process, 2, timeout_seconds)
        if "error" in hooks_response:
            return [], f"Codex hooks/list failed: {hooks_response['error']}"
        entries = hook_trust_entries_from_response(hooks_response)
        return entries, None
    except (BrokenPipeError, OSError, TimeoutError, RuntimeError) as exc:
        return [], f"Codex app-server trust check failed: {exc}"
    finally:
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass


def fetch_hook_trust_entries(
    workspace_root: Path,
    codex_home_dir: Path,
    timeout_seconds: float = DEFAULT_TRUST_TIMEOUT_SECONDS,
) -> tuple[list[dict[str, Any]], str | None]:
    return _fetch_hook_trust_entries_once(
        workspace_root, codex_home_dir, timeout_seconds
    )


def hook_trust_entries_from_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    result = response.get("result")
    if not isinstance(result, dict):
        return []
    entries = result.get("data")
    if not isinstance(entries, list):
        return []

    hooks: list[dict[str, Any]] = []
    for workspace_entry in entries:
        if not isinstance(workspace_entry, dict):
            continue
        cwd = workspace_entry.get("cwd")
        for hook in workspace_entry.get("hooks", []):
            if not isinstance(hook, dict):
                continue
            hooks.append(
                {
                    "cwd": cwd,
                    "event_name": hook.get("eventName"),
                    "source": hook.get("source"),
                    "source_path": hook.get("sourcePath"),
                    "command": hook.get("command"),
                    "enabled": hook.get("enabled"),
                    "current_hash": hook.get("currentHash"),
                    "trust_status": hook.get("trustStatus"),
                }
            )
    return hooks


def summarize_hook_trust(entries: list[dict[str, Any]]) -> dict[str, Any]:
    review_required = [
        entry
        for entry in entries
        if entry.get("enabled") is True
        and entry.get("trust_status") in REVIEW_REQUIRED_HOOK_STATUSES
    ]
    enabled_entries = [entry for entry in entries if entry.get("enabled") is True]
    return {
        "hook_trust_entries": entries,
        "hook_trust_ready": bool(enabled_entries) and not review_required,
        "hook_trust_review_required": review_required,
    }


def build_status(
    workspace_root: Path | str = ".",
    codex_dir: Path | None = None,
    include_trust_status: bool = False,
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

    status: dict[str, Any] = {
        "workspace_root": root.as_posix(),
        "harness_workspace": (root / CONTRACTS_PATH).exists(),
        "contract_path": (root / CONTRACTS_PATH).as_posix(),
        "codex_home": home.as_posix(),
        "user_config": user_config.as_posix(),
        "user_config_exists": user_config.exists(),
        "user_hooks_feature_enabled": user_feature_enabled,
        "user_codex_hooks_enabled": user_feature_enabled,
        "hooks_feature_enabled": hooks_enabled,
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
        "repo_hooks_feature_enabled": repo_feature_enabled,
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
    if include_trust_status:
        trust_entries, trust_error = fetch_hook_trust_entries(root, home)
        status["hook_trust_checked"] = True
        status["hook_trust_error"] = trust_error
        if trust_error is None:
            status.update(summarize_hook_trust(trust_entries))
        else:
            status.update(
                {
                    "hook_trust_entries": [],
                    "hook_trust_ready": False,
                    "hook_trust_review_required": [],
                }
            )
    else:
        status["hook_trust_checked"] = False
        status["hook_trust_error"] = None
        status["hook_trust_entries"] = []
        status["hook_trust_ready"] = None
        status["hook_trust_review_required"] = []
    return status


def render_status(status: dict[str, Any]) -> str:
    harness_state = "present" if status["harness_workspace"] else "missing"
    effective_flag = "enabled" if status["hooks_feature_enabled"] else "disabled"
    workspace_flag = (
        "enabled" if status["repo_hooks_feature_enabled"] else "disabled"
    )
    user_flag = "enabled" if status["user_hooks_feature_enabled"] else "disabled"
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
    if status.get("hook_trust_checked"):
        trust_error = status.get("hook_trust_error")
        if trust_error:
            lines.append(f"- hook trust status: NOT_RUN ({trust_error})")
        elif status.get("hook_trust_ready"):
            lines.append("- hook trust status: trusted")
        else:
            lines.append("- hook trust status: review required")
        review_required = status.get("hook_trust_review_required", [])
        if review_required:
            lines.append("- hooks requiring /hooks review:")
            for entry in review_required:
                lines.append(
                    "  - "
                    f"{entry.get('event_name')} "
                    f"{entry.get('trust_status')} "
                    f"{entry.get('current_hash')} "
                    f"({entry.get('command')})"
                )
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
    parser.add_argument(
        "--trust-status",
        action="store_true",
        help=(
            "Ask Codex app-server for hook trust state. This detects hooks that "
            "still need manual /hooks review."
        ),
    )
    args = parser.parse_args()

    status = build_status(
        Path(args.workspace_root), include_trust_status=args.trust_status
    )
    if args.json:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print(render_status(status))
    if not status["hook_install_ready"]:
        return 1
    if args.trust_status and not status["hook_trust_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
