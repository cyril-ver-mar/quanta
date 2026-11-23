"""Settings — paths, resources, ΔSCF XPS options."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.components.sidebar import render_sidebar
from src.ui.components.update_banner import render_update_settings
from src.utils.config import AppSettings
from src.utils.i18n import t
from src.utils.secrets import clear_secrets_cache, load_secrets, secrets_status
from src.utils.version import version_label

load_secrets()
settings = render_sidebar(AppSettings.load())
lang = settings.language
st.title(t("nav_settings", lang))
st.caption(version_label())

st.subheader(t("settings_gaussian", lang))
settings.gaussian_exe = st.text_input(t("settings_gaussian_exe", lang), value=settings.gaussian_exe)
st.caption(t("settings_gaussian_cli_hint", lang))
settings.work_dir = st.text_input(t("settings_work_dir", lang), value=settings.work_dir)
st.caption(t("settings_work_dir_hint", lang))
settings.scratch_dir = st.text_input(t("settings_scratch_dir", lang), value=settings.scratch_dir)
c1, c2 = st.columns(2)
settings.nproc = int(c1.number_input(t("settings_nproc", lang), min_value=1, max_value=64, value=settings.nproc))
settings.mem_mb = int(c2.number_input(t("settings_mem", lang), min_value=500, max_value=256000, value=settings.mem_mb, step=100))

st.subheader(t("settings_engine", lang))
settings.engine = st.selectbox(
    t("settings_engine", lang),
    options=["gaussian", "gpaw"],
    index=0 if (settings.engine or "gaussian") == "gaussian" else 1,
    format_func=lambda name: t(f"settings_engine_{name}", lang),
)
st.caption(t("settings_engine_hint", lang))

st.subheader(t("settings_dscf", lang))
st.caption(t("settings_dscf_hint", lang))
c1, c2 = st.columns(2)
_func_options = ["pbe", "b3lyp"]
_func_index = _func_options.index(settings.dscf_functional.lower()) if settings.dscf_functional.lower() in _func_options else 0
settings.dscf_functional = c1.selectbox(
    t("settings_functional", lang),
    options=_func_options,
    index=_func_index,
    format_func=lambda x: "PBEPBE (PBE)" if x == "pbe" else "B3LYP",
)
st.caption(t("settings_dscf_g09_hint", lang))
settings.dscf_basis = c2.text_input(t("settings_basis", lang), value=settings.dscf_basis)
settings.xps_fwhm_ev = float(st.number_input(t("settings_fwhm", lang), value=float(settings.xps_fwhm_ev)))

st.subheader(t("settings_reference", lang))
st.caption(t("settings_reference_help", lang))
_ref_modes = ["absolute", "global", "per_element", "fermi", "vbm"]
_ref_index = _ref_modes.index(settings.xps_reference_mode) if settings.xps_reference_mode in _ref_modes else 0
settings.xps_reference_mode = st.selectbox(
    t("settings_reference_mode", lang),
    options=_ref_modes,
    index=_ref_index,
    format_func=lambda name: t(f"settings_reference_{name}", lang),
)
_ref_elements = ["C", "N", "O"]
_el_index = _ref_elements.index(settings.xps_reference_element) if settings.xps_reference_element in _ref_elements else 0
settings.xps_reference_element = st.selectbox(
    t("settings_reference_element", lang),
    options=_ref_elements,
    index=_el_index,
)
r1, r2, r3 = st.columns(3)
settings.xps_c1s_ref_ev = float(r1.number_input(t("settings_c1s_ref", lang), value=float(settings.xps_c1s_ref_ev)))
settings.xps_n1s_ref_ev = float(r2.number_input(t("settings_n1s_ref", lang), value=float(settings.xps_n1s_ref_ev)))
settings.xps_o1s_ref_ev = float(r3.number_input(t("settings_o1s_ref", lang), value=float(settings.xps_o1s_ref_ev)))
settings.dscf_apply_c1s_shift = settings.xps_reference_mode == "global"

st.subheader(t("settings_gpaw", lang))
st.caption(t("settings_gpaw_hint", lang))
g1, g2, g3 = st.columns(3)
settings.gpaw_xc = g1.text_input(t("settings_gpaw_xc", lang), value=settings.gpaw_xc)
settings.gpaw_pw_cutoff_ev = float(
    g2.number_input(t("settings_gpaw_cutoff", lang), min_value=50.0, value=float(settings.gpaw_pw_cutoff_ev), step=50.0)
)
settings.gpaw_smearing_ev = float(
    g3.number_input(t("settings_gpaw_smearing", lang), min_value=0.0, value=float(settings.gpaw_smearing_ev), step=0.05, format="%.3f")
)
g4, g5 = st.columns(2)
settings.gpaw_kpts = g4.text_input(t("settings_gpaw_kpts", lang), value=settings.gpaw_kpts)
settings.gpaw_supercell = g5.text_input(t("settings_gpaw_supercell", lang), value=settings.gpaw_supercell)
_charge_modes = ["neutral", "charged"]
_charge_index = _charge_modes.index(settings.gpaw_charge_mode) if settings.gpaw_charge_mode in _charge_modes else 0
settings.gpaw_charge_mode = st.selectbox(
    t("settings_gpaw_charge_mode", lang),
    options=_charge_modes,
    index=_charge_index,
    format_func=lambda name: t(f"settings_gpaw_charge_{name}", lang),
)
st.caption(t("settings_gpaw_charge_help", lang))
settings.gpaw_elements = st.text_input(t("settings_gpaw_elements", lang), value=settings.gpaw_elements)
settings.gpaw_setup_name = st.text_input(t("settings_gpaw_setup_name", lang), value=settings.gpaw_setup_name)
settings.gpaw_setup_dir = st.text_input(t("settings_gpaw_setup_dir", lang), value=settings.gpaw_setup_dir)

if st.button(t("save", lang)):
    settings.save()
    st.success(t("settings_saved", lang))

st.divider()
st.subheader(t("settings_secrets", lang))
st.caption(t("settings_secrets_hint", lang))
sec = secrets_status()
st.write(t("settings_secrets_path", lang, path=sec["path"]))
if sec["exists"]:
    st.success(t("settings_secrets_found", lang, keys=", ".join(sec["keys"]) or "—"))
else:
    st.info(t("settings_secrets_missing", lang))
if sec["github_token_configured"]:
    source = (
        t("settings_secrets_token_env", lang)
        if sec["github_token_from_env"]
        else t("settings_secrets_token_file", lang)
    )
    st.caption(t("settings_secrets_token_ok", lang, source=source))
else:
    st.caption(t("settings_secrets_token_missing", lang))
if st.button(t("settings_secrets_reload", lang), key="_secrets_reload"):
    clear_secrets_cache()
    load_secrets()
    st.rerun()

st.divider()
render_update_settings(lang)
