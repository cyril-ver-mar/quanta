"""Quanta entrypoint — page config, session defaults, home."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.connection import init_db
from src.ui.components.sidebar import render_sidebar
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.paths import ensure_runtime_dirs

SESSION_DEFAULTS = {
    "settings_loaded": False,
    "selected_job_id": None,
    "selected_compound_id": None,
}

st.set_page_config(page_title="Quanta", layout="wide", initial_sidebar_state="expanded")

for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

ensure_runtime_dirs()
init_db()
settings = AppSettings.load()
settings = render_sidebar(settings)

st.title(t("app_title", settings.language))
st.caption(t("app_tagline", settings.language))

st.markdown(
    """
### Workflow (ΔSCF XPS)
1. **Settings** — Gaussian path, PBE/B3LYP, Voigt FWHM, C1s reference  
2. **Compounds** — upload mol2 / pdb / sdf (RDKit)  
3. **Work review** — 3D structure preview before calculations  
4. **Jobs** — create a multi-step ΔSCF workflow (see step guide)  
5. **Queue** — run steps one-by-one on Windows (disabled on Mac without `g09`)  
6. **Results** — ΔSCF binding energies and C/N/O spectra  
7. **Archive** — export zip on Windows → import on Mac for analysis  

**Method:** gas-phase ΔSCF in Gaussian 09 — OPT → neutral SP (E₀) → core-hole SP per atom (BE = ΔE).
"""
)
