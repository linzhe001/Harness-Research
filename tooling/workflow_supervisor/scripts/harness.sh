#!/usr/bin/env bash
# Human-facing shorthand for the Harness workflow supervisor CLI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_CTL="$SCRIPT_DIR/workflow_ctl.sh"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  harness.sh grill <init|round|packet> [grill options]
  harness.sh <prepare|build|iterate|release|change> [start options]
  harness.sh <status|pause|stop|resume|answer|approve|recover|tail> [options]
  harness.sh <validate-worker-result|validate-nodes|validate-postconditions|monitor-iterate> [options]

Segment commands are shorthand for:
  workflow_ctl.sh start --segment <segment> ...
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

command="$1"
shift

case "$command" in
  grill)
    exec python3 "$SCRIPT_DIR/../../grill/draft.py" \
      --workspace-root "$WORKSPACE_ROOT" "$@"
    ;;
  prepare|build|iterate|release|change)
    exec "$WORKFLOW_CTL" start --segment "$command" "$@"
    ;;
  status|pause|stop|resume|answer|approve|recover|tail|\
validate-worker-result|validate-nodes|validate-postconditions|monitor-iterate)
    exec "$WORKFLOW_CTL" "$command" "$@"
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    echo "unknown harness command: $command" >&2
    usage >&2
    exit 2
    ;;
esac
