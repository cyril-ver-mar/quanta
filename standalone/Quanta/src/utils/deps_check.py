"""Runtime dependency checks (Layer 1).

Validates imports required to run Quanta (not dev/test tools).
Used by install scripts, run/launch, and app.py on startup.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from typing import Iterable, List, Sequence

# import_name → pip package name (for pip install hints)
RUNTIME_DEPS: tuple[tuple[str, str], ...] = (
    ("streamlit", "streamlit"),
    ("rdkit", "rdkit"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("matplotlib", "matplotlib"),
    ("plotly", "plotly"),
    ("py3Dmol", "py3Dmol"),
)


@dataclass(frozen=True)
class MissingDep:
    import_name: str
    pip_name: str
    error: str


def check_runtime_deps(deps: Sequence[tuple[str, str]] = RUNTIME_DEPS) -> List[MissingDep]:
    """Return missing/failed imports (empty list = OK)."""
    missing: List[MissingDep] = []
    for import_name, pip_name in deps:
        try:
            importlib.import_module(import_name)
        except Exception as exc:  # noqa: BLE001
            missing.append(MissingDep(import_name, pip_name, str(exc)))
    return missing


def format_cli_message(missing: Iterable[MissingDep]) -> str:
    lines = [
        "ERROR: Missing Python packages required by Quanta:",
        "",
    ]
    for item in missing:
        lines.append(f"  · {item.import_name} ({item.pip_name}): {item.error}")
    lines.extend(
        [
            "",
            "How to fix:",
            "  · macOS/Linux: ./install.sh  or  ./run.sh",
            "  · Windows:     install.bat  or  run.bat",
            "  · Or activate venv and run: pip install -r requirements.txt",
        ]
    )
    return "\n".join(lines)


def exit_if_missing_cli() -> None:
    missing = check_runtime_deps()
    if missing:
        print(format_cli_message(missing), file=sys.stderr)
        raise SystemExit(1)
    print("ok — all runtime dependencies importable")


def ensure_runtime_deps() -> list[MissingDep]:
    """Install from requirements if missing, then re-check."""
    from pathlib import Path

    missing = check_runtime_deps()
    if not missing:
        return []
    root = Path(__file__).resolve().parents[2]
    req = root / "requirements-runtime.txt"
    if not req.is_file():
        req = root / "requirements.txt"
    if not req.is_file():
        return missing
    import subprocess

    print(f"Installing missing packages from {req.name} …")
    code = subprocess.call([sys.executable, "-m", "pip", "install", "-r", str(req)])
    if code != 0:
        return check_runtime_deps() or missing
    return check_runtime_deps()


if __name__ == "__main__":
    if "--ensure" in sys.argv:
        still = ensure_runtime_deps()
        if still:
            print(format_cli_message(still), file=sys.stderr)
            raise SystemExit(1)
        print("ok — all runtime dependencies importable")
    else:
        exit_if_missing_cli()
