#!/usr/bin/env bash
# Download Quanta application files into $ROOT when missing (standalone bootstrap).
# Sourced by install.sh — expects ROOT, ok, fail, step, C_* set.

fetch_quanta_app() {
  if [[ -f "$ROOT/app.py" ]] && [[ -d "$ROOT/src" ]] && [[ -d "$ROOT/pages" ]]; then
    return 0
  fi

  local repo="cyril-ver-mar/quanta"
  if [[ -f "$ROOT/GITHUB_REPO" ]]; then
    repo="$(tr -d '[:space:]' < "$ROOT/GITHUB_REPO" | head -1)"
  fi

  local tag="${QUANTA_TAG:-}"
  if [[ -z "$tag" ]]; then
    if [[ -f "$ROOT/VERSION" ]]; then
      tag="v$(tr -d '[:space:]' < "$ROOT/VERSION")"
    else
      tag="v1.0.2"
    fi
  fi
  [[ "$tag" == v* ]] || tag="v${tag}"

  local tmp
  tmp="$(mktemp -d)"
  local src=""

  if command -v git >/dev/null 2>&1; then
    if git clone --depth 1 --branch "$tag" "https://github.com/${repo}.git" "$tmp/repo" 2>/dev/null; then
      if [[ -f "$tmp/repo/app.py" ]]; then
        src="$tmp/repo"
      fi
    fi
  fi

  if [[ -z "$src" ]] && command -v curl >/dev/null 2>&1; then
    local zip="$tmp/src.zip"
    # Prefer a Release asset named *standalone*; fall back to source tag archive.
    local asset_url=""
    if command -v python3 >/dev/null 2>&1; then
      asset_url="$(python3 - <<PY
import json, urllib.request
url = "https://api.github.com/repos/${repo}/releases/tags/${tag}"
try:
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    for a in data.get("assets") or []:
        name = (a.get("name") or "").lower()
        if name.endswith(".zip") and "standalone" in name:
            print(a.get("browser_download_url") or "")
            break
except Exception:
    pass
PY
)"
    fi
    if [[ -n "$asset_url" ]] && curl -fsSL "$asset_url" -o "$zip"; then
      :
    elif curl -fsSL "https://github.com/${repo}/archive/refs/tags/${tag}.zip" -o "$zip"; then
      :
    else
      zip=""
    fi
    if [[ -n "$zip" ]] && [[ -f "$zip" ]] && command -v unzip >/dev/null 2>&1; then
      unzip -q "$zip" -d "$tmp"
      local extracted
      extracted="$(find "$tmp" -maxdepth 3 -type f -name 'app.py' | head -1)"
      if [[ -n "$extracted" ]]; then
        src="$(dirname "$extracted")"
      fi
    fi
  fi

  if [[ -z "$src" ]] || [[ ! -f "$src/app.py" ]]; then
    rm -rf "$tmp"
    fail "Could not download Quanta application" \
      "Check internet access and tag ${tag} on GitHub (${repo})" \
      "Or clone the full repo: git clone https://github.com/${repo}.git" \
      "Or run install from the project root that contains app.py and src/"
    return 1
  fi

  local item
  for item in app.py launch.py pages src run.sh run.bat VERSION requirements.txt requirements-runtime.txt .streamlit GITHUB_REPO; do
    if [[ -e "$src/$item" ]]; then
      if [[ -d "$src/$item" ]]; then
        rm -rf "$ROOT/$item"
        cp -R "$src/$item" "$ROOT/"
      else
        cp "$src/$item" "$ROOT/"
      fi
    fi
  done

  mkdir -p "$ROOT/data/jobs" "$ROOT/data/compounds" "$ROOT/data/logs" "$ROOT/exports"
  chmod +x "$ROOT/run.sh" 2>/dev/null || true
  chmod +x "$ROOT/install.sh" 2>/dev/null || true
  rm -rf "$tmp"
  ok "Downloaded Quanta ${tag} from GitHub"
}
