#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
CC_CONNECT_DIR="${REPO_ROOT}/Reference_tool_repo/cc-connect"
LOCAL_GO="${REPO_ROOT}/tooling/remote_control/vendor/go/bin/go"
TARGET_DIR="${REPO_ROOT}/tooling/remote_control/vendor/bin"
TARGET_BIN="${TARGET_DIR}/cc-connect-harness-patched-linux-amd64"

if [[ -x "${LOCAL_GO}" ]]; then
  GO_BIN="${LOCAL_GO}"
elif command -v go >/dev/null 2>&1; then
  GO_BIN="$(command -v go)"
else
  echo "go not found. Install Go 1.25 first, or place it at tooling/remote_control/vendor/go." >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}"

export PATH="$(dirname "${GO_BIN}"):${PATH}"
export GOMODCACHE="${GOMODCACHE:-/tmp/cc-connect-gomod}"
export GOPATH="${GOPATH:-/tmp/cc-connect-gopath}"
export GOCACHE="${GOCACHE:-/tmp/cc-connect-gocache}"

pushd "${CC_CONNECT_DIR}" >/dev/null
make build AGENTS=claudecode,codex PLATFORMS_INCLUDE=feishu
install -m 755 cc-connect "${TARGET_BIN}.new"
mv -f "${TARGET_BIN}.new" "${TARGET_BIN}"
popd >/dev/null

echo "Patched cc-connect installed to:"
echo "  ${TARGET_BIN}"
echo
echo "Restart with:"
echo "  tooling/remote_control/bin/cc-connect -config tooling/remote_control/config/cc_connect.local.toml"
