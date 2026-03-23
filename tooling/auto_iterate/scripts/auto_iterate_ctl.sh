#!/usr/bin/env bash
# Thin shell wrapper for the auto-iterate controller CLI.
# Locates the repo root and Python, then delegates to the Python CLI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

exec python3 "$SCRIPT_DIR/auto_iterate_ctl.py" --workspace-root "$REPO_ROOT" "$@"
