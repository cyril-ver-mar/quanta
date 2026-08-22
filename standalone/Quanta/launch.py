#!/usr/bin/env python3
"""Launch Streamlit for Quanta."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    app = ROOT / "app.py"
    return subprocess.call(
        [sys.executable, "-m", "streamlit", "run", str(app), "--server.headless", "true"],
        cwd=str(ROOT),
    )


if __name__ == "__main__":
    raise SystemExit(main())
