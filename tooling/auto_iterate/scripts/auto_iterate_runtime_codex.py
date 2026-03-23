#!/usr/bin/env python3
"""Standalone Codex runtime adapter entry point.

Reads a round brief, validates it, renders a prompt, invokes Codex,
and writes a result file.  Used by the controller but also independently
testable.

Usage:
    auto_iterate_runtime_codex.py \\
        --brief <brief.json> \\
        --result <result.json> \\
        --account <account_id> \\
        --codex-home <path> \\
        --workspace-root <path> \\
        [--timeout <seconds>] [--grace <seconds>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the auto_iterate package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from auto_iterate.state import load_json, atomic_write_json
from auto_iterate.runtime import (
    BriefValidationError,
    PhaseSupervisor,
    validate_brief,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Codex runtime adapter")
    parser.add_argument("--brief", required=True, help="Path to round brief JSON")
    parser.add_argument("--result", required=True, help="Path to write result JSON")
    parser.add_argument("--account", required=True, help="Account ID")
    parser.add_argument("--codex-home", required=True, help="CODEX_HOME path")
    parser.add_argument("--workspace-root", required=True, help="Project workspace root")
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout in seconds")
    parser.add_argument("--grace", type=int, default=30, help="Grace period before SIGKILL")
    parser.add_argument("--dry-run", action="store_true", help="Skip real Codex invocation")
    args = parser.parse_args(argv)

    try:
        brief = load_json(args.brief)
        validate_brief(brief)
    except BriefValidationError as e:
        print(f"ERROR: Invalid brief: {e}", file=sys.stderr)
        return 200  # Incompatible brief — frozen exit code per 01§6.2
    except Exception as e:
        print(f"ERROR: Cannot load brief: {e}", file=sys.stderr)
        return 1

    runtime_dir = Path(args.result).parent
    supervisor = PhaseSupervisor(
        workspace_root=args.workspace_root,
        runtime_dir=runtime_dir,
    )

    result = supervisor.run_phase(
        brief=brief,
        account_id=args.account,
        codex_home=args.codex_home,
        timeout_sec=args.timeout,
        terminate_grace_sec=args.grace,
        dry_run=args.dry_run,
    )

    atomic_write_json(args.result, result)
    return result.get("exit_code", 0)


if __name__ == "__main__":
    sys.exit(main())
