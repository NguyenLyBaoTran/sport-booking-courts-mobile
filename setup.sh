#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN=""
FOUND_PYTHON="false"

for candidate in python3 python; do
  if ! command -v "$candidate" >/dev/null 2>&1; then
    continue
  fi
  FOUND_PYTHON="true"
  if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v "$candidate")"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ "$FOUND_PYTHON" == "true" ]]; then
    printf '%s\n' "Python was found, but version 3.10 or newer is required. Install Python 3.10+ and retry." >&2
  else
    printf '%s\n' "Python 3 was not found. Install Python 3.10+ and Docker Engine with Compose v2, then retry." >&2
  fi
  exit 1
fi

exec "$PYTHON_BIN" "$ROOT_DIR/setup_config.py" "$@"
