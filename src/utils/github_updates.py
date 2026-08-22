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
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from src.utils.paths import ROOT
from src.utils.version import get_version

logger = logging.getLogger(__name__)

USER_AGENT = "Quanta-updater"
API_TIMEOUT_S = 8.0
PREFERRED_ASSET_SUBSTR = ("standalone", "quanta")

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


def classify_github_error(exc: BaseException) -> tuple[str, str]:
    """Map a network/parse exception to ``(error_code, technical_detail)``."""
    if isinstance(exc, urllib.error.HTTPError):
        code = int(exc.code)
        reason = str(exc.reason or "")
        detail = f"HTTP {code}" + (f": {reason}" if reason else "")
        if code == 404:
            return ERR_HTTP_404, detail
        if code == 403:
            headers = getattr(exc, "headers", None)
            remaining = ""
            if headers is not None:
                remaining = str(headers.get("X-RateLimit-Remaining") or "")
            if remaining == "0":
                return ERR_HTTP_403, f"{detail} (rate limit)"
            return ERR_HTTP_403, detail
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
) -> tuple[Optional[ReleaseInfo], Optional[str], str]:
    """Return ``(release, error_code, detail)``. ``error_code`` is None on success."""
    repo = _normalize_repo(repo) or ""
    if not repo:
        return None, ERR_NOT_CONFIGURED, "empty repo id"
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # classified below — never raise to UI
        code, detail = classify_github_error(exc)
        logger.warning("GitHub release check failed for %s [%s]: %s", repo, code, detail)
        return None, code, detail
    if not isinstance(payload, dict):
        return None, ERR_BAD_RESPONSE, "latest release payload is not an object"
    tag = str(payload.get("tag_name") or "")
    if not tag:
        return None, ERR_BAD_RESPONSE, "latest release has no tag_name"
    version = tag.lstrip("vV")
    zip_url, zip_name = _pick_zip_asset(list(payload.get("assets") or []))
    html_url = str(payload.get("html_url") or f"https://github.com/{repo}/releases/latest")
    return (
        ReleaseInfo(
            tag=tag,
            version=version,
            html_url=html_url,
            zip_url=zip_url,
            zip_name=zip_name,
            name=str(payload.get("name") or tag),
        ),
        None,
        "",
    )


@dataclass(frozen=True)
class UpdateStatus:
    configured: bool
    local_version: str
    update_available: bool
    latest: Optional[ReleaseInfo]
    repo: Optional[str]
    message: str = ""
    error_code: Optional[str] = None


def check_for_update(local_version: Optional[str] = None, root: Optional[Path] = None) -> UpdateStatus:
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
    latest, err, detail = fetch_latest_release_outcome(repo)
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
