"""Application version helpers (Layer 1).

Single source of truth: repository root ``VERSION`` file (semver).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_version() -> str:
    path = ROOT / "VERSION"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"
    return text.splitlines()[0].strip() if text else "0.0.0"


def version_label(app_name: str = "Quanta") -> str:
    return f"{app_name} {get_version()}"
