#!/usr/bin/env bash
# Thin shell wrapper for the Codex runtime adapter.
# Locates the repo root and Python, then delegates to the Python script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use the Python from PATH (conda/venv expected to be active).
exec python3 "$SCRIPT_DIR/auto_iterate_runtime_codex.py" "$@"
