"""Load optional secrets from app-root ``SECRETS`` file (Layer 1).

Trusted installs may place a ``SECRETS`` file next to ``app.py`` and copy it
between machines. Values are never logged. Environment variables always win
over the file (so CI / shell overrides work).

File format (``KEY=value``, ``#`` comments, blank lines ignored)::

    # GitHub personal access token — raises API rate limit for update checks
    GITHUB_TOKEN=ghp_xxxxxxxx

Supported keys (aliases accepted):

- ``GITHUB_TOKEN`` / ``QUANTA_GITHUB_TOKEN`` / ``GH_TOKEN``
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from src.utils.paths import ROOT

logger = logging.getLogger(__name__)

SECRETS_FILENAME = "SECRETS"
SECRETS_EXAMPLE_FILENAME = "SECRETS.example"

# Keys that may appear in SECRETS (canonical name → accepted aliases).
_SECRET_ALIASES: dict[str, tuple[str, ...]] = {
    "GITHUB_TOKEN": ("GITHUB_TOKEN", "QUANTA_GITHUB_TOKEN", "GH_TOKEN"),
}


def secrets_path(root: Path | None = None) -> Path:
    return (root or ROOT) / SECRETS_FILENAME


def secrets_example_path(root: Path | None = None) -> Path:
    return (root or ROOT) / SECRETS_EXAMPLE_FILENAME


def secrets_file_exists(root: Path | None = None) -> bool:
    return secrets_path(root).is_file()


def parse_secrets_text(text: str) -> dict[str, str]:
    """Parse KEY=value lines; strip quotes; skip comments/blank lines."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and value:
            out[key] = value
    return out


def _read_secrets_file(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        logger.warning("Could not read secrets file %s: %s", path, exc)
        return {}
    return parse_secrets_text(text)


@lru_cache(maxsize=8)
def load_secrets(root: str | None = None) -> Mapping[str, str]:
    """Load SECRETS from disk once (cached). Pass ``root`` as str for cache key."""
    base = Path(root) if root else ROOT
    path = secrets_path(base)
    if not path.is_file():
        return {}
    data = _read_secrets_file(path)
    if data:
        # Never log values — only which keys were present.
        logger.info("Loaded secrets file (%d key(s)): %s", len(data), ", ".join(sorted(data)))
    return data


def clear_secrets_cache() -> None:
    load_secrets.cache_clear()


def get_secret(name: str, *, root: Path | None = None, default: str = "") -> str:
    """Resolve a secret: process env first, then SECRETS file aliases."""
    aliases = _SECRET_ALIASES.get(name, (name,))
    for key in aliases:
        env_val = (os.environ.get(key) or "").strip()
        if env_val:
            return env_val

    file_map = load_secrets(str(root) if root else None)
    for key in aliases:
        val = (file_map.get(key) or "").strip()
        if val:
            return val
    return default


def github_token(*, root: Path | None = None) -> str:
    """Token for GitHub API (update checks). Empty if not configured."""
    return get_secret("GITHUB_TOKEN", root=root)


def secrets_status(*, root: Path | None = None) -> dict[str, object]:
    """Safe status for Settings UI (no secret values)."""
    path = secrets_path(root)
    exists = path.is_file()
    keys: list[str] = []
    if exists:
        keys = sorted(_read_secrets_file(path).keys())
    token_from_env = bool(
        (os.environ.get("QUANTA_GITHUB_TOKEN") or "").strip()
        or (os.environ.get("GITHUB_TOKEN") or "").strip()
        or (os.environ.get("GH_TOKEN") or "").strip()
    )
    token_from_file = bool(github_token(root=root)) and not token_from_env
    return {
        "path": str(path),
        "exists": exists,
        "keys": keys,
        "github_token_configured": bool(github_token(root=root)),
        "github_token_from_env": token_from_env,
        "github_token_from_file": token_from_file,
    }
