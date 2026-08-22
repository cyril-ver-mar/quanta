"""L1 — app settings persisted as JSON under data/."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from src.utils.paths import CONFIG_PATH, ensure_runtime_dirs


@dataclass
class AppSettings:
    gaussian_exe: str = ""
    work_dir: str = ""
    scratch_dir: str = ""
    nproc: int = 4
    mem_mb: int = 1500
    language: str = "en"
    # ΔSCF XPS (gas phase)
    dscf_functional: str = "pbe"
    dscf_basis: str = "6-31g(d)"
    xps_fwhm_ev: float = 1.2
    xps_c1s_ref_ev: float = 284.3
    dscf_apply_c1s_shift: bool = True
    # Legacy Yamada keys (ignored if present in old settings.json)
    xps_scale: float = 1.024
    xps_apply_linear_map: bool = False
    xps_c1s_slope: float = 0.74
    xps_o1s_slope: float = 0.96
    xps_n1s_slope: float = 1.5

    @classmethod
    def load(cls, path: Path | None = None) -> "AppSettings":
        ensure_runtime_dirs()
        cfg = path or CONFIG_PATH
        if not cfg.exists():
            settings = cls()
            settings.save(cfg)
            return settings
        raw = json.loads(cfg.read_text(encoding="utf-8"))
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, path: Path | None = None) -> None:
        ensure_runtime_dirs()
        cfg = path or CONFIG_PATH
        cfg.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
