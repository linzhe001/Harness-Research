from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness_contracts import (
    active_contract,
    load_contracts,
    missing_reads,
    repo_root,
    validate_contract_files,
)
from hook_status import build_status, render_status


def check_hooks_config(root: Path) -> list[str]:
    errors: list[str] = []
    hooks_path = root / "tooling" / "codex_hooks" / "hooks.json"
    if not hooks_path.exists():
        return [f"missing hooks config: {hooks_path}"]
    data = json.loads(hooks_path.read_text(encoding="utf-8"))
    for event, groups in data.get("hooks", {}).items():
        for group_index, group in enumerate(groups):
            for hook_index, hook in enumerate(group.get("hooks", [])):
                command = hook.get("command", "")
                if "tooling/codex_hooks/" not in command:
                    errors.append(
                        f"{event}[{group_index}].hooks[{hook_index}]: "
                        "command does not reference tooling/codex_hooks"
                    )
                script = (
                    command.split("tooling/codex_hooks/", 1)[-1]
                    .split('"', 1)[0]
                    .split(" ", 1)[0]
                )
                if script and not (root / "tooling" / "codex_hooks" / script).exists():
                    errors.append(
                        f"{event}[{group_index}].hooks[{hook_index}]: "
                        f"missing script {script}"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Harness skill contracts and hook runtime state."
    )
    parser.add_argument(
        "--workspace-root", default=".", help="Repository root or subdirectory."
    )
    parser.add_argument(
        "--list", action="store_true", help="List configured skill contracts."
    )
    parser.add_argument(
        "--check-read-ledger",
        action="store_true",
        help="Check current active skill read ledger.",
    )
    parser.add_argument(
        "--hook-status",
        action="store_true",
        help="Print user/repo Codex hook installation status.",
    )
    args = parser.parse_args()

    root = repo_root(Path(args.workspace_root))
    if args.hook_status:
        print(render_status(build_status(root)))
        return 0

    if args.list:
        print(json.dumps([c["skill"] for c in load_contracts(root)], indent=2))
        return 0

    errors = validate_contract_files(root)
    errors.extend(check_hooks_config(root))
    if args.check_read_ledger:
        contract = active_contract(root)
        if contract:
            errors.extend(
                f"missing read: {path}" for path in missing_reads(root, contract)
            )

    if errors:
        for error in errors:
            print(error)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
