#!/usr/bin/env bash
# Quanta one-file bootstrapper — downloads the latest GitHub Release zip
# into the folder you choose (not necessarily where this script lives).
set -euo pipefail

REPO="${QUANTA_GITHUB_REPO:-cyril-ver-mar/quanta}"
APP_DIR_NAME="Quanta"
PRESERVE=("data" "exports" "venv" ".venv")

START_CWD="$(pwd)"

if [[ -t 1 ]] && [[ "${NO_COLOR:-}" == "" ]]; then
  C_ACCENT=$'\033[38;2;217;119;87m'
  C_OK=$'\033[38;2;61;154;110m'
  C_ERR=$'\033[38;2;196;74;74m'
  C_WARN=$'\033[38;2;196;140;40m'
  C_DIM=$'\033[2m'
  C_BOLD=$'\033[1m'
  C_RESET=$'\033[0m'
else
  C_ACCENT=""; C_OK=""; C_ERR=""; C_WARN=""; C_DIM=""; C_BOLD=""; C_RESET=""
fi

ok() { printf '  %s✓%s %s\n' "$C_OK" "$C_RESET" "$*"; }
fail() {
  echo
  printf '%s╭─ Error ──────────────────────────────────────╮%s\n' "$C_ERR" "$C_RESET"
  printf '%s│%s %s\n' "$C_ERR" "$C_RESET" "$1"
  shift || true
  for line in "$@"; do
    printf '  %s·%s %s\n' "$C_ACCENT" "$C_RESET" "$line"
  done
  echo
  exit 1
}

banner() {
  printf '%s\n' "${C_ACCENT}${C_BOLD}"
  cat <<'EOF'
  ╭──────────────────────────────────────────────╮
  │   Quanta                                     │
  │   Bootstrap — download latest from GitHub    │
  ╰──────────────────────────────────────────────╯
EOF
  printf '%s\n' "${C_RESET}"
}

banner

DEFAULT_DIR="$START_CWD"
echo
printf '%s%sInstall folder%s\n' "$C_WARN" "$C_BOLD" "$C_RESET"
echo "  App will be created as:  <folder>/${APP_DIR_NAME}"
echo "  Default (current directory):"
printf '  %s%s%s\n' "$C_BOLD" "$DEFAULT_DIR" "$C_RESET"
echo
printf '  Enter path (or press Enter for default): '
read -r ENTERED_DIR
if [[ -z "${ENTERED_DIR}" ]]; then
  SCRIPT_DIR="$DEFAULT_DIR"
else
  SCRIPT_DIR="$ENTERED_DIR"
fi
SCRIPT_DIR="${SCRIPT_DIR/#\~/$HOME}"
SCRIPT_DIR="$(cd "$SCRIPT_DIR" 2>/dev/null && pwd)" || {
  mkdir -p "$ENTERED_DIR" 2>/dev/null || true
  SCRIPT_DIR="$(cd "${ENTERED_DIR/#\~/$HOME}" && pwd)" || fail "Cannot use install path: ${ENTERED_DIR}"
}
case "$SCRIPT_DIR" in
  /tmp|/*/Temp|/*/temp)
    fail "Temp folder is not allowed as install path" "Choose a normal folder, e.g. ~/Quanta"
    ;;
esac

echo
printf '%s%sWARNING%s\n' "$C_WARN" "$C_BOLD" "$C_RESET"
echo
echo "  This script will download and install Quanta into:"
printf '  %s%s%s\n' "$C_BOLD" "$SCRIPT_DIR" "$C_RESET"
echo "  App folder:"
printf '  %s%s/%s%s\n' "$C_BOLD" "$SCRIPT_DIR" "$APP_DIR_NAME" "$C_RESET"
echo
echo "  • Creates / updates:  ${APP_DIR_NAME}/"
echo "  • Keeps (if present):  data/, exports/, venv/"
echo "  • Needs: network + Python 3.11 later for ./install.sh"
echo
printf '  Type %sYES%s to continue (anything else cancels): ' "$C_BOLD" "$C_RESET"
read -r CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
  echo
  echo "  Cancelled."
  echo
  exit 0
fi

mkdir -p "$SCRIPT_DIR"
cd "$SCRIPT_DIR"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1" "Install it, then re-run this script"
}

need_cmd curl
need_cmd unzip

TMP="$(mktemp -d "${TMPDIR:-/tmp}/quanta_boot.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo
printf '%s[1/4]%s Resolve latest GitHub Release…\n' "$C_ACCENT" "$C_RESET"
API="https://api.github.com/repos/${REPO}/releases/latest"
JSON="$TMP/release.json"
HTTP_CODE="$(curl -sS -L -A "Quanta-bootstrap" -H "Accept: application/vnd.github+json" \
  -o "$JSON" -w "%{http_code}" "$API" || true)"
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "GitHub API failed (HTTP $HTTP_CODE)" \
    "Check https://github.com/${REPO}/releases" \
    "Repo must be public, or set QUANTA_GITHUB_REPO=owner/name"
fi

TAG="$(grep -m1 '"tag_name"' "$JSON" | sed 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
ZIP_URL=""
ZIP_NAME=""

while IFS= read -r line; do
  url="$(printf '%s' "$line" | sed -n 's/.*"browser_download_url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
  name="$(printf '%s' "$line" | sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
  [[ -z "$url" || -z "$name" ]] && continue
  [[ "$name" != *.zip ]] && continue
  if [[ "$name" == *[Ss]tandalone* ]]; then
    ZIP_URL="$url"
    ZIP_NAME="$name"
    break
  fi
  if [[ -z "$ZIP_URL" && "$name" == *[Qq]uanta* ]]; then
    ZIP_URL="$url"
    ZIP_NAME="$name"
  fi
  if [[ -z "$ZIP_URL" ]]; then
    ZIP_URL="$url"
    ZIP_NAME="$name"
  fi
done < <(grep -E '"name"|"browser_download_url"' "$JSON" || true)

if [[ -z "$ZIP_URL" ]]; then
  TAG_FALLBACK="$(curl -sS -L -A "Quanta-bootstrap" -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${REPO}/tags?per_page=1" | grep -m1 '"name"' | sed 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
  if [[ -n "$TAG_FALLBACK" ]]; then
    TAG="$TAG_FALLBACK"
    ZIP_URL="https://github.com/${REPO}/archive/refs/tags/${TAG}.zip"
    ZIP_NAME="${TAG}.zip"
    ok "No release zip — using source archive for tag ${TAG}"
  else
    fail "No .zip asset on the latest release" \
      "Check https://github.com/${REPO}/releases" \
      "Or set QUANTA_GITHUB_REPO=owner/name"
  fi
fi
ok "Latest release: ${TAG:-unknown}"
ok "Asset: ${ZIP_NAME}"

echo
printf '%s[2/4]%s Download package…\n' "$C_ACCENT" "$C_RESET"
ZIP_PATH="$TMP/pkg.zip"
curl -sS -L -A "Quanta-bootstrap" -o "$ZIP_PATH" "$ZIP_URL" \
  || fail "Download failed" "Check network / GitHub status"
ok "Downloaded ($(wc -c < "$ZIP_PATH" | tr -d ' ') bytes)"

echo
printf '%s[3/4]%s Unpack into %s/%s …\n' "$C_ACCENT" "$C_RESET" "$SCRIPT_DIR" "$APP_DIR_NAME"
EXTRACT="$TMP/extract"
mkdir -p "$EXTRACT"
unzip -q "$ZIP_PATH" -d "$EXTRACT"

SRC=""
while IFS= read -r -d '' candidate; do
  if [[ -f "$candidate/app.py" && -f "$candidate/VERSION" ]]; then
    SRC="$candidate"
    break
  fi
done < <(find "$EXTRACT" -type d -path "*/standalone/Quanta" -print0 2>/dev/null)

if [[ -z "$SRC" ]]; then
  while IFS= read -r -d '' app; do
    d="$(dirname "$app")"
    if [[ -f "$d/VERSION" ]]; then
      SRC="$d"
      break
    fi
  done < <(find "$EXTRACT" -name app.py -print0 2>/dev/null)
fi

if [[ -z "$SRC" ]]; then
  fail "Zip does not contain app.py + VERSION"
fi

DEST="$SCRIPT_DIR/$APP_DIR_NAME"
mkdir -p "$DEST"

HOLD="$TMP/preserve"
mkdir -p "$HOLD"
for name in "${PRESERVE[@]}"; do
  if [[ -e "$DEST/$name" ]]; then
    mv "$DEST/$name" "$HOLD/$name"
    ok "Preserved $name"
  fi
done

find "$DEST" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
cp -R "$SRC"/. "$DEST"/

for name in "${PRESERVE[@]}"; do
  if [[ -e "$HOLD/$name" ]]; then
    rm -rf "$DEST/$name"
    mv "$HOLD/$name" "$DEST/$name"
  fi
done
ok "Installed to $DEST"
if [[ -f "$DEST/VERSION" ]]; then
  ok "VERSION $(tr -d '\r' < "$DEST/VERSION" | head -n1)"
fi

echo
printf '%s[4/4]%s Next steps\n' "$C_ACCENT" "$C_RESET"
echo
printf '%sHow to finish setup and run%s\n' "$C_BOLD" "$C_RESET"
echo
echo "  1. Open Terminal"
echo "  2. Go to the app folder:"
printf '     %scd "%s"%s\n' "$C_BOLD" "$DEST" "$C_RESET"
echo "  3. First time only — install Python deps:"
printf '     %s./install.sh%s\n' "$C_BOLD" "$C_RESET"
echo "  4. Start the app:"
printf '     %s./run.sh%s\n' "$C_BOLD" "$C_RESET"
echo
echo "  Browser: http://localhost:8501  (or http://127.0.0.1:8501)"
echo
ok "Bootstrap finished."
echo
