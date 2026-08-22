#!/usr/bin/env bash
# Quanta launcher
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  echo "Missing venv. Run ./install.sh first."
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate
VPY="$ROOT/venv/bin/python"

if [[ ! -f app.py ]]; then
  echo "app.py not found — run ./install.sh to download the application."
  exit 1
fi

if ! PYTHONPATH="$ROOT" "$VPY" -m src.utils.deps_check --ensure; then
  echo "Package check failed — run ./install.sh"
  exit 1
fi

exec "$VPY" launch.py
