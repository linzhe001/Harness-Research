#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BIN_DIR="${BIN_DIR:-${HOME}/.local/bin}"
INSTALL_SHELL_INIT=0
SHELL_INIT_MARKER_START="# >>> harness remote-control commands >>>"
SHELL_INIT_MARKER_END="# <<< harness remote-control commands <<<"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --shell-init)
      INSTALL_SHELL_INIT=1
      shift
      ;;
    -h|--help)
      cat <<EOF
Usage: tooling/remote_control/scripts/install_user_commands.sh [--shell-init]

Options:
  --shell-init   Ensure ~/.profile and ~/.bashrc add ~/.local/bin to PATH
EOF
      exit 0
      ;;
    *)
      echo "install_user_commands: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

install_link() {
  local src="$1"
  local name="$2"
  if [[ ! -x "$src" ]]; then
    echo "install_user_commands: source command is missing or not executable: $src" >&2
    exit 1
  fi
  ln -sfn "$src" "${BIN_DIR}/${name}"
  echo "Installed ${name} -> ${src}"
}

ensure_shell_init_file() {
  local target_file="$1"
  local path_dir="$2"
  mkdir -p "$(dirname "${target_file}")"
  touch "${target_file}"
  if grep -Fq "${SHELL_INIT_MARKER_START}" "${target_file}"; then
    echo "Shell init already managed by harness marker: ${target_file}"
    return 0
  fi
  if grep -Fq "${path_dir}" "${target_file}"; then
    echo "Shell init already references ${path_dir}: ${target_file}"
    return 0
  fi
  if [[ "${path_dir}" == "${HOME}/.local/bin" ]] && grep -Eq '(\$HOME|~|/[^[:space:]]+)/\.local/bin' "${target_file}"; then
    echo "Shell init already references ~/.local/bin: ${target_file}"
    return 0
  fi
  if grep -Eq '(^|[^#[:alnum:]_])(codex_all|cw)\(\)[[:space:]]*\{' "${target_file}"; then
    echo "Shell init already defines codex_all/cw function: ${target_file}"
    return 0
  fi
  if grep -Eq "^[[:space:]]*alias[[:space:]]+(codex_all|cw|ca)=" "${target_file}"; then
    echo "Shell init already defines codex_all/cw alias: ${target_file}"
    return 0
  fi
  cat >>"${target_file}" <<EOF

${SHELL_INIT_MARKER_START}
if [ -d "${path_dir}" ]; then
    case ":\$PATH:" in
        *:"${path_dir}":*) ;;
        *) PATH="${path_dir}:\$PATH" ;;
    esac
fi
${SHELL_INIT_MARKER_END}
EOF
  echo "Updated ${target_file}"
}

mkdir -p "$BIN_DIR"

install_link "${REPO_ROOT}/tooling/remote_control/bin/codex_all" "codex_all"
install_link "${REPO_ROOT}/tooling/remote_control/bin/cw" "cw"

if [[ "${INSTALL_SHELL_INIT}" -eq 1 ]]; then
  ensure_shell_init_file "${HOME}/.profile" "${BIN_DIR}"
  ensure_shell_init_file "${HOME}/.bashrc" "${BIN_DIR}"
fi

cat <<EOF

Command install completed.

Installed commands:
  ${BIN_DIR}/codex_all
  ${BIN_DIR}/cw

If the current shell still cannot find them, run:
  export PATH="${BIN_DIR}:\$PATH"

For future shells, rerun with:
  tooling/remote_control/scripts/install_user_commands.sh --shell-init

This appends a minimal PATH block to ~/.profile and ~/.bashrc if missing.
EOF
