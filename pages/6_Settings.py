"""Settings — paths, resources, XPS options."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.components.sidebar import render_sidebar
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.version import get_version, version_label

st.set_page_config(page_title="Quanta · Settings", layout="wide")
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_settings", lang))
st.caption(version_label())

st.subheader("Gaussian / folders")
settings.gaussian_exe = st.text_input("Gaussian executable path", value=settings.gaussian_exe)
settings.work_dir = st.text_input("Work directory (optional)", value=settings.work_dir)
settings.scratch_dir = st.text_input("Scratch / GAUSS_SCRDIR (optional)", value=settings.scratch_dir)
c1, c2 = st.columns(2)
settings.nproc = int(c1.number_input("%nprocshared", min_value=1, max_value=64, value=settings.nproc))
settings.mem_mb = int(c2.number_input("%mem MB", min_value=500, max_value=256000, value=settings.mem_mb, step=100))

st.subheader("XPS corrections (Yamada & Sato)")
settings.xps_scale = float(st.number_input("Scale factor", value=float(settings.xps_scale), format="%.4f"))
settings.xps_c1s_ref_ev = float(st.number_input("C1s reference (eV)", value=float(settings.xps_c1s_ref_ev)))
settings.xps_fwhm_ev = float(st.number_input("Voigt FWHM (eV)", value=float(settings.xps_fwhm_ev)))
settings.xps_apply_linear_map = st.checkbox("Apply linear map (correction 3)", value=settings.xps_apply_linear_map)
c1, c2, c3 = st.columns(3)
settings.xps_c1s_slope = float(c1.number_input("C1s slope", value=float(settings.xps_c1s_slope)))
settings.xps_o1s_slope = float(c2.number_input("O1s slope", value=float(settings.xps_o1s_slope)))
settings.xps_n1s_slope = float(c3.number_input("N1s slope", value=float(settings.xps_n1s_slope)))

if st.button(t("save", lang)):
    settings.save()
    st.success("Saved to data/settings.json")
