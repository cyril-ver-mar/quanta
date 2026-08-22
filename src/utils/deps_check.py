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


if __name__ == "__main__":
    exit_if_missing_cli()
