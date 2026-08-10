#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3.11}"
if [[ ! -d venv ]]; then
  "$PYTHON" -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo "Install complete. Run: ./run.sh"
