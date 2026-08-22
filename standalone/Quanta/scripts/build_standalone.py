#!/usr/bin/env python3
"""Build end-user standalone copy of Quanta.

Usage (from project root):
  python scripts/build_standalone.py

Output:
  standalone/Quanta/
"""

from __future__ import annotations

import shutil
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "standalone" / "Quanta"

COPY_TREES = ["pages", "src", "fixtures"]
COPY_FILES = [
    "app.py",
    "launch.py",
    "install.sh",
    "install.bat",
    "run.sh",
    "run.bat",
    "VERSION",
    "requirements-runtime.txt",
]

COPY_SCRIPT_FILES = ["scripts/fetch_app.sh"]

SKIP_NAME_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".DS_Store",
    ".cursor",
}

USER_README = """# Quanta

Gaussian 09 DFT jobs and **ΔSCF XPS** analysis (gas-phase molecules).

## Install & run

### macOS / Linux

```bash
./install.sh
./run.sh
```

### Windows

```bat
install.bat
run.bat
```

Open in browser: http://localhost:8501  
If the browser does not open automatically, paste the URL manually.

## Workflow

1. **Settings** — Gaussian path (Windows), functional, FWHM  
2. **Compounds** — import mol2 / pdb / sdf  
3. **Work review** — check 3D structure  
4. **Jobs** — create ΔSCF workflow  
5. **Queue** — run Gaussian steps  
6. **Results** — binding energies and spectra  

Requires **Python 3.11**.

## Secrets (optional)

Copy `SECRETS.example` → `SECRETS` next to `app.py` and add:

```
GITHUB_TOKEN=ghp_your_token
```

This raises GitHub update-check rate limits. Keep `SECRETS` private; you may copy it between trusted machines. In-app updates preserve `SECRETS`.
"""


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(*SKIP_NAME_PARTS, "*.pyc"),
    )


def _chmod_exec(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> None:
    if OUT.exists():
        for child in OUT.iterdir():
            if child.name == "venv":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        OUT.mkdir(parents=True)

    for rel in COPY_TREES:
        _copy_tree(ROOT / rel, OUT / rel)

    for rel in COPY_FILES:
        src = ROOT / rel
        if not src.exists():
            raise SystemExit(f"Missing required file: {rel}")
        shutil.copy2(src, OUT / rel)

    for rel in COPY_SCRIPT_FILES:
        src = ROOT / rel
        if src.is_file():
            dst = OUT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    github_repo = ROOT / "GITHUB_REPO"
    if not github_repo.is_file():
        github_repo = ROOT / "GITHUB_REPO.example"
    if github_repo.is_file():
        repo_line = ""
        for line in github_repo.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            if text.endswith(".git"):
                text = text[:-4]
            if "/" in text and " " not in text:
                repo_line = text
                break
        if repo_line:
            (OUT / "GITHUB_REPO").write_text(f"{repo_line}\n", encoding="utf-8")

    secrets_example = ROOT / "SECRETS.example"
    if secrets_example.is_file():
        shutil.copy2(secrets_example, OUT / "SECRETS.example")
    # Never copy a real SECRETS file into the distributable.

    runtime_req = ROOT / "requirements-runtime.txt"
    if runtime_req.is_file():
        shutil.copy2(runtime_req, OUT / "requirements.txt")
        shutil.copy2(runtime_req, OUT / "requirements-runtime.txt")

    st_src = ROOT / ".streamlit" / "config.toml"
    if st_src.is_file():
        st_dir = OUT / ".streamlit"
        st_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(st_src, st_dir / "config.toml")

    for rel in ("data/jobs", "data/compounds", "data/logs", "exports"):
        p = OUT / rel
        p.mkdir(parents=True, exist_ok=True)
        (p / ".gitkeep").write_text("", encoding="utf-8")

    (OUT / "README.md").write_text(USER_README, encoding="utf-8")

    for script in ("install.sh", "run.sh"):
        _chmod_exec(OUT / script)

    bad: list[str] = []
    for path in OUT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".md", ".txt", ".toml", ".sh", ".bat"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "/Users/" in text or "C:\\Users\\" in text or "kirillverbilo" in text:
            bad.append(str(path.relative_to(OUT)))
    if bad:
        raise SystemExit("Hardcoded user paths in standalone build:\n  " + "\n  ".join(bad))

    print(f"Standalone build ready: {OUT}")
    print("Zip standalone/Quanta/ for distribution, or commit the folder to git.")


if __name__ == "__main__":
    main()
