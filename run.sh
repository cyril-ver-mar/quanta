#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d venv ]]; then
  echo "Missing venv. Run ./install.sh first."
  exit 1
fi
# shellcheck disable=SC1091
source venv/bin/activate
exec python launch.py
