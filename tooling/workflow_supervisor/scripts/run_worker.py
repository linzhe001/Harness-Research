#!/usr/bin/env python3
"""Workflow supervisor worker-result adapter.

V0 provides fail-closed validation for worker JSON outputs. Future slices may
extend this file to launch Skills, but supervisor state decisions must continue
to use the structured result contract instead of worker prose.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import workflow_ctl


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a workflow supervisor worker result JSON file."
    )
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--result", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    workspace_root = workflow_ctl.repo_root(args.workspace_root)
    try:
        data = workflow_ctl.load_json(Path(args.result))
        if not isinstance(data, dict):
            raise ValueError("worker result must be an object")
        errors = workflow_ctl.validate_worker_result(workspace_root, data)
    except ValueError as exc:
        errors = [str(exc)]

    if errors:
        if args.json:
            print(json.dumps({"ok": False, "errors": errors}, indent=2))
        else:
            for error in errors:
                print(error)
        return workflow_ctl.EXIT_INVALID_INPUT
    if args.json:
        print(json.dumps({"ok": True, "errors": []}, indent=2))
    else:
        print("PASS")
    return workflow_ctl.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
