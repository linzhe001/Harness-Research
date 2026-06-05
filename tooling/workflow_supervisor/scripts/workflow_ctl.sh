#!/usr/bin/env bash
# Thin shell wrapper for the Harness workflow supervisor CLI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

exec python3 "$SCRIPT_DIR/workflow_ctl.py" --workspace-root "$REPO_ROOT" "$@"
