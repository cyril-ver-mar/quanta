#!/usr/bin/env bash
# Quanta installer — clean terminal UX
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -t 1 ]] && [[ "${NO_COLOR:-}" == "" ]]; then
  C_ACCENT=$'\033[38;2;217;119;87m'
  C_OK=$'\033[38;2;61;154;110m'
  C_ERR=$'\033[38;2;196;74;74m'
  C_DIM=$'\033[2m'
  C_BOLD=$'\033[1m'
  C_RESET=$'\033[0m'
else
  C_ACCENT=""; C_OK=""; C_ERR=""; C_DIM=""; C_BOLD=""; C_RESET=""
fi

banner() {
  printf '%s\n' "${C_ACCENT}${C_BOLD}"
  cat <<'EOF'
  ╭──────────────────────────────────────────────╮
  │                                              │
  │   Quanta                                     │
  │   Setup from scratch                         │
  │                                              │
  ╰──────────────────────────────────────────────╯
EOF
  printf '%s\n' "${C_RESET}${C_DIM}  Gaussian DFT · ΔSCF XPS workflow${C_RESET}"
  echo
}

step() {
  local n="$1" total="$2" msg="$3"
  printf '%s[%s/%s]%s %s%s%s\n' "$C_ACCENT" "$n" "$total" "$C_RESET" "$C_BOLD" "$msg" "$C_RESET"
}

ok() { printf '  %s✓%s %s\n' "$C_OK" "$C_RESET" "$*"; }

fail() {
  local title="$1"
  shift
  echo
  printf '%s╭─ Error ──────────────────────────────────────╮%s\n' "$C_ERR" "$C_RESET"
  printf '%s│%s %-44s %s│%s\n' "$C_ERR" "$C_RESET" "$title" "$C_ERR" "$C_RESET"
  printf '%s╰──────────────────────────────────────────────╯%s\n' "$C_ERR" "$C_RESET"
  if [[ "$#" -gt 0 ]]; then
    echo
    printf '%sHow to fix%s\n' "$C_BOLD" "$C_RESET"
    for line in "$@"; do
      printf '  %s·%s %s\n' "$C_ACCENT" "$C_RESET" "$line"
    done
  fi
  echo
  exit 1
}

tip() {
  printf '%s  ── next ──%s\n' "$C_DIM" "$C_RESET"
  printf '  %s%s%s\n' "$C_BOLD" "$*" "$C_RESET"
  echo
  printf '%s  If the browser does not open by itself:%s\n' "$C_BOLD" "$C_RESET"
  printf '  %s·%s open http://localhost:8501\n' "$C_ACCENT" "$C_RESET"
  printf '  %s·%s or http://127.0.0.1:8501\n' "$C_ACCENT" "$C_RESET"
  echo
}

TOTAL=6
banner

step 1 "$TOTAL" "Locate Python 3.11"
PY=""
for cand in python3.11 python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    ver="$("$cand" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || true)"
    if [[ "$ver" == "3.11" ]]; then
      PY="$cand"
      break
    fi
  fi
done
if [[ -z "$PY" ]]; then
  fail "Python 3.11 was not found on PATH" \
    "macOS: brew install python@3.11" \
    "Ubuntu: sudo apt install python3.11 python3.11-venv" \
    "Then re-run: ./install.sh" \
    "Check: python3.11 --version"
fi
ok "Using $($PY --version 2>&1 | head -1) ($PY)"

step 2 "$TOTAL" "Check venv module"
if ! "$PY" -c "import venv" 2>/dev/null; then
  fail "Python venv module is missing" \
    "Ubuntu/Debian: sudo apt install python3.11-venv" \
    "Then re-run: ./install.sh"
fi
ok "venv module available"

step 3 "$TOTAL" "Create / refresh virtualenv"
if [[ ! -d venv ]]; then
  if ! "$PY" -m venv venv; then
    fail "Could not create ./venv" \
      "Delete a broken venv folder if it exists: rm -rf venv" \
      "Ensure write permission in: $ROOT" \
      "Re-run: ./install.sh"
  fi
  ok "Created ./venv"
else
  ok "Reusing existing ./venv"
fi

# shellcheck disable=SC1091
source venv/bin/activate
VPY="$ROOT/venv/bin/python"
VPIP="$ROOT/venv/bin/pip"
if [[ ! -x "$VPY" ]]; then
  fail "venv/bin/python is missing or not executable" \
    "rm -rf venv && ./install.sh"
fi

step 4 "$TOTAL" "Install Python packages"
if [[ ! -f requirements.txt ]]; then
  fail "requirements.txt not found" \
    "Run this script from the Quanta project root" \
    "Expected file: $ROOT/requirements.txt"
fi
if ! "$VPY" -m pip install --upgrade pip >/tmp/quanta_pip_up.log 2>&1; then
  fail "Failed to upgrade pip" \
    "See /tmp/quanta_pip_up.log" \
    "Check network / proxy settings" \
    "Retry: ./install.sh"
fi
ok "pip upgraded"
if ! "$VPIP" install -r requirements.txt; then
  fail "pip install -r requirements.txt failed" \
    "Check network access to PyPI" \
    "RDKit may take a few minutes on first install" \
    "Try: source venv/bin/activate && pip install -r requirements.txt"
fi
ok "Dependencies installed"

step 5 "$TOTAL" "Create data folders & smoke-test imports"
mkdir -p data/jobs data/compounds data/logs exports
if ! "$VPY" -c "
import importlib
mods = ('streamlit','rdkit','pandas','numpy','matplotlib','plotly','py3Dmol')
for m in mods:
    importlib.import_module(m)
"; then
  fail "Dependency import smoke-test failed" \
    "Re-run ./install.sh after fixing pip errors" \
    "Activate venv and run: pip install -r requirements.txt"
fi
ok "All runtime packages import OK (streamlit, rdkit, …)"
ok "Folders: data/jobs, data/compounds, exports"

step 6 "$TOTAL" "Finish"
ok "Install complete"
echo
tip "./run.sh"
printf '%s  Windows: run.bat · Settings → Gaussian path (Windows run mode)%s\n' "$C_DIM" "$C_RESET"
echo

# Drop installer so end users are not confused by a second setup script.
echo
printf '  Removing install.sh (no longer needed)...\n'
(
  sleep 1
  rm -f "$ROOT/install.sh"
) &

