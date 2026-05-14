#!/usr/bin/env bash
# Install HydraDB CLI from PyPI.
# Usage:
#   curl -fsSL https://cli.hydradb.com/install | bash
#
# Optional:
#   HYDRADB_CLI_VERSION=0.1.0 curl -fsSL ... | bash
#   HYDRADB_CLI_FORCE=1 curl -fsSL ... | bash

set -euo pipefail

PACKAGE_NAME="${HYDRADB_CLI_PACKAGE:-hydradb-cli}"
COMMAND_NAME="${HYDRADB_CLI_COMMAND:-hydradb}"
VERSION="${HYDRADB_CLI_VERSION:-}"
FORCE="${HYDRADB_CLI_FORCE:-0}"

if [ -n "$VERSION" ]; then
  PACKAGE_SPEC="${PACKAGE_NAME}==${VERSION}"
else
  PACKAGE_SPEC="${PACKAGE_NAME}"
fi

info() {
  printf '\033[1;34m[hydradb]\033[0m %s\n' "$1"
}

warn() {
  printf '\033[1;33m[hydradb]\033[0m %s\n' "$1"
}

fail() {
  printf '\033[1;31m[hydradb]\033[0m %s\n' "$1" >&2
  exit 1
}

find_python() {
  for candidate in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
      then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done

  return 1
}

PYTHON="$(find_python || true)"
if [ -z "$PYTHON" ]; then
  fail "Python 3.10 or higher is required. Install Python 3.10+ and run this again."
fi

PYTHON_VERSION="$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
info "Using Python ${PYTHON_VERSION}"

install_with_pipx() {
  if ! command -v pipx >/dev/null 2>&1; then
    return 1
  fi

  info "Installing with pipx"

  if pipx list 2>/dev/null | grep -q "package ${PACKAGE_NAME} "; then
    if [ "$FORCE" = "1" ]; then
      pipx uninstall "$PACKAGE_NAME" >/dev/null 2>&1 || true
      pipx install "$PACKAGE_SPEC"
    else
      pipx upgrade "$PACKAGE_NAME" || pipx install --force "$PACKAGE_SPEC"
    fi
  else
    pipx install "$PACKAGE_SPEC"
  fi

  return 0
}

install_with_pip_user() {
  info "pipx not found. Installing with pip --user"

  "$PYTHON" -m pip install --user --upgrade pip >/dev/null
  "$PYTHON" -m pip install --user --upgrade "$PACKAGE_SPEC"
}

if ! install_with_pipx; then
  install_with_pip_user
fi

USER_BIN="$($PYTHON - <<'PY'
import os
import site
import sys
if os.name == "nt":
    print(os.path.join(site.USER_BASE, "Scripts"))
else:
    print(os.path.join(site.USER_BASE, "bin"))
PY
)"

if command -v "$COMMAND_NAME" >/dev/null 2>&1; then
  info "Installed successfully"
  "$COMMAND_NAME" --version || true
  exit 0
fi

if [ -x "${USER_BIN}/${COMMAND_NAME}" ]; then
  info "Installed successfully"
  "${USER_BIN}/${COMMAND_NAME}" --version || true
  warn "${USER_BIN} is not on your PATH. Add this line to your shell profile:"
  printf '\n  export PATH="%s:$PATH"\n\n' "$USER_BIN"
  exit 0
fi

fail "Installation finished, but '${COMMAND_NAME}' was not found. Check your Python scripts directory or pipx path."
