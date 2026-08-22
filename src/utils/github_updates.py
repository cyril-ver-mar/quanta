"""GitHub Releases update check (Layer 1 — no Streamlit).

Public API only. Configure repo via (first match wins):

1. Environment ``QUANTA_GITHUB_REPO`` (``owner/name``)
2. Root file ``GITHUB_REPO`` (one line ``owner/name``)
3. ``git remote get-url origin`` when available
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from src.utils.paths import DATA_DIR, ROOT
from src.utils.version import get_version

logger = logging.getLogger(__name__)

USER_AGENT = "Quanta-updater"
API_TIMEOUT_S = 8.0
PREFERRED_ASSET_SUBSTR = ("standalone", "quanta")
CACHE_PATH = DATA_DIR / "update_check_cache.json"
CACHE_TTL_OK_S = 3600.0  # 1 h — avoid hammering GitHub on every page
CACHE_TTL_RATE_LIMIT_S = 900.0  # 15 min backoff after 403

ERR_NOT_CONFIGURED = "not_configured"
ERR_NETWORK = "network"
ERR_TIMEOUT = "timeout"
ERR_SSL = "ssl"
ERR_HTTP_404 = "http_404"
ERR_HTTP_403 = "http_403"
ERR_HTTP = "http"
ERR_BAD_RESPONSE = "bad_response"
ERR_UNEXPECTED = "unexpected"


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    version: str
    html_url: str
    zip_url: Optional[str]
    zip_name: Optional[str]
    name: str = ""


def parse_semver(text: str) -> tuple[int, int, int]:
    """Parse ``1.2.3`` or ``v1.2.3``; unknown → (0, 0, 0)."""
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def is_newer(remote: str, local: str) -> bool:
    return parse_semver(remote) > parse_semver(local)


def _normalize_repo(raw: str) -> Optional[str]:
    text = (raw or "").strip()
    if not text or text.startswith("#"):
        return None
    if text.endswith(".git"):
        text = text[:-4]
    if "github.com" in text:
        path = urlparse(text).path.strip("/")
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return None
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text):
        return text
    return None


def _read_repo_file(repo_file: Path) -> Optional[str]:
    """Return first valid ``owner/name`` from a GITHUB_REPO file (skip comments)."""
    try:
        # utf-8-sig strips BOM added by some Windows editors (Notepad)
        text = repo_file.read_text(encoding="utf-8-sig")
    except OSError as exc:
        logger.warning("Could not read GITHUB_REPO: %s", exc)
        return None
    for line in text.splitlines():
        parsed = _normalize_repo(line)
        if parsed:
            return parsed
    return None


def resolve_github_repo(root: Optional[Path] = None) -> Optional[str]:
    """Return ``owner/name`` or None when not configured."""
    env = _normalize_repo(os.environ.get("QUANTA_GITHUB_REPO", ""))
    if env:
        return env

    base = root or ROOT
    repo_file = base / "GITHUB_REPO"
    if repo_file.is_file():
        parsed = _read_repo_file(repo_file)
        if parsed:
            return parsed

    try:
        out = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=str(base),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        parsed = _normalize_repo(out)
        if parsed:
            return parsed
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _pick_zip_asset(assets: list[dict]) -> tuple[Optional[str], Optional[str]]:
    zips = [
        a
        for a in assets
        if isinstance(a, dict)
        and str(a.get("name", "")).lower().endswith(".zip")
        and a.get("browser_download_url")
    ]
    if not zips:
        return None, None

    def score(asset: dict) -> tuple[int, str]:
        name = str(asset.get("name", "")).lower()
        pref = 0
        for i, needle in enumerate(PREFERRED_ASSET_SUBSTR):
            if needle in name:
                pref = len(PREFERRED_ASSET_SUBSTR) - i
                break
        return (-pref, name)

    best = sorted(zips, key=score)[0]
    return str(best["browser_download_url"]), str(best.get("name") or "update.zip")


def _github_token() -> str:
    from src.utils.secrets import github_token

    return github_token()


def _api_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = _github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _rate_limit_reset_note(headers: Any) -> str:
    if headers is None:
        return ""
    reset_raw = headers.get("X-RateLimit-Reset")
    if not reset_raw:
        return ""
    try:
        reset_dt = datetime.fromtimestamp(int(reset_raw), tz=timezone.utc)
        return f" Resets ~{reset_dt.strftime('%H:%M')} UTC."
    except (TypeError, ValueError, OSError):
        return ""


def _load_disk_cache(repo: str) -> tuple[Optional[ReleaseInfo], Optional[str], str] | None:
    if not CACHE_PATH.is_file():
        return None
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("repo") != repo:
        return None
    fetched_at = float(payload.get("fetched_at") or 0)
    ttl = float(payload.get("ttl_s") or 0)
    if ttl <= 0 or (time.time() - fetched_at) > ttl:
        return None
    if payload.get("ok"):
        rel = payload.get("release") or {}
        return (
            ReleaseInfo(
                tag=str(rel.get("tag") or ""),
                version=str(rel.get("version") or ""),
                html_url=str(rel.get("html_url") or ""),
                zip_url=rel.get("zip_url"),
                zip_name=rel.get("zip_name"),
                name=str(rel.get("name") or ""),
            ),
            None,
            "",
        )
    return None, payload.get("error_code"), str(payload.get("detail") or "")


def _save_disk_cache(
    repo: str,
    *,
    release: ReleaseInfo | None,
    error_code: str | None,
    detail: str,
    ttl_s: float,
) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "repo": repo,
            "fetched_at": time.time(),
            "ttl_s": ttl_s,
            "ok": release is not None and error_code is None,
        }
        if release is not None:
            payload["release"] = {
                "tag": release.tag,
                "version": release.version,
                "html_url": release.html_url,
                "zip_url": release.zip_url,
                "zip_name": release.zip_name,
                "name": release.name,
            }
        else:
            payload["error_code"] = error_code
            payload["detail"] = detail
        CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write update cache: %s", exc)


def clear_update_cache() -> None:
    """Drop cached GitHub release response (e.g. before manual re-check)."""
    try:
        if CACHE_PATH.is_file():
            CACHE_PATH.unlink()
    except OSError:
        pass


def classify_github_error(exc: BaseException) -> tuple[str, str]:
    """Map a network/parse exception to ``(error_code, technical_detail)``."""
    if isinstance(exc, urllib.error.HTTPError):
        code = int(exc.code)
        reason = str(exc.reason or "")
        detail = f"HTTP {code}" + (f": {reason}" if reason else "")
        reset_note = _rate_limit_reset_note(getattr(exc, "headers", None))
        if code == 404:
            return ERR_HTTP_404, detail
        if code == 403:
            headers = getattr(exc, "headers", None)
            remaining = ""
            if headers is not None:
                remaining = str(headers.get("X-RateLimit-Remaining") or "")
            lower = reason.lower()
            if remaining == "0" or "rate limit" in lower:
                return ERR_HTTP_403, f"{detail} (rate limit).{reset_note}".strip()
            return ERR_HTTP_403, detail + reset_note
        return ERR_HTTP, detail

    if isinstance(exc, TimeoutError) or isinstance(exc, socket.timeout):
        return ERR_TIMEOUT, str(exc) or "timed out"

    if isinstance(exc, ssl.SSLError):
        return ERR_SSL, str(exc)

    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return ERR_TIMEOUT, str(reason)
        if isinstance(reason, ssl.SSLError):
            return ERR_SSL, str(reason)
        text = str(reason or exc).lower()
        if "timed out" in text or "timeout" in text:
            return ERR_TIMEOUT, str(reason or exc)
        if "ssl" in text or "certificate" in text:
            return ERR_SSL, str(reason or exc)
        return ERR_NETWORK, str(reason or exc)

    if isinstance(exc, json.JSONDecodeError):
        return ERR_BAD_RESPONSE, str(exc)

    if isinstance(exc, OSError):
        text = str(exc).lower()
        if "timed out" in text:
            return ERR_TIMEOUT, str(exc)
        if "ssl" in text or "certificate" in text:
            return ERR_SSL, str(exc)
        return ERR_NETWORK, str(exc)

    return ERR_UNEXPECTED, str(exc)


def fetch_latest_release(repo: str) -> Optional[ReleaseInfo]:
    """GET ``/repos/{repo}/releases/latest``. Returns None on any failure."""
    release, _code, _detail = fetch_latest_release_outcome(repo)
    return release


def fetch_latest_release_outcome(
    repo: str,
    *,
    use_cache: bool = True,
) -> tuple[Optional[ReleaseInfo], Optional[str], str]:
    """Return ``(release, error_code, detail)``. ``error_code`` is None on success."""
    repo = _normalize_repo(repo) or ""
    if not repo:
        return None, ERR_NOT_CONFIGURED, "empty repo id"

    if use_cache:
        cached = _load_disk_cache(repo)
        if cached is not None:
            logger.debug("Using cached GitHub release check for %s", repo)
            return cached

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers=_api_headers(), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # classified below — never raise to UI
        code, detail = classify_github_error(exc)
        logger.warning("GitHub release check failed for %s [%s]: %s", repo, code, detail)
        ttl = CACHE_TTL_RATE_LIMIT_S if code == ERR_HTTP_403 else 60.0
        _save_disk_cache(repo, release=None, error_code=code, detail=detail, ttl_s=ttl)
        return None, code, detail
    if not isinstance(payload, dict):
        detail = "latest release payload is not an object"
        _save_disk_cache(repo, release=None, error_code=ERR_BAD_RESPONSE, detail=detail, ttl_s=60.0)
        return None, ERR_BAD_RESPONSE, detail
    tag = str(payload.get("tag_name") or "")
    if not tag:
        detail = "latest release has no tag_name"
        _save_disk_cache(repo, release=None, error_code=ERR_BAD_RESPONSE, detail=detail, ttl_s=60.0)
        return None, ERR_BAD_RESPONSE, detail
    version = tag.lstrip("vV")
    zip_url, zip_name = _pick_zip_asset(list(payload.get("assets") or []))
    html_url = str(payload.get("html_url") or f"https://github.com/{repo}/releases/latest")
    release = ReleaseInfo(
        tag=tag,
        version=version,
        html_url=html_url,
        zip_url=zip_url,
        zip_name=zip_name,
        name=str(payload.get("name") or tag),
    )
    _save_disk_cache(repo, release=release, error_code=None, detail="", ttl_s=CACHE_TTL_OK_S)
    return release, None, ""


@dataclass(frozen=True)
class UpdateStatus:
    configured: bool
    local_version: str
    update_available: bool
    latest: Optional[ReleaseInfo]
    repo: Optional[str]
    message: str = ""
    error_code: Optional[str] = None


def check_for_update(
    local_version: Optional[str] = None,
    root: Optional[Path] = None,
    *,
    use_cache: bool = True,
) -> UpdateStatus:
    """Compare local VERSION to GitHub latest release (network; typed errors)."""
    local = (local_version or get_version()).strip()
    repo = resolve_github_repo(root)
    if not repo:
        return UpdateStatus(
            configured=False,
            local_version=local,
            update_available=False,
            latest=None,
            repo=None,
            message="GitHub repo not configured",
            error_code=ERR_NOT_CONFIGURED,
        )
    latest, err, detail = fetch_latest_release_outcome(repo, use_cache=use_cache)
    if latest is None:
        return UpdateStatus(
            configured=True,
            local_version=local,
            update_available=False,
            latest=None,
            repo=repo,
            message=detail or "Could not fetch latest release",
            error_code=err or ERR_UNEXPECTED,
        )
    newer = is_newer(latest.version, local)
    return UpdateStatus(
        configured=True,
        local_version=local,
        update_available=newer,
        latest=latest,
        repo=repo,
        message="update available" if newer else "up to date",
        error_code=None,
    )
