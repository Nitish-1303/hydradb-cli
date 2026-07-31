#!/usr/bin/env bash
# Install HydraDB CLI from GitHub Releases.
# Usage:
#   curl -fsSL https://cli.hydradb.com/install | bash
#
# Optional:
#   HYDRADB_CLI_VERSION=0.1.1 curl -fsSL ... | bash
#   HYDRADB_CLI_FORCE=1 curl -fsSL ... | bash
#
# The wheel is downloaded from the GitHub release; its runtime dependencies
# (typer, httpx, rich, hydradb-sdk) still resolve from PyPI as usual.

set -euo pipefail

REPO="${HYDRADB_CLI_REPO:-usecortex/hydradb-cli}"
PACKAGE_NAME="${HYDRADB_CLI_PACKAGE:-hydradb-cli}"
COMMAND_NAME="${HYDRADB_CLI_COMMAND:-hydradb}"
VERSION="${HYDRADB_CLI_VERSION:-}"
FORCE="${HYDRADB_CLI_FORCE:-0}"

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

# Resolve the newest published release by following the /releases/latest
# redirect, which lands on /releases/tag/vX.Y.Z. This uses no API quota.
resolve_latest_version() {
  "$PYTHON" - "$REPO" <<'PY'
import sys
import urllib.request

repo = sys.argv[1]
url = f"https://github.com/{repo}/releases/latest"
try:
    with urllib.request.urlopen(url, timeout=30) as response:
        final = response.url
except Exception as exc:  # noqa: BLE001 - any failure means "could not resolve"
    print(f"  reason: {exc}", file=sys.stderr)
    raise SystemExit(1) from None

tag = final.rstrip("/").rsplit("/", 1)[-1]
if not tag or tag == "latest":
    print(f"error: no published release found at {url}", file=sys.stderr)
    raise SystemExit(1)

print(tag[1:] if tag.startswith("v") else tag)
PY
}

if [ -z "$VERSION" ]; then
  info "Resolving latest release of ${REPO}"
  VERSION="$(resolve_latest_version || true)"
  if [ -z "$VERSION" ]; then
    fail "Could not resolve the latest release. Pin one with HYDRADB_CLI_VERSION=<x.y.z> and try again."
  fi
fi

# setuptools normalises the distribution name in artifact filenames.
DIST_NAME="$(printf '%s' "$PACKAGE_NAME" | tr '-' '_')"
WHEEL_NAME="${DIST_NAME}-${VERSION}-py3-none-any.whl"
WHEEL_URL="https://github.com/${REPO}/releases/download/v${VERSION}/${WHEEL_NAME}"

info "Installing ${PACKAGE_NAME} ${VERSION}"

if ! "$PYTHON" - "$WHEEL_URL" <<'PY'
import sys
import urllib.request

request = urllib.request.Request(sys.argv[1], method="HEAD")
try:
    with urllib.request.urlopen(request, timeout=30):
        pass
except Exception as exc:  # noqa: BLE001 - any failure means "not downloadable"
    print(f"  reason: {exc}", file=sys.stderr)
    raise SystemExit(1) from None
PY
then
  fail "No wheel for version ${VERSION} at ${WHEEL_URL}. Check https://github.com/${REPO}/releases for available versions."
fi

install_with_pipx() {
  if ! command -v pipx >/dev/null 2>&1; then
    return 1
  fi

  info "Installing with pipx"

  # The spec is a URL, so pipx cannot resolve an upgrade from it; a forced
  # install is the only path that reliably replaces an existing version.
  if [ "$FORCE" = "1" ] || pipx list 2>/dev/null | grep -q "package ${PACKAGE_NAME} "; then
    pipx install --force "$WHEEL_URL"
  else
    pipx install "$WHEEL_URL"
  fi

  return 0
}

install_with_pip_user() {
  info "pipx not found. Installing with pip --user"

  "$PYTHON" -m pip install --user --upgrade pip >/dev/null

  if [ "$FORCE" = "1" ]; then
    "$PYTHON" -m pip install --user --force-reinstall "$WHEEL_URL"
  else
    "$PYTHON" -m pip install --user --upgrade "$WHEEL_URL"
  fi
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
